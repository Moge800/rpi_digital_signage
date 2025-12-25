"""PLC通信サービス

PLCClientをラップし、APIサーバー内で一元管理するシングルトンサービス。
複数リクエストからの同時アクセスを防ぎ、安全なPLC通信を提供。

タイムアウト機構:
- PLC通信はスレッドで分離して実行
- タイムアウト (デフォルト3秒) を超えると失敗として扱う
- 連続失敗回数が閾値を超えるとプロセス終了
"""

import os
import random
import signal
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import datetime
from typing import Any, Callable

from backend.logging import api_logger as logger
from backend.config_helpers import get_use_plc, get_config_data
from config.settings import Settings


class PLCCommunicationTimeoutError(Exception):
    """PLC通信タイムアウトエラー"""

    pass


class PLCService:
    """PLC通信サービス (シングルトン)

    APIサーバー内でPLC通信を一元管理。
    スレッドセーフなアクセスとタイムアウト機構を提供。
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

        # タイムアウト設定
        self._fetch_timeout = self._settings.PLC_FETCH_TIMEOUT
        self._failure_limit = self._settings.PLC_FETCH_FAILURE_LIMIT

        # 連続失敗カウンタ
        self._consecutive_failures = 0

        # スレッドプールエグゼキュータ (PLC通信用)
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="plc")

        # 遅延インポート用の関数参照
        self._fetch_production_data: Callable[..., Any] | None = None
        self._fetch_production_timestamp: Callable[..., datetime] | None = None
        self._get_plc_device_dict: Callable[[], dict[str, str]] | None = None

        logger.info(
            f"PLCService initialized (USE_PLC={self._use_plc}, "
            f"timeout={self._fetch_timeout}s, failure_limit={self._failure_limit})"
        )

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
        # スレッドプールをシャットダウン
        self._executor.shutdown(wait=False, cancel_futures=True)

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

    def _execute_with_timeout(
        self, func: Callable[..., Any], operation_name: str, *args: Any, **kwargs: Any
    ) -> Any:
        """PLC通信をタイムアウト付きで実行

        Args:
            func: 実行する関数
            operation_name: 操作名 (ログ出力用)
            *args: 関数の位置引数
            **kwargs: 関数のキーワード引数

        Returns:
            関数の戻り値

        Raises:
            PLCCommunicationTimeoutError: タイムアウト時
        """
        start_time = time.perf_counter()
        logger.debug(f"PLC communication started: {operation_name}")

        try:
            future = self._executor.submit(func, *args, **kwargs)
            result = future.result(timeout=self._fetch_timeout)

            elapsed = time.perf_counter() - start_time
            logger.debug(
                f"PLC communication completed: {operation_name} ({elapsed:.3f}s)"
            )

            # 成功したので連続失敗カウンタをリセット
            self._consecutive_failures = 0
            return result

        except FuturesTimeoutError:
            elapsed = time.perf_counter() - start_time
            logger.error(
                f"PLC communication timeout: {operation_name} "
                f"(elapsed={elapsed:.3f}s, limit={self._fetch_timeout}s)"
            )
            self._handle_failure()
            raise PLCCommunicationTimeoutError(
                f"{operation_name} timed out after {self._fetch_timeout}s"
            )

        except Exception as e:
            elapsed = time.perf_counter() - start_time
            logger.error(
                f"PLC communication error: {operation_name} " f"({elapsed:.3f}s): {e}"
            )
            self._handle_failure()
            raise

    def _handle_failure(self) -> None:
        """連続失敗時の処理

        連続失敗回数をインクリメントし、閾値を超えたらプロセス終了
        """
        self._consecutive_failures += 1
        logger.warning(
            f"PLC communication failure count: {self._consecutive_failures}/{self._failure_limit}"
        )

        if self._consecutive_failures >= self._failure_limit:
            logger.critical(
                f"PLC communication failed {self._consecutive_failures} times consecutively. "
                "Terminating API process for watchdog recovery."
            )
            # Watchdog に再起動を任せるため、プロセスを自発的に終了
            self._terminate_process()

    def _terminate_process(self) -> None:
        """プロセスを終了する

        SIGTERMを送信してgracefulにシャットダウン
        """
        logger.info("Initiating process termination...")
        try:
            self.shutdown()
        except Exception as e:
            logger.warning(f"Error during shutdown before termination: {e}")

        # SIGTERMを自分自身に送信
        os.kill(os.getpid(), signal.SIGTERM)

    def get_production_data(self) -> Any:
        """生産データを取得

        Returns:
            ProductionData: 生産データ

        Note:
            USE_PLC=false の場合はダミーデータを返す
            PLC通信はタイムアウト付きスレッドで実行
        """
        with self._access_lock:
            self._last_update = datetime.now()

            if self._use_plc and self._client is not None:
                if self._fetch_production_data is None:
                    raise RuntimeError(
                        "PLCService not initialized. Call initialize() first."
                    )
                return self._execute_with_timeout(
                    self._fetch_production_data,
                    "fetch_production_data",
                    self._client,
                )
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
            return self._execute_with_timeout(
                self._fetch_production_timestamp,
                "fetch_production_timestamp",
                self._client,
                time_device,
            )

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
            "consecutive_failures": self._consecutive_failures,
        }

    def reset_failure_count(self) -> None:
        """連続失敗カウンタをリセット (テスト用)"""
        self._consecutive_failures = 0

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
