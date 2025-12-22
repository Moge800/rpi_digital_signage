from pathlib import Path

from .logger import setup_logger, setup_root_logger

# プロジェクトルートのlogsフォルダを使用
# src/backend/logging/__init__.py → 3つ上がプロジェクトルート
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LOGS_DIR = _PROJECT_ROOT / "logs"

# アプリケーション全体で共通のロガー設定
launcher_logger = setup_logger(
    "backend.launcher", log_file=str(_LOGS_DIR / "launcher.log")
)
plc_logger = setup_logger("backend.plc", log_file=str(_LOGS_DIR / "plc.log"))
backend_logger = setup_logger("backend.utils", log_file=str(_LOGS_DIR / "backend.log"))
app_logger = setup_logger(
    "frontend", log_file=str(_LOGS_DIR / "app.log"), level=20
)  # INFO
api_logger = setup_logger("api", log_file=str(_LOGS_DIR / "api.log"), level=20)  # INFO

__all__ = [
    "setup_logger",
    "setup_root_logger",
    "launcher_logger",
    "plc_logger",
    "backend_logger",
    "app_logger",
    "api_logger",
]
