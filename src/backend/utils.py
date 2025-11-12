import os
from dotenv import load_dotenv
from backend.plc.plc_client import PLCClient
from schemas import ProductionData
from typing import Literal, cast

load_dotenv()


def get_use_plc() -> bool:
    """USE_PLC設定を取得"""
    use_plc = os.getenv("USE_PLC", "true").lower()
    return use_plc in ("1", "true", "yes", "on")


def get_line_name() -> str:
    """LINE_NAME設定を取得"""
    return os.getenv("LINE_NAME", "NONAME")


def get_refresh_interval() -> float:
    """フロントエンドのリフレッシュ間隔（秒）を取得"""
    interval = os.getenv("REFRESH_INTERVAL")
    if interval is not None:
        try:
            return int(interval)
        except ValueError:
            pass
    return 10  # デフォルト10秒


def get_log_level() -> Literal["DEBUG", "INFO", "WARNING", "ERROR"]:
    """ログレベルを取得"""
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    valid_levels = ("DEBUG", "INFO", "WARNING", "ERROR")
    return cast(
        Literal["DEBUG", "INFO", "WARNING", "ERROR"],
        level if level in valid_levels else "INFO",
    )


def fetch_plc_data(client: PLCClient) -> ProductionData:
    """PLCからのデータ取得（ダミー実装）"""
    # ここにPLCからのデータ取得ロジックを実装
    return ProductionData(
        line_name="LINE_1",
        production_type=1,
        plan=45000,
        actual=30000,
        remain_min=300,
        alarm=False,
        alarm_msg="",
        timestamp=None,
    )
