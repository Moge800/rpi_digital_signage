"""FastAPI メインアプリケーション

デジタルサイネージバックエンドAPI。
PLCとの通信を一元管理し、フロントエンドにRESTful APIを提供。

起動方法:
    uvicorn src.api.main:app --host 127.0.0.1 --port 8000
"""

import signal
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI
from dotenv import load_dotenv

# プロジェクトルートをパスに追加 (signage_app.pyと同じパターン)
sys.path.insert(0, str(Path(__file__).parent.parent))

# .envファイルを読み込む
load_dotenv()

from api.routes import production, system
from api.services.plc_service import plc_service
from backend.logging import api_logger as logger


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """アプリケーションのライフサイクル管理

    起動時: PLC接続を初期化
    終了時: PLC接続を安全に切断
    """
    # 起動時
    logger.info("API Server starting...")
    plc_service.initialize()

    yield

    # 終了時
    logger.info("API Server shutting down...")
    plc_service.shutdown()
    logger.info("API Server shutdown complete")


app = FastAPI(
    title="Digital Signage API",
    description="Raspberry Pi デジタルサイネージ バックエンドAPI",
    version="1.0.0",
    lifespan=lifespan,
)

# ルーター登録
app.include_router(production.router, prefix="/api", tags=["production"])
app.include_router(system.router, prefix="/api", tags=["system"])


@app.get("/", tags=["root"])
async def root() -> dict[str, str]:
    """ルートパス

    APIサーバーの情報を返す。
    """
    return {
        "name": "Digital Signage API",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str | int]:
    """ヘルスチェック (軽量)

    PLC通信は行わず、APIプロセスの生存確認のみを行う。
    Watchdogからの監視用エンドポイント。

    Returns:
        {"status": "ok", "pid": <プロセスID>}
    """
    import os

    return {"status": "ok", "pid": os.getpid()}


@app.get("/ready", tags=["health"])
async def readiness_check() -> dict[str, str | int | bool]:
    """レディネスチェック (やや重い)

    スレッドプールが動作しているかなど、実処理能力を確認。
    /health より重いが、SM400読み取りでPLC通信も確認。

    用途:
    - イベントループ詰まりの検知
    - スレッドプール死活確認
    - PLC通信の死活確認 (SM400常時ON)

    Returns:
        {"status": "ok", "pid": <PID>, "plc_alive": <bool>, ...}
    """
    import os
    from concurrent.futures import (
        ThreadPoolExecutor,
        TimeoutError as FuturesTimeoutError,
    )

    pid = os.getpid()

    # スレッドプールが動作しているか確認 (簡単なタスクを投げる)
    def _ping() -> bool:
        return True

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_ping)
            result = future.result(timeout=1.0)  # 1秒でタイムアウト
            thread_pool_ok = result
    except (FuturesTimeoutError, Exception):
        thread_pool_ok = False

    # PLCServiceの状態確認 (通信なし)
    plc_ready = plc_service.is_ready()

    # PLC通信確認 (SM400読み取り)
    plc_alive = plc_service.ping_plc()

    # 総合判定
    if thread_pool_ok and plc_ready and plc_alive:
        status = "ok"
    elif thread_pool_ok and plc_ready:
        status = "degraded"  # 状態はOKだがPLC通信不可
    else:
        status = "unhealthy"

    return {
        "status": status,
        "pid": pid,
        "thread_pool_ok": thread_pool_ok,
        "plc_service_ready": plc_ready,
        "plc_alive": plc_alive,
    }


# シャットダウンシグナルハンドラ (Linux/Raspberry Pi用)
# Windows環境ではuvicornのデフォルト処理に任せる
import platform

if platform.system() != "Windows":

    def handle_shutdown_signal(signum: int, frame: object) -> None:
        """シグナル受信時のクリーンアップ"""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        plc_service.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_shutdown_signal)
    signal.signal(signal.SIGINT, handle_shutdown_signal)
