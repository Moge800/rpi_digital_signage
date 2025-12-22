import time
import socket
from functools import wraps
from pymcprotocol import Type3E
from .base import BasePLCClient
from config.settings import Settings
from backend.logging import plc_logger as logger
from typing import Any, Callable, TypeAlias

Func: TypeAlias = Callable[..., Any]

# PLC通信タイムアウト設定（秒）
PLC_SOCKET_TIMEOUT = 5  # ソケット読み書きタイムアウト
PLC_CONNECT_TIMEOUT = 3  # 接続タイムアウト


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
        except (ConnectionError, OSError, TimeoutError, socket.timeout) as e:
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
            ) in ["read_words", "read_bits", "read_dwords"]:
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
            elif _func_name == "read_dwords":
                size = kwargs.get("size", args[1] if len(args) > 1 else 1)
                return [0] * size  # ダミーのダブルワードデータ
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
        # ソケットタイムアウトを設定（デフォルト2秒は短すぎる場合がある）
        self.plc.soc_timeout = PLC_SOCKET_TIMEOUT
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
        ConnectionRefusedError時は、RECONNECT_RETRY設定値の回数までリトライする。

        Returns:
            bool: 接続成功時True、失敗時False
        """
        for attempt in range(self.settings.RECONNECT_RETRY):
            try:
                self.plc.connect(str(self.settings.PLC_IP), self.settings.PLC_PORT)
                # TCPキープアライブを有効化（long-lived connection対策）
                self._enable_keepalive()
                logger.info(
                    f"Connected to PLC at {self.settings.PLC_IP}:{self.settings.PLC_PORT}"
                )
                self.connected = True
                return True

            except ConnectionRefusedError as e:
                if attempt < self.settings.RECONNECT_RETRY - 1:
                    logger.warning(
                        f"Connection refused (attempt {attempt + 1}/{self.settings.RECONNECT_RETRY}): {e}. "
                        "PLC may be starting up, retrying in 5 seconds..."
                    )
                    time.sleep(5)
                else:
                    logger.error(
                        f"Failed to connect to PLC after {self.settings.RECONNECT_RETRY} attempts: {e}"
                    )
                    self.connected = False
                    return False

            except (ConnectionError, OSError, TimeoutError) as e:
                logger.error(f"Failed to connect to PLC: {e}")
                self.connected = False
                return False

        # ループが全て終わった場合（想定外だが安全のため）
        self.connected = False
        return False

    def _enable_keepalive(self) -> None:
        """TCPキープアライブを有効化する

        長時間接続でのhalf-open状態を検出するため、
        OSレベルのTCPキープアライブを設定する。
        """
        try:
            sock = self.plc._sock
            if sock is None:
                return

            # TCPキープアライブを有効化
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

            # Linux固有のキープアライブ設定
            # TCP_KEEPIDLE: 最初のキープアライブまでのアイドル時間（秒）
            # TCP_KEEPINTVL: キープアライブの間隔（秒）
            # TCP_KEEPCNT: 切断判定までのキープアライブ回数
            if hasattr(socket, "TCP_KEEPIDLE"):
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)
            if hasattr(socket, "TCP_KEEPINTVL"):
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
            if hasattr(socket, "TCP_KEEPCNT"):
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)

            logger.debug("TCP keepalive enabled")
        except (OSError, AttributeError) as e:
            logger.warning(f"Failed to enable TCP keepalive: {e}")

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
        ConnectionRefusedError時は、PLCポート開放を待つため
        より長い待機時間（15秒）を使用する。

        Returns:
            bool: 再接続成功時True、全試行失敗時False

        Note:
            AUTO_RECONNECT=trueの場合、read_words/read_bits実行時に
            自動的にこのメソッドが呼び出される。
        """
        for i in range(self.settings.RECONNECT_RETRY):
            logger.info(f"Reconnect attempt {i+1}/{self.settings.RECONNECT_RETRY}...")

            try:
                self.disconnect()
                # 直接PLC接続を試みる（connect()の内部リトライを避けるため）
                self.plc.connect(str(self.settings.PLC_IP), self.settings.PLC_PORT)
                self._enable_keepalive()  # TCPキープアライブを有効化
                logger.info("Reconnect succeeded.")
                self.connected = True
                return True

            except ConnectionRefusedError as e:
                # PLCポートが開いていない（PLC起動中の可能性）
                logger.warning(
                    f"Reconnect attempt {i+1} port refused: {e}. "
                    "PLC may be starting up, waiting longer..."
                )
                self.connected = False
                # PLCの起動を待つため、通常より長く待機（15秒）
                time.sleep(15)
                continue
            except (ConnectionError, OSError, TimeoutError, socket.timeout) as e:
                logger.warning(f"Reconnect attempt {i+1} failed: {e}")
                self.connected = False
                time.sleep(self.settings.RECONNECT_DELAY)

        logger.error("Failed to reconnect after retries.")
        self.connected = False
        return False

    def ensure_connected(self) -> bool:
        """PLC接続が有効であることを確認し、必要なら再接続する

        長時間稼働時のコネクション切断対策。読み込み前に呼び出すことで
        staleなコネクションを検出・復旧する。

        Returns:
            bool: 接続が有効（または再接続成功）ならTrue
        """
        if not self.connected:
            logger.warning("PLC not connected, attempting to reconnect...")
            return self.reconnect()

        # 接続済みでも実際に通信できるか軽量チェック
        try:
            # SD0（CPUモデル名）を読む = 軽量なヘルスチェック
            # タイムアウトはsoc_timeout（5秒）で発生する
            self.plc.batchread_wordunits("SD0", 1)
            return True
        except (ConnectionError, OSError, TimeoutError, socket.timeout) as e:
            logger.warning(f"PLC connection stale, reconnecting: {e}")
            self.connected = False
            return self.reconnect()
        except Exception as e:
            # 予期せぬエラーもキャッチしてログ
            logger.error(f"Unexpected error in health check: {e}")
            self.connected = False
            return self.reconnect()

    def _ensure_connection(self) -> None:
        """PLC接続が確立されていることを保証するユーティリティメソッド

        Raises:
            ConnectionError: PLC未接続時
        """
        if not self.connected:
            raise ConnectionError("Not connected to PLC.")

    @debug_dummy_read
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

    @debug_dummy_read
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

    @debug_dummy_read
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
