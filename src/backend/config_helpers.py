"""設定取得ヘルパー関数

環境変数やPydantic Settingsから各種設定値を取得する関数群。
モジュールレベルでSettingsをシングルトン化し、効率的にアクセス。
"""

from config.production_config import ProductionConfigManager
from config.settings import LogLevel, Settings
from schemas import ProductionTypeConfig

# 設定のシングルトンインスタンス（モジュールレベルで1回だけ初期化）
_settings = Settings()

# ProductionConfigManagerのシングルトンインスタンス（モジュールレベルで1回だけ初期化）
_config_manager = ProductionConfigManager()


def get_use_plc() -> bool:
    """USE_PLC設定を取得

    Returns:
        bool: PLC使用フラグ
    """
    return _settings.USE_PLC


def get_line_name() -> str:
    """LINE_NAME設定を取得

    Returns:
        str: ライン名
    """
    return _settings.LINE_NAME


def get_refresh_interval() -> float:
    """フロントエンドのリフレッシュ間隔（秒）を取得

    Returns:
        float: リフレッシュ間隔（秒）
    """
    return _settings.REFRESH_INTERVAL


def get_log_level() -> LogLevel:
    """ログレベルを取得

    Returns:
        LogLevel: ログレベル (Enum)
    """
    return _settings.LOG_LEVEL


def get_kiosk_mode() -> bool:
    """Kioskモード設定を取得

    Returns:
        bool: Kioskモードが有効ならTrue
    """
    return _settings.KIOSK_MODE


def get_config_data(production_type: int) -> ProductionTypeConfig:
    """指定された機種番号に対応する機種設定を取得する

    モジュールレベルでキャッシュされたProductionConfigManagerを使用。
    config/production_types/{LINE_NAME}.jsonから読み込まれた設定を返す。

    Args:
        production_type: 機種番号 (0-15)

    Returns:
        ProductionTypeConfig: 機種設定オブジェクト
            - production_type: 機種番号
            - name: 機種名
            - fully: 1パレットあたりの積載数
            - seconds_per_product: 1個あたりの生産時間(秒)

    Raises:
        ValueError: 機種番号が範囲外または未定義の場合

    Note:
        パフォーマンス最適化のため、繰り返し呼び出しても初期化は1回のみ。

    Examples:
        >>> config = get_config_data(1)
        >>> print(config.name)  # "機種A"
        >>> print(config.fully)  # 2800
    """
    return _config_manager.get_config(production_type)
