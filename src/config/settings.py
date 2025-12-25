import os
from enum import Enum
from pydantic import IPvAnyAddress, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Any


class Theme(str, Enum):
    """UIテーマ

    Attributes:
        DARK: ダークモード (黒背景)
        LIGHT: ライトモード (白背景)
    """

    DARK = "dark"
    LIGHT = "light"


class LogLevel(str, Enum):
    """ログレベル

    Attributes:
        DEBUG: デバッグ情報
        INFO: 通常情報
        WARNING: 警告
        ERROR: エラー
    """

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class Settings(BaseSettings):
    """アプリケーション設定 (Pydantic Settings)

    .envファイルから環境変数を読み込み、型安全な設定管理を提供する。

    Attributes:
        PLC_IP: PLCのIPアドレス
        PLC_PORT: PLCのポート番号 (1-65535)
        AUTO_RECONNECT: PLC切断時の自動再接続フラグ
        RECONNECT_RETRY: 再接続試行回数 (0-10)
        RECONNECT_RESTART: 再接続失敗後にアプリケーションを再起動するかどうかのフラグ
        RECONNECT_DELAY: 再接続試行間隔(秒) (0-60) - reconnect()での待機時間
        DEBUG_DUMMY_READ: ダミーデータ読み取りモード
        USE_PLC: PLC使用フラグ (Falseの場合はダミーデータ)
        LINE_NAME: ライン名 (機種マスタJSONファイル名と対応)
        REFRESH_INTERVAL: フロントエンド自動更新間隔(秒)
        LOG_LEVEL: ログレベル (LogLevel Enum)
        THEME: UIテーマ (Theme Enum: DARK/LIGHT)
        KIOSK_MODE: Kioskモード (True: フルスクリーン自動起動, False: 通常モード)
        API_HOST: APIサーバーホスト (デフォルト: 127.0.0.1)
        API_PORT: APIサーバーポート (デフォルト: 8000)
        PLC_FETCH_TIMEOUT: PLC通信タイムアウト秒数 (デフォルト: 3.0)
        PLC_FETCH_FAILURE_LIMIT: 連続失敗でプロセス終了する回数 (デフォルト: 5)
        ALLOW_FRONTEND_RESTART: フロントエンドからの再起動許可フラグ
        WATCHDOG_INTERVAL: Watchdogのヘルスチェック間隔 (秒)
        WATCHDOG_FAILURE_LIMIT: Watchdogが再起動するまでの失敗回数
        WATCHDOG_RESTART_COOLDOWN: 再起動クールダウン時間 (秒)
        FRONTEND_API_TIMEOUT: フロントエンドのAPI通信タイムアウト (秒)
    """

    PLC_IP: IPvAnyAddress
    PLC_PORT: int = Field(gt=0, le=65535)  # 1-65535の範囲
    AUTO_RECONNECT: bool = True
    RECONNECT_RETRY: int = Field(ge=0, le=10)  # 0-10回の範囲
    RECONNECT_RESTART: bool = False
    RECONNECT_DELAY: float = Field(ge=0.0, le=60.0)  # 0-60秒の範囲
    DEBUG_DUMMY_READ: bool = False
    USE_PLC: bool = True
    LINE_NAME: str = "NONAME"
    REFRESH_INTERVAL: float = 10.0
    LOG_LEVEL: LogLevel = LogLevel.INFO
    THEME: Theme = Theme.DARK
    KIOSK_MODE: bool = False
    API_HOST: str = "127.0.0.1"
    API_PORT: int = Field(default=8000, gt=0, le=65535)

    # PLC通信タイムアウト設定
    PLC_FETCH_TIMEOUT: float = Field(default=3.0, ge=1.0, le=30.0)
    PLC_PING_TIMEOUT: float = Field(default=2.0, ge=0.5, le=10.0)  # ping_plc用(短め)
    PLC_FETCH_FAILURE_LIMIT: int = Field(default=5, ge=1, le=20)

    # フロントエンドからの再起動許可
    ALLOW_FRONTEND_RESTART: bool = False

    # Watchdog設定
    WATCHDOG_INTERVAL: float = Field(default=10.0, ge=5.0, le=60.0)
    WATCHDOG_FAILURE_LIMIT: int = Field(default=3, ge=1, le=10)
    WATCHDOG_RESTART_COOLDOWN: float = Field(default=1800.0, ge=60.0, le=7200.0)

    # フロントエンドAPI通信設定
    FRONTEND_API_TIMEOUT: float = Field(default=3.0, ge=1.0, le=30.0)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def __init__(self: Any, **kwargs: Any) -> None:
        # 環境変数プレセット: DEBUG_LOG が真なら LOG_LEVEL を DEBUG にする
        # ユーザーが明示的に LOG_LEVEL を設定している場合は上書きしない
        if "LOG_LEVEL" not in kwargs and os.getenv("LOG_LEVEL") is None:
            debug_env = os.getenv("DEBUG_LOG")
            if isinstance(debug_env, str) and debug_env.lower() in (
                "1",
                "true",
                "yes",
                "on",
            ):
                kwargs.setdefault("LOG_LEVEL", LogLevel.DEBUG)

        # .envファイルの存在チェック
        if not os.path.exists(".env") and not kwargs:
            raise FileNotFoundError(
                "\n❌ .env file not found.\n"
                "Please copy .env.example to .env and configure it:\n"
                "  cp .env.example .env  (Linux/Mac)\n"
                "  Copy-Item .env.example .env  (Windows)\n"
            )

        super().__init__(**kwargs)


