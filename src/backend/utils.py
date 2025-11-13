from backend.plc.plc_client import PLCClient
from schemas import ProductionData
from config.production_config import ProductionConfigManager, ProductionTypeConfig
from config.settings import Settings
from backend.logging import plc_logger as logger
from typing import Literal
from datetime import datetime


def get_use_plc() -> bool:
    """USE_PLC設定を取得"""
    settings = Settings()
    return settings.USE_PLC


def get_line_name() -> str:
    """LINE_NAME設定を取得"""
    settings = Settings()
    return settings.LINE_NAME


def get_refresh_interval() -> float:
    """フロントエンドのリフレッシュ間隔（秒）を取得"""
    settings = Settings()
    return settings.REFRESH_INTERVAL


def get_log_level() -> Literal["DEBUG", "INFO", "WARNING", "ERROR"]:
    """ログレベルを取得"""
    settings = Settings()
    return settings.LOG_LEVEL


def get_config_data(production_type: int) -> ProductionTypeConfig:
    """指定された機種番号に対応する機種設定を取得する

    Args:
        production_type: 機種番号 (0-15)

    Returns:
        ProductionTypeConfig: 機種設定オブジェクト
    """
    config_manager = ProductionConfigManager()
    return config_manager.get_config(production_type)


def get_plc_device_dict() -> dict[str, str]:
    """PLCデバイスリスト設定を取得"""
    from config.settings import PLCDeviceList

    device_list_settings = PLCDeviceList()
    return {
        "TIME_DEVICE": device_list_settings.TIME_DEVICE,
        "PRODUCTION_TYPE_DEVICE": device_list_settings.PRODUCTION_TYPE_DEVICE,
        "PLAN_DEVICE": device_list_settings.PLAN_DEVICE,
        "ACTUAL_DEVICE": device_list_settings.ACTUAL_DEVICE,
        "ALARM_FLAG_DEVICE": device_list_settings.ALARM_FLAG_DEVICE,
        "ALARM_MSG_DEVICE": device_list_settings.ALARM_MSG_DEVICE,
        "IN_OPERATING_DEVICE": device_list_settings.IN_OPERATING_DEVICE,
    }


