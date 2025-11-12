import os
from backend.plc.plc_client import PLCClient
from schemas import ProductionData
from config.production_config import ProductionConfigManager
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


def remain_pallet_calculation(
    plan: int, actual: int, production_type: int, decimals: int | None = 2
) -> float:
    """残りパレット数を計算する

    Args:
        plan: 計画生産数
        actual: 実績生産数
        production_type: 機種番号 (0-15)
        decimals: 小数点以下の桁数 (Noneの場合は丸めない)

    Returns:
        float: 残りパレット数
    """
    config_manager = ProductionConfigManager()
    config = config_manager.get_config(production_type)

    remaining_units = max(0, plan - actual)
    remain_pallet = remaining_units / config.fully

    return round(remain_pallet, decimals) if decimals is not None else remain_pallet


def calculate_remain_minutes(
    plan: int, actual: int, production_type: int, decimals: int | None = 2
) -> float:
    """残り時間(分)を計算

    Args:
        plan: 計画数
        actual: 実績数
        production_type: 機種番号
        decimals: 小数点以下の桁数 (Noneの場合は丸めない)

    Returns:
        float: 残り時間(分)
    """
    config_manager = ProductionConfigManager()
    config = config_manager.get_config(production_type)

    remain = plan - actual
    remain_seconds = remain * config.seconds_per_product  # 残り個数 × 1個あたりの秒数
    remain_minute = remain_seconds / 60.0

    return round(remain_minute, decimals) if decimals is not None else remain_minute


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
    if head_device == "":
        raise ValueError("head_device cannot be an empty string")

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
    line_name = get_line_name()
    production_type = 1  # TODO: PLCから取得
    plan = 30000
    actual = 20000
    in_operating = True

    # 機種設定を使って計算
    remain_min = calculate_remain_minutes(plan, actual, production_type)
    remain_pallet = remain_pallet_calculation(plan, actual, production_type)

    alarm = False
    alarm_msg = ""
    timestamp = datetime(2025, 1, 12, 10, 30, 0)

    return ProductionData(
        line_name=line_name,
        production_type=production_type,
        plan=plan,
        actual=actual,
        in_operating=in_operating,
        remain_min=remain_min,
        remain_pallet=remain_pallet,
        alarm=alarm,
        alarm_msg=alarm_msg,
        timestamp=timestamp,
    )
