"""APIクライアントモジュール

FastAPIバックエンドと通信するためのクライアント。
Streamlitフロントエンドから使用する。

フェイルセーフ機能:
- タイムアウト付きリクエスト (デフォルト3秒)
- エラー時は前回取得値を返す
"""

import httpx
from datetime import datetime
from typing import Any

from config.settings import Settings
from schemas import ProductionData
from backend.logging import app_logger as logger

# 設定読み込み
_settings = Settings()
API_BASE_URL = f"http://{_settings.API_HOST}:{_settings.API_PORT}"

# タイムアウト設定 (設定ファイルから読み込み)
API_TIMEOUT = _settings.FRONTEND_API_TIMEOUT

# 前回取得値のキャッシュ (フェイルセーフ用)
_last_production_data: ProductionData | None = None


def _get_client() -> httpx.Client:
    """HTTPクライアントを取得"""
    return httpx.Client(base_url=API_BASE_URL, timeout=API_TIMEOUT)


def fetch_production_from_api() -> ProductionData:
    """APIから生産データを取得

    フェイルセーフ: エラー時は前回取得値を返す (利用可能な場合)

    Returns:
        ProductionData: 生産データ

    Raises:
        httpx.HTTPError: API通信エラー時 (前回値がない場合)
    """
    global _last_production_data

    try:
        with _get_client() as client:
            response = client.get("/api/production")
            response.raise_for_status()
            data = response.json()

            result = ProductionData(
                line_name=data["line_name"],
                production_type=data["production_type"],
                production_name=data["production_name"],
                plan=data["plan"],
                actual=data["actual"],
                in_operating=data["in_operating"],
                remain_min=data["remain_min"],
                remain_pallet=data["remain_pallet"],
                fully=data["fully"],
                alarm=data["alarm"],
                alarm_msg=data["alarm_msg"],
                timestamp=datetime.fromisoformat(data["timestamp"]),
            )

            # 成功時は前回値を更新
            _last_production_data = result
            return result

    except httpx.TimeoutException as e:
        logger.warning(f"API request timeout ({API_TIMEOUT}s): {e}")
        return _get_fallback_data("APIタイムアウト")

    except httpx.HTTPStatusError as e:
        logger.error(
            f"API returned error: {e.response.status_code} - {e.response.text}"
        )
        return _get_fallback_data(f"APIエラー: {e.response.status_code}")

    except httpx.RequestError as e:
        logger.error(f"API connection error: {e}")
        return _get_fallback_data("API接続エラー")


def _get_fallback_data(error_msg: str) -> ProductionData:
    """フォールバックデータを取得

    前回取得値があればそれを返し、なければエラーデータを返す。

    Args:
        error_msg: エラーメッセージ

    Returns:
        ProductionData: 前回値またはエラーデータ
    """
    global _last_production_data

    if _last_production_data is not None:
        logger.info(
            f"Using cached data from {_last_production_data.timestamp.isoformat()}"
        )
        # 前回値のコピーを作成 (alarm_msgを更新)
        fallback = ProductionData(
            line_name=_last_production_data.line_name,
            production_type=_last_production_data.production_type,
            production_name=_last_production_data.production_name,
            plan=_last_production_data.plan,
            actual=_last_production_data.actual,
            in_operating=_last_production_data.in_operating,
            remain_min=_last_production_data.remain_min,
            remain_pallet=_last_production_data.remain_pallet,
            fully=_last_production_data.fully,
            alarm=False,  # キャッシュ使用中はアラーム表示しない
            alarm_msg=f"[キャッシュ] {error_msg}",
            timestamp=_last_production_data.timestamp,
        )
        return fallback
    else:
        # 前回値がない場合はエラーデータ
        logger.warning("No cached data available, returning error data")
        error_data = ProductionData.error()
        error_data.alarm_msg = error_msg
        return error_data


def check_api_health() -> bool:
    """APIサーバーのヘルスチェック

    Returns:
        bool: APIが正常ならTrue
    """
    try:
        with _get_client() as client:
            response = client.get("/health")
            return response.status_code == 200
    except httpx.RequestError:
        return False


def get_api_status() -> dict[str, Any]:
    """APIからステータスを取得

    Returns:
        dict: ステータス情報
    """
    try:
        with _get_client() as client:
            response = client.get("/api/status")
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Failed to get API status: {e}")
        return {
            "plc_connected": False,
            "use_plc": False,
            "line_name": "UNKNOWN",
            "last_update": None,
        }


def request_time_sync() -> dict[str, Any]:
    """APIに時刻同期をリクエスト

    Returns:
        dict: 同期結果
    """
    try:
        with _get_client() as client:
            response = client.post("/api/system/sync-time")
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Time sync request failed: {e}")
        return {
            "success": False,
            "synced_time": None,
            "message": f"API通信エラー: {e}",
        }


def request_shutdown() -> dict[str, Any]:
    """APIサーバーのシャットダウンをリクエスト

    Returns:
        dict: シャットダウン結果
    """
    try:
        with _get_client() as client:
            response = client.post("/api/shutdown")
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Shutdown request failed: {e}")
        return {
            "status": "error",
            "message": f"API通信エラー: {e}",
        }


def request_restart() -> dict[str, Any]:
    """APIサーバーの再起動をリクエスト (緊急用)

    .env の ALLOW_FRONTEND_RESTART=true の場合のみ有効。

    Returns:
        dict: 再起動結果
    """
    try:
        with _get_client() as client:
            response = client.post("/api/restart")
            if response.status_code == 403:
                return {
                    "status": "forbidden",
                    "message": "再起動は許可されていません",
                }
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Restart request failed: {e}")
        return {
            "status": "error",
            "message": f"API通信エラー: {e}",
        }


def is_restart_allowed() -> bool:
    """フロントエンドからの再起動が許可されているか確認

    Returns:
        bool: 許可されていればTrue
    """
    return _settings.ALLOW_FRONTEND_RESTART
