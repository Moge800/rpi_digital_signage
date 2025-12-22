"""APIクライアントモジュール

FastAPIバックエンドと通信するためのクライアント。
Streamlitフロントエンドから使用する。
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

# タイムアウト設定
API_TIMEOUT = 5.0  # 秒


def _get_client() -> httpx.Client:
    """HTTPクライアントを取得"""
    return httpx.Client(base_url=API_BASE_URL, timeout=API_TIMEOUT)


def fetch_production_from_api() -> ProductionData:
    """APIから生産データを取得

    Returns:
        ProductionData: 生産データ

    Raises:
        httpx.HTTPError: API通信エラー時
    """
    try:
        with _get_client() as client:
            response = client.get("/api/production")
            response.raise_for_status()
            data = response.json()

            return ProductionData(
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
    except httpx.HTTPStatusError as e:
        logger.error(
            f"API returned error: {e.response.status_code} - {e.response.text}"
        )
        raise
    except httpx.RequestError as e:
        logger.error(f"API connection error: {e}")
        raise


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
