from abc import ABC, abstractmethod


class BasePLCClient(ABC):
    """PLC通信クライアントの抽象基底クラス

    新しいPLC種別を追加する場合は、このクラスを継承して実装する。
    現在の実装: PLCClient (MELSEC Qシリーズ Type3E)
    """

    @abstractmethod
    def connect(self) -> bool:
        """PLCに接続する

        Returns:
            bool: 接続成功時True、失敗時False
        """
        ...

    @abstractmethod
    def disconnect(self) -> bool:
        """PLCから切断する

        Returns:
            bool: 切断成功時True、失敗時False
        """
        ...

    @abstractmethod
    def read_words(self, device_name: str, size: int) -> list[int]:
        """ワードデバイスから複数ワードを読み取る

        Args:
            device_name: デバイス名 (例: "D100")
            size: 読み取るワード数

        Returns:
            list[int]: 読み取ったワードデータのリスト length=size
        """
        ...

    @abstractmethod
    def read_bits(self, device_name: str, size: int) -> list[int]:
        """ビットデバイスから複数ビットを読み取る

        Args:
            device_name: デバイス名 (例: "M100")
            size: 読み取るビット数

        Returns:
            list[int]: 読み取ったビットデータのリスト (0 or 1) length=size
        """
        ...

    @abstractmethod
    def reconnect(self) -> bool:
        """PLC再接続を試みる

        Returns:
            bool: 再接続成功時True、失敗時False
        """
        ...
