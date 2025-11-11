from .logger import setup_logger, setup_root_logger

# アプリケーション全体で共通のロガー設定
plc_logger = setup_logger("backend.plc", log_file="logs/plc.log")
app_logger = setup_logger("frontend", log_file="logs/app.log", level=20)  # INFO

__all__ = ["setup_logger", "setup_root_logger", "plc_logger", "app_logger"]
