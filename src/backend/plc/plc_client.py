import time
from functools import wraps
from pymcprotocol import Type3E
from .base import BasePLCClient
from ...config.settings import Settings
from ..logging import plc_logger as logger


def auto_reconnect(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
            if getattr(self.settings, "AUTO_RECONNECT", False):
                logger.info("Attempting to reconnect...")
                if self.reconnect():
                    # 再接続成功したらもう1回だけリトライ
                    return func(self, *args, **kwargs)
            # ここまで来たら本当にダメなやつ
            logger.error(f"Operation failed after reconnect attempts: {e}")
            raise

    return wrapper


def debug_dummy_read(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if self.settings.DEBUG_DUMMY_READ:
            logger.debug(
                f"Dummy read for {func.__name__} with args: {args}, kwargs: {kwargs}"
            )
            if func.__name__ == "read_words":
                size = kwargs.get("size", args[1] if len(args) > 1 else 1)
                return [0] * size  # ダミーのワードデータ
            elif func.__name__ == "read_bits":
                size = kwargs.get("size", args[1] if len(args) > 1 else 1)
                return [0] * size  # ダミーのビットデータ
        return func(self, *args, **kwargs)

    return wrapper


class PLCClient(BasePLCClient):
    def __init__(self, settings: Settings):
        self.plc = Type3E()
        self.settings = settings
        self.connected = False
        self.connect()

    def connect(self):
        try:
            self.plc.connect(str(self.settings.PLC_IP), self.settings.PLC_PORT)
            logger.info(
                f"Connected to PLC at {self.settings.PLC_IP}:{self.settings.PLC_PORT}"
            )
            self.connected = True
        except Exception as e:
            logger.error(f"Failed to connect to PLC: {e}")
            self.connected = False

    def disconnect(self):
        try:
            self.plc.close()
            logger.info("Disconnected from PLC")
        except Exception as e:
            logger.error(f"Failed to disconnect from PLC: {e}")
        finally:
            self.connected = False

    def reconnect(self) -> bool:
        for i in range(self.settings.RECONNECT_RETRY):
            try:
                logger.info(
                    f"Reconnect attempt {i+1}/{self.settings.RECONNECT_RETRY}..."
                )
                self.disconnect()
                self.connect()
                if self.connected:
                    logger.info("Reconnect succeeded.")
                    return True
            except Exception as e:
                logger.warning(f"Reconnect attempt {i+1} failed: {e}")
            time.sleep(self.settings.RECONNECT_DELAY)
        logger.error("Failed to reconnect after retries.")
        return False

    @auto_reconnect
    def read_words(self, device_name: str, size: int = 1) -> list[int]:
        if not self.connected:
            raise ConnectionError("Not connected to PLC.")
        data = self.plc.batchread_wordunits(device_name, size)
        logger.debug(f"Read words {device_name}: {data}")
        return data

    @auto_reconnect
    def read_bits(self, device_name: str, size: int = 1) -> list[int]:
        if not self.connected:
            raise ConnectionError("Not connected to PLC.")
        data = self.plc.batchread_bitunits(device_name, size)
        logger.debug(f"Read bits {device_name}: {data}")
        return data


_client: PLCClient | None = None


def get_plc_client() -> PLCClient:
    global _client
    if _client is None:
        settings = Settings()  # type: ignore  # .envから読み込む
        _client = PLCClient(settings)
    return _client


if __name__ == "__main__":
    settings = Settings()  # type: ignore  # .envから読み込む
    client = PLCClient(settings)

    try:
        words = client.read_words("D100", 2)
        bits = client.read_bits("X0", 8)
        print("WORDS:", words)
        print("BITS :", bits)
    finally:
        client.disconnect()
