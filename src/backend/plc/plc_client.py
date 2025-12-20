import time
from functools import wraps
from pymcprotocol import Type3E
from .base import BasePLCClient
from config.settings import Settings
from backend.logging import plc_logger as logger
from typing import Any, Callable, TypeAlias

Func: TypeAlias = Callable[..., Any]


def func_name(func: Func) -> str:
    """関数の名前を取得するユーティリティ関数

    Args:
        func: 関数オブジェクト

    Returns:
        str: 関数名
    """
    return getattr(func, "__name__", repr(func))


def auto_reconnect(func: Func) -> Func:
    """PLC通信エラー時に自動再接続を試みるデコレータ

    設定でAUTO_RECONNECT=trueの場合、ConnectionError等の発生時に
    自動的に再接続を試み、成功したら元の処理を1回だけリトライする。

    Args:
        func: デコレート対象の関数

    Returns:
        wrapper: ラップされた関数
    """

    @wraps(func)
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        try:
            return func(self, *args, **kwargs)
        except (ConnectionError, OSError, TimeoutError) as e:
            logger.error(f"Error in {func_name(func)}: {e}")
            if getattr(self.settings, "AUTO_RECONNECT", False):
                logger.info("Attempting to reconnect...")
                if self.reconnect():
                    # 再接続成功したらもう1回だけリトライ
                    return func(self, *args, **kwargs)
            # ここまで来たら本当にダメなやつ
            logger.error(f"Operation failed after reconnect attempts: {e}")
            if getattr(self.settings, "RECONNECT_RESTART", False) and func_name(
                func
            ) in ["read_words", "read_bits"]:
                logger.critical("Reconnection failed. Restarting application...")
                from backend.system_utils import restart_system

                restart_system()

            raise

    return wrapper


def debug_dummy_read(func: Func) -> Func:
    """デバッグモード時にダミーデータを返すデコレータ

    設定でDEBUG_DUMMY_READ=trueの場合、実際のPLC通信を行わず
    ゼロ埋めのダミーデータを返す。PLC未接続環境でのテスト用。

    Args:
        func: デコレート対象の関数

    Returns:
        wrapper: ラップされた関数
    """

    @wraps(func)
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        _func_name = func_name(func)
        if self.settings.DEBUG_DUMMY_READ:
            logger.debug(
                f"Dummy read for {_func_name} with args: {args}, kwargs: {kwargs}"
            )
            if _func_name == "read_words":
                size = kwargs.get("size", args[1] if len(args) > 1 else 1)
                return [0] * size  # ダミーのワードデータ
            elif _func_name == "read_bits":
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

    def __del__(self) -> None:
        """デストラクタ: インスタンス破棄時にPLC接続をクローズ

        メモリーリーク防止のため、ガベージコレクション時に自動的に切断する。
        """
        try:
            if hasattr(self, "connected") and self.connected:
                self.disconnect()
                logger.debug("PLCClient cleaned up in destructor")
        except Exception as e:
            # デストラクタ内での例外は握りつぶす（Python仕様）
            logger.warning(f"Error during PLCClient cleanup: {e}")

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
        """PLC接続を再確立する

        設定されたRECONNECT_RETRY回数分、再接続を試みる。
        各試行の間にはRECONNECT_DELAY秒の遅延を挟む。

        Returns:
            bool: 再接続成功時True、全試行失敗時False

        Note:
            AUTO_RECONNECT=trueの場合、read_words/read_bits実行時に
            自動的にこのメソッドが呼び出される。
        """
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

    def _ensure_connection(self) -> None:
        """PLC接続が確立されていることを保証するユーティリティメソッド

        Raises:
            ConnectionError: PLC未接続時
        """
        if not self.connected:
            raise ConnectionError("Not connected to PLC.")

    @auto_reconnect
    def read_words(self, device_name: str, size: int = 1) -> list[int]:
        """PLCからワードデバイスを読み取る

        Args:
            device_name: デバイス名 (例: "D100", "SD210")
            size: 読み取るワード数 (デフォルト: 1)

        Returns:
            list[int]: 読み取ったワードデータのリスト (length=size)

        Raises:
            ConnectionError: PLC未接続または通信エラー時

        Note:
            @auto_reconnectデコレータにより、通信エラー時は
            自動的に再接続を試みる (AUTO_RECONNECT=true時)。
        """
        self._ensure_connection()
        data = self.plc.batchread_wordunits(device_name, size)
        logger.debug(f"Read words {device_name}: {data}")
        return data

    @auto_reconnect
    def read_bits(self, device_name: str, size: int = 1) -> list[int]:
        """PLCからビットデバイスを読み取る

        Args:
            device_name: デバイス名 (例: "M100", "X10")
            size: 読み取るビット数 (デフォルト: 1)

        Returns:
            list[int]: 読み取ったビットデータのリスト (0 or 1, length=size)

        Raises:
            ConnectionError: PLC未接続または通信エラー時

        Note:
            @auto_reconnectデコレータにより、通信エラー時は
            自動的に再接続を試みる (AUTO_RECONNECT=true時)。
        """
        self._ensure_connection()
        data = self.plc.batchread_bitunits(device_name, size)
        logger.debug(f"Read bits {device_name}: {data}")
        return data

    @auto_reconnect
    def read_dwords(self, device_name: str, size: int = 1) -> list[int]:
        """PLCからダブルワードデバイスを読み取る

        Args:
            device_name: デバイス名 (例: "D100", "SD210")
            size: 読み取るダブルワード数 (デフォルト: 1)
                1ダブルワード = 2ワード = 32ビット

        Returns:
            list[int]: 読み取ったダブルワードデータのリスト (length=size)
                符号付き32ビット整数 (-2147483648 ~ 2147483647)

        Raises:
            ConnectionError: PLC未接続または通信エラー時

        Note:
            @auto_reconnectデコレータにより、通信エラー時は
            自動的に再接続を試みる (AUTO_RECONNECT=true時)。
            リトルエンディアン形式で2ワードを32ビット整数に変換する。
        """
        self._ensure_connection()
        data = self.plc.batchread_wordunits(device_name, size * 2)
        # 連続する2ワード(16ビット×2)を32ビット整数に変換
        # 例: [0x1234, 0x5678] → 0x56781234 (リトルエンディアン)
        dwords = [
            int.from_bytes(
                # 各ワードを2バイトに分解してリトルエンディアンで結合
                b"".join(
                    word.to_bytes(2, byteorder="little")
                    for word in data[i * 2 : i * 2 + 2]
                ),
                byteorder="little",
                signed=True,
            )
            for i in range(size)
        ]
        logger.debug(f"Read dwords {device_name}: {dwords}")
        return dwords


def get_plc_client() -> PLCClient:
    """PLCクライアントのシングルトンインスタンスを取得

    Returns:
        PLCClient: シングルトンインスタンス (既に接続済み)

    Note:
        初回呼び出し時に.envファイルからSettings()を読み込み、
        PLC接続を確立する。2回目以降は既存インスタンスを返す。
    """
    return PLCClient.get_instance()
