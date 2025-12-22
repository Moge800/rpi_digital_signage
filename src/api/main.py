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


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """ヘルスチェック (軽量)

    Returns:
        {"status": "ok"}
    """
    return {"status": "ok"}


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
