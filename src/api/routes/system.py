"""システム関連エンドポイント

/api/system/sync-time - PLC時刻同期
/api/shutdown         - 安全なシャットダウン
"""

import os
import signal
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.services.plc_service import plc_service
from backend.system_utils import set_system_clock
from backend.logging import api_logger as logger

router = APIRouter()


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
        await asyncio.sleep(0.5)  # レスポンス送信を待つ
        logger.info("Sending SIGTERM to self...")
        os.kill(os.getpid(), signal.SIGTERM)

    asyncio.create_task(delayed_shutdown())

    return ShutdownResponse(
        status="shutting_down",
        message="シャットダウンを開始しました。PLCとの接続を安全に切断しました。",
    )
