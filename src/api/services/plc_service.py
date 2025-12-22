"""PLC通信サービス

PLCClientをラップし、APIサーバー内で一元管理するシングルトンサービス。
複数リクエストからの同時アクセスを防ぎ、安全なPLC通信を提供。
"""

import random
import threading
from datetime import datetime
from typing import Any, Callable

from backend.logging import api_logger as logger
from backend.config_helpers import get_use_plc, get_config_data
from config.settings import Settings


class PLCService:
    """PLC通信サービス (シングルトン)

    APIサーバー内でPLC通信を一元管理。
    スレッドセーフなアクセスを提供。
    """

    _instance: "PLCService | None" = None
    _lock = threading.Lock()
    _initialized: bool = False

    def __new__(cls) -> "PLCService":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        self._client: Any = None
        self._use_plc = get_use_plc()
        self._settings = Settings()
        self._last_update: datetime | None = None
        self._access_lock = threading.Lock()

        # 遅延インポート用の関数参照
        self._fetch_production_data: Callable[..., Any] | None = None
        self._fetch_production_timestamp: Callable[..., datetime] | None = None
        self._get_plc_device_dict: Callable[[], dict[str, str]] | None = None

        logger.info(f"PLCService initialized (USE_PLC={self._use_plc})")

    def initialize(self) -> None:
        """PLC接続を初期化"""
        # 遅延インポート
        from backend.plc.plc_client import get_plc_client
        from backend.plc.plc_fetcher import (
            fetch_production_data,
            fetch_production_timestamp,
            get_plc_device_dict,
        )

        self._fetch_production_data = fetch_production_data
        self._fetch_production_timestamp = fetch_production_timestamp
        self._get_plc_device_dict = get_plc_device_dict

        if self._use_plc:
            try:
                self._client = get_plc_client()
                logger.info("PLC client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize PLC client: {e}")
                self._client = None

    def shutdown(self) -> None:
        """PLC接続を安全に切断"""
        # タイムアウト付きでロック取得を試みる (デッドロック防止)
        acquired = self._access_lock.acquire(timeout=5.0)
        try:
            if self._client is not None:
                try:
                    if hasattr(self._client, "connected") and self._client.connected:
                        self._client.disconnect()
                        logger.info("PLC connection closed safely")
                except Exception as e:
                    logger.warning(f"Error during PLC disconnect: {e}")
                finally:
                    self._client = None
        finally:
            if acquired:
                self._access_lock.release()
            else:
                logger.warning("Could not acquire lock for shutdown (timeout)")
                # ロック取得できなくてもクライアント参照はクリア
                self._client = None

    def get_production_data(self) -> Any:
        """生産データを取得

        Returns:
            ProductionData: 生産データ

        Note:
            USE_PLC=false の場合はダミーデータを返す
        """
        with self._access_lock:
            self._last_update = datetime.now()

            if self._use_plc and self._client is not None:
                if self._fetch_production_data is None:
                    raise RuntimeError(
                        "PLCService not initialized. Call initialize() first."
                    )
                return self._fetch_production_data(self._client)
            else:
                return self._generate_dummy_data()

    def get_plc_timestamp(self) -> datetime | None:
        """PLCから時刻を取得

        Returns:
            datetime | None: PLC時刻 (USE_PLC=false時はNone)
        """
        if not self._use_plc or self._client is None:
            return None

        with self._access_lock:
            if (
                self._get_plc_device_dict is None
                or self._fetch_production_timestamp is None
            ):
                return None
            time_device = self._get_plc_device_dict()["TIME_DEVICE"]
            if not time_device:
                return None
            return self._fetch_production_timestamp(self._client, time_device)

    def get_status(self) -> dict[str, Any]:
        """サービス状態を取得

        Returns:
            dict: 状態情報
        """
        connected = False
        if self._use_plc and self._client is not None:
            connected = getattr(self._client, "connected", False)

        return {
            "plc_connected": connected,
            "use_plc": self._use_plc,
            "line_name": self._settings.LINE_NAME,
            "last_update": (
                self._last_update.isoformat() if self._last_update else None
            ),
        }

    def _generate_dummy_data(self) -> Any:
        """ダミーデータを生成 (開発/テスト用)"""
        from schemas import ProductionData
        from backend.calculators import calculate_remain_pallet

        # ダミーデータ生成用定数
        SECONDS_PER_PRODUCT = 1.2
        ALARM_THRESHOLD = 8000
        ALARM_PROBABILITY = 0.5
        MAX_PRODUCTION_TYPE = 2

        production_type = random.randint(0, MAX_PRODUCTION_TYPE)

        try:
            config = get_config_data(production_type)
        except ValueError:
            config = get_config_data(0)

        plan = 45000  # 固定値
        actual = random.randint(0, plan)
        remain = max(0, plan - actual)
        fully = config.fully
        remain_seconds = remain * SECONDS_PER_PRODUCT
        remain_min = int(remain_seconds / 60.0)

        is_alarm = actual > ALARM_THRESHOLD and random.random() < ALARM_PROBABILITY

        return ProductionData(
            line_name=self._settings.LINE_NAME,
            production_type=production_type,
            production_name=config.name,
            plan=plan,
            actual=actual,
            remain_pallet=calculate_remain_pallet(
                plan, actual, production_type=production_type, decimals=1
            ),
            remain_min=remain_min,
            fully=fully,
            in_operating=True,
            alarm=is_alarm,
            alarm_msg="【テスト】アラーム発生中" if is_alarm else "",
            timestamp=datetime.now(),
        )


# シングルトンインスタンス
plc_service = PLCService()
