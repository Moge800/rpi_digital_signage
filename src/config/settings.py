import os
from pydantic import IPvAnyAddress, Field
from pydantic_settings import BaseSettings
import dotenv

dotenv.load_dotenv()


class Settings(BaseSettings):
    PLC_IP: IPvAnyAddress
    PLC_PORT: int = Field(gt=0, le=65535)  # 1-65535の範囲
    AUTO_RECONNECT: bool = True
    RECONNECT_RETRY: int = Field(ge=0, le=10)  # 0-10回の範囲
    RECONNECT_DELAY: float = Field(ge=0.0, le=60.0)  # 0-60秒の範囲
    DEBUG_DUMMY_READ: bool = False

    class Config:
        env_file = ".env"
        if not os.path.exists(env_file):
            raise FileNotFoundError(f"{env_file} not found")
