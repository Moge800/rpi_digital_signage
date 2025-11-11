import os
import dotenv
from backend.plc.plc_client import PLCClient
from frontend.schemas import ProductionData

dotenv.load_dotenv()


def get_refresh_interval():
    """フロントエンドのリフレッシュ間隔（秒）を取得"""
    interval = os.getenv("REFRESH_INTERVAL")
    if interval is not None:
        try:
            return int(interval)
        except ValueError:
            pass
    return 10  # デフォルト10秒


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
