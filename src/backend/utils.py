import os
from backend.plc.plc_client import PLCClient
from schemas import ProductionData
from typing import Literal, cast
from datetime import datetime


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


def fetch_production_timestamp(
    client: PLCClient, head_device: str = "SD210"
) -> datetime:
    """PLCから生産データのタイムスタンプを取得

    三菱PLCの日時データはBCD形式で格納されている。
    SD210から3ワード(YMDhms)を読み取り、datetime型に変換する。

    フォーマット例:
    - ワード1 (SD210): 0x2511 → 2025年11月
    - ワード2 (SD211): 0x1314 → 13日14時
    - ワード3 (SD212): 0x3045 → 30分45秒

    Args:
        client: PLCクライアント
        head_device: 日時格納デバイス (デフォルト: SD210)

    Returns:
        datetime: PLCから取得した日時
    """
    try:
        # SD210から3ワード読み取り
        data = client.read_words(head_device, size=3)

        # BCD形式を10進数に変換
        # 例: 0x2511 → "2511" → 年=25, 月=11
        word1 = f"{data[0]:04x}"
        Y = int("20" + word1[:2])  # 年: 先頭2桁 (20xx年)
        M = int(word1[2:])  # 月: 後ろ2桁

        word2 = f"{data[1]:04x}"
        D = int(word2[:2])  # 日: 先頭2桁
        h = int(word2[2:])  # 時: 後ろ2桁

        word3 = f"{data[2]:04x}"
        m = int(word3[:2])  # 分: 先頭2桁
        s = int(word3[2:])  # 秒: 後ろ2桁

        return datetime(Y, M, D, h, m, s)

    except (ConnectionError, OSError, ValueError, IndexError) as e:
        # PLC接続エラーまたはデータ変換エラー時は現在時刻を返す
        from backend.logging import plc_logger as logger

        logger.warning(f"Failed to get timestamp from PLC: {e}, using system time")
        return datetime.now()


def fetch_production_data(client: PLCClient) -> ProductionData:
    """PLCから生産データを一括取得

    将来的な実装例:
    - fetch_production_timestamp() でタイムスタンプ取得
    - 各デバイスから計画数、実績数、アラーム情報を取得
    - ProductionDataに統合して返す
    """
    # TODO: 実際のPLCデバイスから取得する実装
    # timestamp = fetch_production_timestamp(client)
    # plan = client.read_words("D100", size=1)[0]
    # actual = client.read_words("D101", size=1)[0]
    # alarm = client.read_bits("M100", size=1)[0]

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