class PLCDeviceList(BaseSettings):
    """PLCデバイスアドレス設定 (Pydantic Settings)

    各データ項目のPLCデバイスアドレスを管理する。
    .envファイルから読み込み、実機環境に合わせて設定する。

    Attributes:
        TIME_DEVICE: タイムスタンプ格納デバイス (BCD形式YMDhms)
        PRODUCTION_TYPE_DEVICE: 生産機種番号格納デバイス
        PLAN_DEVICE: 計画生産数格納デバイス
        ACTUAL_DEVICE: 実績生産数格納デバイス
        ALARM_FLAG_DEVICE: アラームフラグ格納デバイス
        ALARM_MSG_DEVICE: アラームメッセージ格納デバイス
        IN_OPERATING_DEVICE: 稼働中フラグ格納デバイス
    """

    TIME_DEVICE: str = "SD210"
    PRODUCTION_TYPE_DEVICE: str = ""
    PLAN_DEVICE: str = ""
    ACTUAL_DEVICE: str = ""
    ALARM_FLAG_DEVICE: str = ""
    ALARM_MSG_DEVICE: str = ""
    IN_OPERATING_DEVICE: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def __init__(self: Any, **kwargs: Any) -> None:
        # .envファイルの存在チェック
        if not os.path.exists(".env") and not kwargs:
            raise FileNotFoundError(
                "\n❌ .env file not found.\n"
                "Please copy .env.example to .env and configure it:\n"
                "  cp .env.example .env  (Linux/Mac)\n"
                "  Copy-Item .env.example .env  (Windows)\n"
            )
        super().__init__(**kwargs)


class WatchdogSettings(BaseSettings):
    """Watchdog専用設定 (軽量)

    Watchdogプロセスが必要とする最小限の設定のみを読み込む。
    API側の設定との混在を避けるため分離。

    Attributes:
        API_HOST: APIサーバーホスト
        API_PORT: APIサーバーポート
        WATCHDOG_INTERVAL: ヘルスチェック間隔 (秒)
        WATCHDOG_FAILURE_LIMIT: 再起動までの失敗回数
        WATCHDOG_RESTART_COOLDOWN: 再起動クールダウン初期値 (秒) - バックオフの先頭値
        WATCHDOG_STARTUP_GRACE: 起動後の猶予時間 (秒)
        WATCHDOG_BACKOFF_MAX: バックオフ最大値 (秒)
        WATCHDOG_API_STARTUP_TIMEOUT: API起動待機の最大秒数
        WATCHDOG_API_STARTUP_CHECK_INTERVAL: API起動確認の間隔 (秒)
        WATCHDOG_READY_CHECK_INTERVAL: /readyチェック間隔 (秒, 0で無効)
    """

    API_HOST: str = "127.0.0.1"
    API_PORT: int = Field(default=8000, gt=0, le=65535)
    WATCHDOG_INTERVAL: float = Field(default=10.0, ge=5.0, le=60.0)
    WATCHDOG_FAILURE_LIMIT: int = Field(default=3, ge=1, le=10)
    WATCHDOG_RESTART_COOLDOWN: float = Field(default=60.0, ge=30.0, le=300.0)
    WATCHDOG_STARTUP_GRACE: float = Field(default=60.0, ge=30.0, le=180.0)
    WATCHDOG_BACKOFF_MAX: float = Field(default=1800.0, ge=300.0, le=7200.0)
    WATCHDOG_API_STARTUP_TIMEOUT: int = Field(default=15, ge=5, le=60)
    WATCHDOG_API_STARTUP_CHECK_INTERVAL: float = Field(default=1.0, ge=0.5, le=5.0)
    WATCHDOG_READY_CHECK_INTERVAL: float = Field(
        default=60.0, ge=0.0, le=300.0
    )  # 0で無効

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def __init__(self: Any, **kwargs: Any) -> None:
        if not os.path.exists(".env") and not kwargs:
            raise FileNotFoundError(
                "\n❌ .env file not found.\n"
                "Please copy .env.example to .env and configure it:\n"
                "  cp .env.example .env  (Linux/Mac)\n"
                "  Copy-Item .env.example .env  (Windows)\n"
            )
        super().__init__(**kwargs)