def calculate_remain_pallet(
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
    config = get_config_data(production_type)

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
    config = get_config_data(production_type)

    remain = plan - actual
    remain_seconds = remain * config.seconds_per_product  # 残り個数 × 1個あたりの秒数
    remain_minute = remain_seconds / 60.0

    return round(remain_minute, decimals) if decimals is not None else remain_minute


def fetch_production_timestamp(client: PLCClient, head_device: str) -> datetime:
    """PLCから生産データのタイムスタンプを取得

    三菱PLCの日時データはBCD形式で格納されている。
    SD210から3ワード(YMDhms)を読み取り、datetime型に変換する。

    フォーマット例:
    - ワード1 (SD210): 0x2511 → 2025年11月
    - ワード2 (SD211): 0x1314 → 13日14時
    - ワード3 (SD212): 0x3045 → 30分45秒

    Args:
        client: PLCクライアント
        head_device: 日時格納デバイス

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
        logger.warning(f"Failed to get timestamp from PLC: {e}, using system time")
        return datetime.now()


def fetch_production_type(client: PLCClient, device_address: str) -> int:
    """PLCから生産機種番号を取得

    Args:
        client: PLCクライアント
        device_address: 機種番号格納デバイスアドレス

    Returns:
        int: 生産機種番号
    """
    try:
        data = client.read_words(device_address, size=1)
        production_type = data[0]
        return production_type
    except (ConnectionError, OSError, ValueError, IndexError) as e:
        logger.warning(f"Failed to get production type from PLC: {e}, using default 0")
        return 0  # 0をデフォルト値として返す,0番は存在しない機種


def fetch_plan(client: PLCClient, device_address: str) -> int:
    """PLCから生産計画数を取得

    Args:
        client: PLCクライアント
        device_address: 計画数格納デバイスアドレス

    Returns:
        int: 生産計画数
    """
    try:
        data = client.read_words(device_address, size=1)
        plan = data[0]
        return plan
    except (ConnectionError, OSError, ValueError, IndexError) as e:
        logger.warning(f"Failed to get production plan from PLC: {e}, using default 0")
        return 0  # 0をデフォルト値として返す


def fetch_actual(client: PLCClient, device_address: str) -> int:
    """PLCから生産実績数を取得

    Args:
        client: PLCクライアント
        device_address: 実績数格納デバイスアドレス

    Returns:
        int: 生産実績数
    """
    try:
        data = client.read_words(device_address, size=1)
        actual = data[0]
        return actual
    except (ConnectionError, OSError, ValueError, IndexError) as e:
        logger.warning(
            f"Failed to get production actual from PLC: {e}, using default 0"
        )
        return 0  # 0をデフォルト値として返す


def fetch_in_operating(client: PLCClient, device_address: str) -> bool:
    """PLCから稼働中フラグを取得

    Args:
        client: PLCクライアント
        device_address: 稼働中フラグ格納デバイスアドレス

    Returns:
        bool: 稼働中フラグ
    """
    try:
        data = client.read_bits(device_address, size=1)
        in_operating = bool(data[0])
        return in_operating
    except (ConnectionError, OSError, ValueError, IndexError) as e:
        logger.warning(
            f"Failed to get in_operating flag from PLC: {e}, using default False"
        )
        return False  # Falseをデフォルト値として返す


def fetch_alarm_flag(client: PLCClient, device_address: str) -> bool:
    """PLCからアラームフラグを取得

    Args:
        client: PLCクライアント
        device_address: アラームフラグ格納デバイスアドレス

    Returns:
        bool: アラームフラグ
    """
    try:
        data = client.read_bits(device_address, size=1)
        alarm_flag = bool(data[0])
        return alarm_flag
    except (ConnectionError, OSError, ValueError, IndexError) as e:
        logger.warning(f"Failed to get alarm flag from PLC: {e}, using default False")
        return False  # Falseをデフォルト値として返す


def fetch_alarm_msg(client: PLCClient, device_address: str) -> str:
    """PLCからアラームメッセージを取得

    Args:
        client: PLCクライアント
        device_address: アラームメッセージ格納デバイスアドレス

    Returns:
        str: アラームメッセージ
    """
    try:
        data = client.read_words(device_address, size=10)  # 10ワード分読み取り
        # ワードデータを文字列に変換 (例: [0x414C, 0x4152] → "ALAR")
        alarm_msg = "".join(chr((word >> 8) & 0xFF) + chr(word & 0xFF) for word in data)
        alarm_msg = alarm_msg.rstrip("\x00")  # 末尾のNULL文字を削除
        return alarm_msg
    except (ConnectionError, OSError, ValueError, IndexError) as e:
        logger.warning(
            f"Failed to get alarm message from PLC: {e}, using default empty string"
        )
        return ""  # 空文字をデフォルト値として返す


def fetch_production_data(client: PLCClient) -> ProductionData:
    """PLCから生産データを一括取得

    将来的な実装例:
    - fetch_production_timestamp() でタイムスタンプ取得
    - 各デバイスから計画数、実績数、アラーム情報を取得
    - ProductionDataに統合して返す
    """
    # TODO: 実際のPLCデバイスから取得する実装
    device_dict = get_plc_device_dict()
    line_name = get_line_name()
    production_type = fetch_production_type(
        client, device_dict["PRODUCTION_TYPE_DEVICE"]
    )
    plan = fetch_plan(client, device_dict["PLAN_DEVICE"])
    actual = fetch_actual(client, device_dict["ACTUAL_DEVICE"])
    in_operating = fetch_in_operating(client, device_dict["IN_OPERATING_DEVICE"])
    alarm = fetch_alarm_flag(client, device_dict["ALARM_FLAG_DEVICE"])
    alarm_msg = fetch_alarm_msg(client, device_dict["ALARM_MSG_DEVICE"])

    # 機種設定を取得してproduction_nameを解決
    config = get_config_data(production_type)

    # 機種設定を使って計算
    remain_min = calculate_remain_minutes(plan, actual, production_type)
    remain_pallet = calculate_remain_pallet(plan, actual, production_type)
    timestamp = fetch_production_timestamp(client, device_dict["TIME_DEVICE"])

    return ProductionData(
        line_name=line_name,
        production_type=production_type,
        production_name=config.name,
        plan=plan,
        actual=actual,
        in_operating=in_operating,
        remain_min=remain_min,
        remain_pallet=remain_pallet,
        alarm=alarm,
        alarm_msg=alarm_msg,
        timestamp=timestamp,
    )
