import time
from functools import wraps
from pymcprotocol import Type3E
from .base import BasePLCClient
from config.settings import Settings
from backend.logging import plc_logger as logger


def auto_reconnect(func):
    """PLC通信エラー時に自動再接続を試みるデコレータ

    設定でAUTO_RECONNECT=trueの場合、ConnectionError等の発生時に
    自動的に再接続を試み、成功したら元の処理を1回だけリトライする。

    Args:
        func: デコレート対象の関数

    Returns:
        wrapper: ラップされた関数
    """

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except (ConnectionError, OSError, TimeoutError) as e:
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
    """デバッグモード時にダミーデータを返すデコレータ

    設定でDEBUG_DUMMY_READ=trueの場合、実際のPLC通信を行わず
    ゼロ埋めのダミーデータを返す。PLC未接続環境でのテスト用。

    Args:
        func: デコレート対象の関数

    Returns:
        wrapper: ラップされた関数
    """

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
    """MELSEC Qシリーズ PLC通信クライアント (Type3E)

    シングルトンパターンで実装されており、アプリケーション全体で
    単一のPLC接続を共有する。自動再接続機能とデバッグモードを搭載。

    使用例:
        >>> client = get_plc_client()
        >>> data = client.read_words("D100", size=10)

    Attributes:
        plc (Type3E): pymcprotocolのType3Eインスタンス
        settings (Settings): PLC接続設定
        connected (bool): 接続状態フラグ
    """

    _instance: "PLCClient | None" = None

    def __init__(self, settings: Settings) -> None:
        """PLCClientを初期化し、自動的に接続を試みる

        Args:
            settings: PLC接続設定 (IP, ポート等)
        """
        self.plc = Type3E()
        self.settings = settings
        self.connected = False
        self.connect()

    @classmethod
    def get_instance(cls, settings: Settings | None = None) -> "PLCClient":
        """シングルトンインスタンスを取得

        Args:
            settings: PLC接続設定 (Noneの場合は.envから自動読み込み)

        Returns:
            PLCClient: シングルトンインスタンス
        """
        if cls._instance is None:
            if settings is None:
                settings = Settings()
            cls._instance = cls(settings)
        return cls._instance

    def connect(self) -> bool:
        """PLCに接続する

        設定されたIPアドレスとポートを使用してPLCへの接続を確立する。
        接続成功時はconnectedフラグをTrueに設定する。

        Returns:
            bool: 接続成功時True、失敗時False
        """
        try:
            self.plc.connect(str(self.settings.PLC_IP), self.settings.PLC_PORT)
            logger.info(
                f"Connected to PLC at {self.settings.PLC_IP}:{self.settings.PLC_PORT}"
            )
            self.connected = True
            return True

        except (ConnectionError, OSError, TimeoutError) as e:
            logger.error(f"Failed to connect to PLC: {e}")
            self.connected = False
            return False

        except ConnectionRefusedError as e:
            logger.error(f"Failed to connect to PLC port check and restart PLC: {e}")
            self.connected = False
            return False

    def disconnect(self) -> bool:
        """PLCから切断する

        PLC接続を閉じ、connectedフラグをFalseに設定する。

        Returns:
            bool: 切断成功時True、失敗時False
        """
        try:
            self.plc.close()
            logger.info("Disconnected from PLC")
            return True

        except (ConnectionError, OSError) as e:
            logger.error(f"Failed to disconnect from PLC: {e}")
            return False

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

            except (ConnectionError, OSError, TimeoutError) as e:
                logger.warning(f"Reconnect attempt {i+1} failed: {e}")
            except ConnectionRefusedError as e:
                logger.warning(f"Reconnect attempt {i+1} port check failed: {e}")
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


def get_plc_client() -> PLCClient:
    """PLCクライアントのシングルトンインスタンスを取得"""
    return PLCClient.get_instance()
