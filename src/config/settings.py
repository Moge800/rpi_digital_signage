import os
from pydantic import IPvAnyAddress, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


class Settings(BaseSettings):
    """アプリケーション設定 (Pydantic Settings)

    .envファイルから環境変数を読み込み、型安全な設定管理を提供する。

    Attributes:
        PLC_IP: PLCのIPアドレス
        PLC_PORT: PLCのポート番号 (1-65535)
        AUTO_RECONNECT: PLC切断時の自動再接続フラグ
        RECONNECT_RETRY: 再接続試行回数 (0-10)
        RECONNECT_DELAY: 再接続試行間隔(秒) (0-60)
        DEBUG_DUMMY_READ: ダミーデータ読み取りモード
        USE_PLC: PLC使用フラグ (Falseの場合はダミーデータ)
        LINE_NAME: ライン名 (機種マスタJSONファイル名と対応)
        REFRESH_INTERVAL: フロントエンド自動更新間隔(秒)
        LOG_LEVEL: ログレベル (DEBUG/INFO/WARNING/ERROR)
    """

    PLC_IP: IPvAnyAddress
    PLC_PORT: int = Field(gt=0, le=65535)  # 1-65535の範囲
    AUTO_RECONNECT: bool = True
    RECONNECT_RETRY: int = Field(ge=0, le=10)  # 0-10回の範囲
    RECONNECT_DELAY: float = Field(ge=0.0, le=60.0)  # 0-60秒の範囲
    DEBUG_DUMMY_READ: bool = False
    USE_PLC: bool = True
    LINE_NAME: str = "NONAME"
    REFRESH_INTERVAL: float = 10.0
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def __init__(self, **kwargs) -> None:
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

    TIME_DEVICE: str = "D210"
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

    def __init__(self, **kwargs) -> None:
        # .envファイルの存在チェック
        if not os.path.exists(".env") and not kwargs:
            raise FileNotFoundError(
                "\n❌ .env file not found.\n"
                "Please copy .env.example to .env and configure it:\n"
                "  cp .env.example .env  (Linux/Mac)\n"
                "  Copy-Item .env.example .env  (Windows)\n"
            )
        super().__init__(**kwargs)
