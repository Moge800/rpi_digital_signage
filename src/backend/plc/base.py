from abc import ABC, abstractmethod


class BasePLCClient(ABC):
    @abstractmethod
    def connect(self): ...

    @abstractmethod
    def disconnect(self): ...

    @abstractmethod
    def read_words(self, device_name: str, size: int): ...

    @abstractmethod
    def read_bits(self, device_name: str, size: int): ...

    @abstractmethod
    def reconnect(self) -> bool: ...
