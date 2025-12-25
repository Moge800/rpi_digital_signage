"""システム関連エンドポイント

/api/system/sync-time - PLC時刻同期
/api/shutdown         - 安全なシャットダウン
/api/restart          - 緊急再起動 (要許可設定)
"""

import os
import signal
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.services.plc_service import plc_service
from backend.system_utils import set_system_clock
from backend.logging import api_logger as logger
from config.settings import Settings

router = APIRouter()

# 設定読み込み
_settings = Settings()


class SyncTimeResponse(BaseModel):
    """時刻同期レスポンス"""

    success: bool
    synced_time: str | None
    message: str


class ShutdownResponse(BaseModel):
    """シャットダウンレスポンス"""

    status: str
    message: str


@router.post("/system/sync-time", response_model=SyncTimeResponse)
async def sync_system_time() -> SyncTimeResponse:
    """PLCの時刻でシステム時刻を同期

    Returns:
        SyncTimeResponse: 同期結果

    Note:
        Linux環境でsudo権限が必要な場合がある
    """
    try:
        plc_time = plc_service.get_plc_timestamp()
        if plc_time is None:
            return SyncTimeResponse(
                success=False,
                synced_time=None,
                message="PLC時刻を取得できません (USE_PLC=false または未接続)",
            )

        success = set_system_clock(plc_time)
        if success:
            logger.info(f"System clock synced with PLC: {plc_time}")
            return SyncTimeResponse(
                success=True,
                synced_time=plc_time.isoformat(),
                message="システム時刻を同期しました",
            )
        else:
            logger.warning("Failed to set system clock")
            return SyncTimeResponse(
                success=False,
                synced_time=plc_time.isoformat(),
                message="システム時刻の設定に失敗しました (権限不足の可能性)",
            )
    except Exception as e:
        logger.error(f"Time sync error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/shutdown", response_model=ShutdownResponse)
async def shutdown_server() -> ShutdownResponse:
    """APIサーバーを安全にシャットダウン

    1. PLCとの接続を切断
    2. ログ出力
    3. プロセス終了シグナル送信

    Returns:
        ShutdownResponse: シャットダウン開始通知

    Note:
        このエンドポイント呼び出し後、サーバーは停止する
    """
    logger.info("Shutdown requested via API")

    # PLCとの接続を安全に切断
    plc_service.shutdown()

    # 自分自身にSIGTERMを送信（graceful shutdown）
    # レスポンスを返した後に終了するため、バックグラウンドで実行
    import asyncio

    async def delayed_shutdown() -> None:
        try:
            await asyncio.sleep(0.5)  # レスポンス送信を待つ
            logger.info("Sending SIGTERM to self...")
            os.kill(os.getpid(), signal.SIGTERM)
        except Exception as e:
            logger.error(f"Error during delayed shutdown: {e}")

    asyncio.create_task(delayed_shutdown())

    return ShutdownResponse(
        status="shutting_down",
        message="シャットダウンを開始しました。PLCとの接続を安全に切断しました。",
    )


class RestartResponse(BaseModel):
    """再起動レスポンス"""

    status: str
    message: str


@router.post("/restart", response_model=RestartResponse)
async def restart_server() -> RestartResponse:
    """APIサーバーを再起動 (緊急用)

    .env の ALLOW_FRONTEND_RESTART=true の場合のみ有効。
    Watchdogに再起動を委ねるため、SIGTERMを送信してプロセスを終了する。

    Returns:
        RestartResponse: 再起動開始通知

    Raises:
        HTTPException: 再起動が許可されていない場合 (403)

    Note:
        - 通常はWatchdogによる自動復旧を使用
        - このエンドポイントは緊急用
    """
    if not _settings.ALLOW_FRONTEND_RESTART:
        logger.warning("Restart request denied: ALLOW_FRONTEND_RESTART=false")
        raise HTTPException(
            status_code=403,
            detail="再起動は許可されていません (ALLOW_FRONTEND_RESTART=false)",
        )

    logger.info("Restart requested via API (emergency)")

    # PLCとの接続を安全に切断
    plc_service.shutdown()

    # 自分自身にSIGTERMを送信 (Watchdogが再起動を担当)
    import asyncio

    async def delayed_restart() -> None:
        try:
            await asyncio.sleep(0.5)  # レスポンス送信を待つ
            logger.info("Sending SIGTERM to self for restart...")
            os.kill(os.getpid(), signal.SIGTERM)
        except Exception as e:
            logger.error(f"Error during delayed restart: {e}")

    asyncio.create_task(delayed_restart())

    return RestartResponse(
        status="restarting",
        message="再起動を開始しました。Watchdogによる復旧をお待ちください。",
    )
