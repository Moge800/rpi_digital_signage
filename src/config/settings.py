import os
from pydantic import IPvAnyAddress, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PLC_IP: IPvAnyAddress
    PLC_PORT: int = Field(gt=0, le=65535)  # 1-65535の範囲
    AUTO_RECONNECT: bool = True
    RECONNECT_RETRY: int = Field(ge=0, le=10)  # 0-10回の範囲
    RECONNECT_DELAY: float = Field(ge=0.0, le=60.0)  # 0-60秒の範囲
    DEBUG_DUMMY_READ: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def __init__(self, **kwargs):
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
    TIME_DEVICE: str = "D210"
    PRODUCTION_TYPE_DEVICE: str = ""
    PLAN_DEVICE: str = ""
    ACTUAL_DEVICE: str = ""
    ALARM_DEVICE: str = ""
    IN_OPERATING_DEVICE: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def __init__(self, **kwargs):
        # .envファイルの存在チェック
        if not os.path.exists(".env") and not kwargs:
            raise FileNotFoundError(
                "\n❌ .env file not found.\n"
                "Please copy .env.example to .env and configure it:\n"
                "  cp .env.example .env  (Linux/Mac)\n"
                "  Copy-Item .env.example .env  (Windows)\n"
            )
        super().__init__(**kwargs)
