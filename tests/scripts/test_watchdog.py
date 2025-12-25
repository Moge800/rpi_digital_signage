"""Watchdogのテスト

APIWatchdogクラスの主要ロジックをテスト。
実際のプロセス起動は行わず、モックを使用。
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, PropertyMock
import pytest


class TestWatchdogSettings:
    """WatchdogSettings のテスト"""

    def test_watchdog_settings_loads_defaults(self):
        """デフォルト値が正しく読み込まれるか"""
        from config.settings import WatchdogSettings

        settings = WatchdogSettings()
        assert settings.API_HOST == "127.0.0.1"
        assert settings.API_PORT == 8000
        assert settings.WATCHDOG_INTERVAL >= 5.0
        assert settings.WATCHDOG_FAILURE_LIMIT >= 1
        assert settings.WATCHDOG_RESTART_COOLDOWN >= 30.0
        assert settings.WATCHDOG_STARTUP_GRACE >= 30.0
        assert settings.WATCHDOG_BACKOFF_MAX >= 300.0
        assert settings.WATCHDOG_API_STARTUP_TIMEOUT >= 5
        assert settings.WATCHDOG_API_STARTUP_CHECK_INTERVAL >= 0.5


class TestAPIWatchdogCooldown:
    """バックオフ計算のテスト"""

    @pytest.fixture
    def mock_settings(self):
        """モック設定"""
        settings = MagicMock()
        settings.API_HOST = "127.0.0.1"
        settings.API_PORT = 8000
        settings.WATCHDOG_INTERVAL = 10.0
        settings.WATCHDOG_FAILURE_LIMIT = 3
        settings.WATCHDOG_RESTART_COOLDOWN = 60.0  # 初期クールダウン
        settings.WATCHDOG_STARTUP_GRACE = 60.0
        settings.WATCHDOG_BACKOFF_MAX = 1800.0
        settings.WATCHDOG_API_STARTUP_TIMEOUT = 15
        settings.WATCHDOG_API_STARTUP_CHECK_INTERVAL = 1.0
        return settings

    @pytest.fixture
    def watchdog(self, mock_settings):
        """テスト用Watchdogインスタンス"""
        with patch("scripts.watchdog.WatchdogSettings", return_value=mock_settings):
            with patch("scripts.watchdog.logger"):
                # インポートを遅延させてパッチを適用
                import sys

                # scripts.watchdog がすでにインポートされていたら削除
                if "scripts.watchdog" in sys.modules:
                    del sys.modules["scripts.watchdog"]

                from scripts.watchdog import APIWatchdog

                watchdog = APIWatchdog()
                return watchdog

    def test_cooldown_stage_0(self, watchdog):
        """初回再起動のクールダウンはWATCHDOG_RESTART_COOLDOWN"""
        watchdog._restart_count = 0
        cooldown = watchdog._get_current_cooldown()
        assert cooldown == 60.0  # initial_cooldown

    def test_cooldown_stage_1(self, watchdog):
        """2回目再起動のクールダウンは5分"""
        watchdog._restart_count = 1
        cooldown = watchdog._get_current_cooldown()
        assert cooldown == 300  # 5分

    def test_cooldown_stage_2(self, watchdog):
        """3回目再起動のクールダウンは15分"""
        watchdog._restart_count = 2
        cooldown = watchdog._get_current_cooldown()
        assert cooldown == 900  # 15分

    def test_cooldown_stage_3(self, watchdog):
        """4回目以降のクールダウンは30分"""
        watchdog._restart_count = 3
        cooldown = watchdog._get_current_cooldown()
        assert cooldown == 1800  # 30分

    def test_cooldown_capped_at_max(self, watchdog):
        """クールダウンは最大値を超えない"""
        watchdog._restart_count = 10  # 大きな値
        cooldown = watchdog._get_current_cooldown()
        assert cooldown <= watchdog._backoff_max


class TestAPIWatchdogHealthCheck:
    """ヘルスチェックのテスト"""

    @pytest.fixture
    def mock_settings(self):
        """モック設定"""
        settings = MagicMock()
        settings.API_HOST = "127.0.0.1"
        settings.API_PORT = 8000
        settings.WATCHDOG_INTERVAL = 10.0
        settings.WATCHDOG_FAILURE_LIMIT = 3
        settings.WATCHDOG_RESTART_COOLDOWN = 60.0
        settings.WATCHDOG_STARTUP_GRACE = 60.0
        settings.WATCHDOG_BACKOFF_MAX = 1800.0
        settings.WATCHDOG_API_STARTUP_TIMEOUT = 15
        settings.WATCHDOG_API_STARTUP_CHECK_INTERVAL = 1.0
        return settings

    @pytest.fixture
    def watchdog(self, mock_settings):
        """テスト用Watchdogインスタンス"""
        with patch("scripts.watchdog.WatchdogSettings", return_value=mock_settings):
            with patch("scripts.watchdog.logger"):
                import sys

                if "scripts.watchdog" in sys.modules:
                    del sys.modules["scripts.watchdog"]

                from scripts.watchdog import APIWatchdog

                watchdog = APIWatchdog()
                # HTTPクライアントをモック
                watchdog._http_client = MagicMock()
                return watchdog

    def test_health_check_success_resets_failures(self, watchdog):
        """ヘルスチェック成功で失敗カウントがリセットされる"""
        watchdog._consecutive_failures = 2
        watchdog._restart_count = 1

        # モックレスポンス
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok", "pid": 12345}
        watchdog._http_client.get.return_value = mock_response

        watchdog._check_health()

        assert watchdog._consecutive_failures == 0
        assert watchdog._restart_count == 0  # 安定動作でリセット
        assert watchdog._last_success_time is not None

    def test_health_check_failure_increments_count(self, watchdog):
        """ヘルスチェック失敗で失敗カウントが増加"""
        watchdog._consecutive_failures = 0

        # 非200レスポンス
        mock_response = MagicMock()
        mock_response.status_code = 500
        watchdog._http_client.get.return_value = mock_response

        watchdog._check_health()

        assert watchdog._consecutive_failures == 1

    def test_health_check_timeout_increments_count(self, watchdog):
        """ヘルスチェックタイムアウトで失敗カウントが増加"""
        import httpx

        watchdog._consecutive_failures = 0
        watchdog._http_client.get.side_effect = httpx.RequestError("timeout")

        watchdog._check_health()

        assert watchdog._consecutive_failures == 1

    def test_health_check_exception_does_not_crash(self, watchdog):
        """予期しない例外でもWatchdogは死なない"""
        watchdog._consecutive_failures = 0
        watchdog._http_client.get.side_effect = Exception("Unexpected error")

        # 例外が発生しても関数は完了する
        watchdog._check_health()

        assert watchdog._consecutive_failures == 1

    def test_pid_change_detected(self, watchdog):
        """PID変化が検知される"""
        watchdog._last_api_pid = 12345

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok", "pid": 67890}
        watchdog._http_client.get.return_value = mock_response

        with patch("scripts.watchdog.logger") as mock_logger:
            watchdog._check_health()

            # PID変化がログに記録される
            assert watchdog._last_api_pid == 67890
            # logger.infoが呼ばれたことを確認（PID変化のログ）
            assert any(
                "PID changed" in str(call) for call in mock_logger.info.call_args_list
            )


class TestAPIWatchdogRestart:
    """再起動ロジックのテスト"""

    @pytest.fixture
    def mock_settings(self):
        """モック設定"""
        settings = MagicMock()
        settings.API_HOST = "127.0.0.1"
        settings.API_PORT = 8000
        settings.WATCHDOG_INTERVAL = 10.0
        settings.WATCHDOG_FAILURE_LIMIT = 3
        settings.WATCHDOG_RESTART_COOLDOWN = 60.0
        settings.WATCHDOG_STARTUP_GRACE = 30.0  # 短い猶予期間
        settings.WATCHDOG_BACKOFF_MAX = 1800.0
        settings.WATCHDOG_API_STARTUP_TIMEOUT = 15
        settings.WATCHDOG_API_STARTUP_CHECK_INTERVAL = 1.0
        return settings

    @pytest.fixture
    def watchdog(self, mock_settings):
        """テスト用Watchdogインスタンス"""
        with patch("scripts.watchdog.WatchdogSettings", return_value=mock_settings):
            with patch("scripts.watchdog.logger"):
                import sys

                if "scripts.watchdog" in sys.modules:
                    del sys.modules["scripts.watchdog"]

                from scripts.watchdog import APIWatchdog

                watchdog = APIWatchdog()
                return watchdog

    def test_restart_blocked_during_startup_grace(self, watchdog):
        """起動猶予期間中は再起動がブロックされる"""
        watchdog._last_restart_time = datetime.now()  # たった今再起動した
        watchdog._consecutive_failures = 5
        initial_restart_count = watchdog._restart_count

        with patch.object(watchdog, "_stop_api_server") as mock_stop:
            with patch.object(watchdog, "_start_api_server") as mock_start:
                watchdog._attempt_restart()

                # 再起動は実行されない
                mock_stop.assert_not_called()
                mock_start.assert_not_called()
                assert watchdog._restart_count == initial_restart_count

    def test_restart_blocked_during_cooldown(self, watchdog):
        """クールダウン中は再起動がブロックされる"""
        # 猶予期間は過ぎたがクールダウン中
        watchdog._last_restart_time = datetime.now() - timedelta(seconds=40)  # 40秒前
        watchdog._startup_grace = 30.0  # 猶予期間30秒
        watchdog._initial_cooldown = 60.0  # クールダウン60秒
        watchdog._restart_count = 0
        watchdog._consecutive_failures = 5

        with patch.object(watchdog, "_stop_api_server") as mock_stop:
            with patch.object(watchdog, "_start_api_server") as mock_start:
                watchdog._attempt_restart()

                # 再起動は実行されない
                mock_stop.assert_not_called()
                mock_start.assert_not_called()

    def test_restart_allowed_after_cooldown(self, watchdog):
        """クールダウン後は再起動が実行される"""
        # クールダウン経過後
        watchdog._last_restart_time = datetime.now() - timedelta(seconds=120)  # 2分前
        watchdog._startup_grace = 30.0
        watchdog._initial_cooldown = 60.0
        watchdog._restart_count = 0
        watchdog._consecutive_failures = 5

        with patch.object(watchdog, "_stop_api_server"):
            with patch.object(watchdog, "_start_api_server", return_value=True):
                with patch.object(watchdog, "_close_http_client"):
                    with patch("scripts.watchdog.time.sleep"):
                        watchdog._attempt_restart()

                        # 再起動カウントが増加
                        assert watchdog._restart_count == 1

    def test_first_restart_allowed(self, watchdog):
        """初回再起動は即座に実行可能"""
        watchdog._last_restart_time = None  # 一度も再起動していない
        watchdog._consecutive_failures = 5

        with patch.object(watchdog, "_stop_api_server"):
            with patch.object(watchdog, "_start_api_server", return_value=True):
                with patch.object(watchdog, "_close_http_client"):
                    with patch("scripts.watchdog.time.sleep"):
                        watchdog._attempt_restart()

                        assert watchdog._restart_count == 1
                        assert watchdog._last_restart_time is not None


class TestAPIWatchdogFailureHandling:
    """失敗処理のテスト"""

    @pytest.fixture
    def mock_settings(self):
        """モック設定"""
        settings = MagicMock()
        settings.API_HOST = "127.0.0.1"
        settings.API_PORT = 8000
        settings.WATCHDOG_INTERVAL = 10.0
        settings.WATCHDOG_FAILURE_LIMIT = 3
        settings.WATCHDOG_RESTART_COOLDOWN = 60.0
        settings.WATCHDOG_STARTUP_GRACE = 60.0
        settings.WATCHDOG_BACKOFF_MAX = 1800.0
        settings.WATCHDOG_API_STARTUP_TIMEOUT = 15
        settings.WATCHDOG_API_STARTUP_CHECK_INTERVAL = 1.0
        return settings

    @pytest.fixture
    def watchdog(self, mock_settings):
        """テスト用Watchdogインスタンス"""
        with patch("scripts.watchdog.WatchdogSettings", return_value=mock_settings):
            with patch("scripts.watchdog.logger"):
                import sys

                if "scripts.watchdog" in sys.modules:
                    del sys.modules["scripts.watchdog"]

                from scripts.watchdog import APIWatchdog

                watchdog = APIWatchdog()
                return watchdog

    def test_failure_count_increments(self, watchdog):
        """失敗カウントが増加する"""
        watchdog._consecutive_failures = 0

        watchdog._handle_health_failure()
        assert watchdog._consecutive_failures == 1

        watchdog._handle_health_failure()
        assert watchdog._consecutive_failures == 2

    def test_restart_triggered_at_limit(self, watchdog):
        """失敗上限で再起動がトリガーされる"""
        watchdog._consecutive_failures = 2  # あと1回で上限
        watchdog._failure_limit = 3

        with patch.object(watchdog, "_attempt_restart") as mock_restart:
            watchdog._handle_health_failure()

            assert watchdog._consecutive_failures == 3
            mock_restart.assert_called_once()

    def test_restart_not_triggered_below_limit(self, watchdog):
        """失敗上限未満では再起動しない"""
        watchdog._consecutive_failures = 0
        watchdog._failure_limit = 3

        with patch.object(watchdog, "_attempt_restart") as mock_restart:
            watchdog._handle_health_failure()

            mock_restart.assert_not_called()
