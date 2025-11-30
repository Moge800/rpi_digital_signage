"""PLC通信データ取得関数

PLCから各種データ(生産数、アラーム、タイムスタンプ等)を取得する関数群。
エラーハンドリングを含む汎用的なfetchヘルパー関数も提供。
"""

from datetime import datetime

from backend.logging import backend_logger as logger
from backend.plc.plc_client import PLCClient
from config.settings import PLCDeviceList
from schemas import ProductionData

# PLCデバイス設定のキャッシュ（モジュールレベルで1回だけ初期化）
_plc_device_list = PLCDeviceList()


def _fetch_word(
    client: PLCClient,
    device_address: str,
    field_name: str,
    default: int = 0,
) -> int:
    """PLCからワードデータを取得する汎用関数

    Args:
        client: PLCクライアント
        device_address: デバイスアドレス
        field_name: フィールド名（ログ出力用）
        default: エラー時のデフォルト値

    Returns:
        int: 取得したワード値
    """
    try:
        data = client.read_words(device_address, size=1)
        return data[0]
    except (ConnectionError, OSError, ValueError, IndexError) as e:
        logger.warning(
            f"Failed to get {field_name} from PLC: {e}, using default {default}"
        )
        return default


def _fetch_bit(
    client: PLCClient,
    device_address: str,
    field_name: str,
    default: bool = False,
) -> bool:
    """PLCからビットデータを取得する汎用関数

    Args:
        client: PLCクライアント
        device_address: デバイスアドレス
        field_name: フィールド名（ログ出力用）
        default: エラー時のデフォルト値

    Returns:
        bool: 取得したビット値
    """
    try:
        data = client.read_bits(device_address, size=1)
        return bool(data[0])
    except (ConnectionError, OSError, ValueError, IndexError) as e:
        logger.warning(
            f"Failed to get {field_name} from PLC: {e}, using default {default}"
        )
        return default


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
        int: 生産機種番号（エラー時は0）
    """
    return _fetch_word(client, device_address, "production type", default=0)


def fetch_plan(client: PLCClient, device_address: str) -> int:
    """PLCから生産計画数を取得

    Args:
        client: PLCクライアント
        device_address: 計画数格納デバイスアドレス

    Returns:
        int: 生産計画数（エラー時は0）
    """
    return _fetch_word(client, device_address, "production plan", default=0)


def fetch_actual(client: PLCClient, device_address: str) -> int:
    """PLCから生産実績数を取得

    Args:
        client: PLCクライアント
        device_address: 実績数格納デバイスアドレス

    Returns:
        int: 生産実績数（エラー時は0）
    """
    return _fetch_word(client, device_address, "production actual", default=0)


def fetch_in_operating(client: PLCClient, device_address: str) -> bool:
    """PLCから稼働中フラグを取得

    Args:
        client: PLCクライアント
        device_address: 稼働中フラグ格納デバイスアドレス

    Returns:
        bool: 稼働中フラグ（エラー時はFalse）
    """
    return _fetch_bit(client, device_address, "in_operating flag", default=False)


def fetch_alarm_flag(client: PLCClient, device_address: str) -> bool:
    """PLCからアラームフラグを取得

    Args:
        client: PLCクライアント
        device_address: アラームフラグ格納デバイスアドレス

    Returns:
        bool: アラームフラグ（エラー時はFalse）
    """
    return _fetch_bit(client, device_address, "alarm flag", default=False)


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


def get_plc_device_dict() -> dict[str, str]:
    """PLCデバイスリスト設定を取得

    Note:
        モジュールレベルでキャッシュされたPLCDeviceListを使用。
        パフォーマンス最適化のため、繰り返し呼び出しても初期化は1回のみ。

    Returns:
        dict[str, str]: PLCデバイスアドレスの辞書
    """
    return {
        "TIME_DEVICE": _plc_device_list.TIME_DEVICE,
        "PRODUCTION_TYPE_DEVICE": _plc_device_list.PRODUCTION_TYPE_DEVICE,
        "PLAN_DEVICE": _plc_device_list.PLAN_DEVICE,
        "ACTUAL_DEVICE": _plc_device_list.ACTUAL_DEVICE,
        "ALARM_FLAG_DEVICE": _plc_device_list.ALARM_FLAG_DEVICE,
        "ALARM_MSG_DEVICE": _plc_device_list.ALARM_MSG_DEVICE,
        "IN_OPERATING_DEVICE": _plc_device_list.IN_OPERATING_DEVICE,
    }


def fetch_production_data(client: PLCClient) -> ProductionData:
    """PLCから生産データを一括取得

    各種デバイスから生産情報を取得し、ProductionDataに統合して返す。
    計算ロジックはcalculators.pyに依存。

    Args:
        client: PLCクライアント

    Returns:
        ProductionData: 統合された生産データ
    """
    from backend.calculators import calculate_remain_minutes, calculate_remain_pallet
    from backend.config_helpers import get_config_data, get_line_name

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
    fully = config.fully
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
        fully=fully,
        alarm=alarm,
        alarm_msg=alarm_msg,
        timestamp=timestamp,
    )
