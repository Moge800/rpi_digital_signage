from .logger import setup_logger, setup_root_logger

# アプリケーション全体で共通のロガー設定
launcher_logger = setup_logger("backend.launcher", log_file="logs/launcher.log")
plc_logger = setup_logger("backend.plc", log_file="logs/plc.log")
backend_logger = setup_logger("backend.utils", log_file="logs/backend.log")
app_logger = setup_logger("frontend", log_file="logs/app.log", level=20)  # INFO

__all__ = [
    "setup_logger",
    "setup_root_logger",
    "launcher_logger",
    "plc_logger",
    "backend_logger",
    "app_logger",
]
