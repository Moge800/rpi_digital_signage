"""Watchdogのテスト

APIWatchdogクラスの主要ロジックをテスト。
実際のプロセス起動は行わず、モックを使用。
"""

from unittest.mock import MagicMock, patch
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
        assert watchdog._last_success_monotonic is not None

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
        watchdog._popen_pid = 11111

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
                "worker PID changed" in str(call)
                for call in mock_logger.info.call_args_list
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
        import time

        watchdog._last_restart_monotonic = time.monotonic()  # たった今再起動した
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
        import time

        # 猶予期間は過ぎたがクールダウン中
        watchdog._last_restart_monotonic = time.monotonic() - 40  # 40秒前
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
        import time

        # クールダウン経過後
        watchdog._last_restart_monotonic = time.monotonic() - 120  # 2分前
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
        watchdog._last_restart_monotonic = None  # 一度も再起動していない
        watchdog._consecutive_failures = 5

        with patch.object(watchdog, "_stop_api_server"):
            with patch.object(watchdog, "_start_api_server", return_value=True):
                with patch.object(watchdog, "_close_http_client"):
                    with patch("scripts.watchdog.time.sleep"):
                        watchdog._attempt_restart()

                        assert watchdog._restart_count == 1
                        assert watchdog._last_restart_monotonic is not None


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


class TestAPIWatchdogHttpClient:
    """HTTPクライアント管理のテスト"""

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

    def test_http_client_reuse(self, watchdog):
        """HTTPクライアントが再利用される"""
        client1 = watchdog._get_http_client()
        client2 = watchdog._get_http_client()

        assert client1 is client2

    def test_http_client_recreated_after_close(self, watchdog):
        """close後に新しいクライアントが作成される"""
        client1 = watchdog._get_http_client()
        watchdog._close_http_client()
        client2 = watchdog._get_http_client()

        assert client1 is not client2

    def test_close_http_client_when_none(self, watchdog):
        """クライアントがNoneの時もcloseは安全"""
        watchdog._http_client = None
        # 例外が発生しないことを確認
        watchdog._close_http_client()
        assert watchdog._http_client is None


class TestAPIWatchdogProcessManagement:
    """プロセス管理のテスト"""

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

    def test_stop_api_server_when_none(self, watchdog):
        """プロセスがNoneの時はstopは何もしない"""
        watchdog._api_process = None
        # 例外が発生しないことを確認
        watchdog._stop_api_server()

    def test_stop_api_server_already_stopped(self, watchdog):
        """既に停止しているプロセスの処理"""
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.poll.return_value = 0  # 既に終了
        watchdog._api_process = mock_process

        with patch("scripts.watchdog.logger"):
            watchdog._stop_api_server()

        # プロセスがNoneにクリアされる
        assert watchdog._api_process is None

    def test_stop_api_server_graceful(self, watchdog):
        """SIGTERMで正常停止"""
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # まだ動作中
        mock_process.wait.return_value = 0  # SIGTERM後に正常終了
        watchdog._api_process = mock_process

        with patch("scripts.watchdog.os.getpgid", return_value=12345):
            with patch("scripts.watchdog.os.killpg") as mock_killpg:
                with patch("scripts.watchdog.logger"):
                    watchdog._stop_api_server()

        # SIGTERMが送信された
        import signal

        mock_killpg.assert_called_once_with(12345, signal.SIGTERM)
        assert watchdog._api_process is None

    def test_stop_api_server_sigkill_on_timeout(self, watchdog):
        """タイムアウト時はSIGKILLで強制終了"""
        import subprocess
        import signal

        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        mock_process.wait.side_effect = [
            subprocess.TimeoutExpired(cmd="test", timeout=5),  # 最初はタイムアウト
            None,  # SIGKILL後は成功
        ]
        watchdog._api_process = mock_process

        with patch("scripts.watchdog.os.getpgid", return_value=12345):
            with patch("scripts.watchdog.os.killpg") as mock_killpg:
                with patch("scripts.watchdog.logger"):
                    watchdog._stop_api_server()

        # SIGTERM → SIGKILL の順で呼ばれる
        assert mock_killpg.call_count == 2
        mock_killpg.assert_any_call(12345, signal.SIGTERM)
        mock_killpg.assert_any_call(12345, signal.SIGKILL)


class TestAPIWatchdogApiStartup:
    """API起動待機のテスト"""

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
        settings.WATCHDOG_API_STARTUP_TIMEOUT = 3  # 短いタイムアウト
        settings.WATCHDOG_API_STARTUP_CHECK_INTERVAL = 0.1
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
                watchdog._http_client = MagicMock()
                return watchdog

    def test_wait_for_api_ready_immediate_success(self, watchdog):
        """即座にAPIが起動完了"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        watchdog._http_client.get.return_value = mock_response
        watchdog._api_process = MagicMock()
        watchdog._api_process.poll.return_value = None

        result = watchdog._wait_for_api_ready()

        assert result is True

    def test_wait_for_api_ready_timeout(self, watchdog):
        """タイムアウトまでAPIが起動しない"""
        import httpx

        watchdog._http_client.get.side_effect = httpx.RequestError("connection refused")
        watchdog._api_process = MagicMock()
        watchdog._api_process.poll.return_value = None

        with patch("scripts.watchdog.time.sleep"):
            result = watchdog._wait_for_api_ready()

        assert result is False

    def test_wait_for_api_ready_process_died(self, watchdog):
        """起動中にプロセスが死亡"""
        import httpx

        watchdog._http_client.get.side_effect = httpx.RequestError("connection refused")
        watchdog._api_process = MagicMock()
        watchdog._api_process.poll.return_value = 1  # プロセス終了
        watchdog._api_process.returncode = 1

        with patch("scripts.watchdog.logger"):
            result = watchdog._wait_for_api_ready()

        assert result is False


class TestAPIWatchdogSignalHandling:
    """シグナルハンドリングのテスト"""

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

    def test_handle_signal_stops_running(self, watchdog):
        """シグナル受信で_runningがFalseになる"""
        import signal

        watchdog._running = True

        with patch.object(watchdog, "_stop_api_server"):
            with patch.object(watchdog, "_close_http_client"):
                with patch("scripts.watchdog.logger"):
                    watchdog._handle_signal(signal.SIGTERM, None)

        assert watchdog._running is False

    def test_handle_signal_cleans_up(self, watchdog):
        """シグナル受信でクリーンアップが実行される"""
        import signal

        with patch.object(watchdog, "_stop_api_server") as mock_stop:
            with patch.object(watchdog, "_close_http_client") as mock_close:
                with patch("scripts.watchdog.logger"):
                    watchdog._handle_signal(signal.SIGINT, None)

        mock_stop.assert_called_once()
        mock_close.assert_called_once()


class TestAPIWatchdogEdgeCases:
    """エッジケースのテスト"""

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

    def test_failure_count_preserved_during_cooldown(self, watchdog):
        """クールダウン中もfailure_countが維持される"""
        import time

        watchdog._consecutive_failures = 5
        watchdog._failure_limit = 3
        # クールダウン中
        watchdog._last_restart_monotonic = time.monotonic() - 30  # 30秒前
        watchdog._startup_grace = 60.0

        with patch.object(watchdog, "_stop_api_server"):
            with patch.object(watchdog, "_start_api_server"):
                with patch("scripts.watchdog.logger"):
                    watchdog._attempt_restart()

        # 失敗カウントは維持される（0にならない）
        assert watchdog._consecutive_failures == 5

    def test_restart_count_resets_on_stable_operation(self, watchdog):
        """安定動作（ヘルスチェック成功）でrestart_countがリセット"""
        watchdog._restart_count = 3  # 複数回再起動後
        watchdog._consecutive_failures = 0

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok", "pid": 12345}
        watchdog._http_client = MagicMock()
        watchdog._http_client.get.return_value = mock_response

        watchdog._check_health()

        # 成功でrestart_countがリセット
        assert watchdog._restart_count == 0

    def test_health_check_with_missing_pid(self, watchdog):
        """PIDなしのレスポンスでも正常動作"""
        watchdog._last_api_pid = 12345

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}  # PIDなし
        watchdog._http_client = MagicMock()
        watchdog._http_client.get.return_value = mock_response

        watchdog._check_health()

        # 前のPIDが維持される（更新されない）
        assert watchdog._last_api_pid == 12345
        assert watchdog._consecutive_failures == 0

    def test_start_api_server_failure(self, watchdog):
        """API起動失敗時の処理"""
        with patch(
            "scripts.watchdog.subprocess.Popen", side_effect=Exception("spawn failed")
        ):
            with patch("scripts.watchdog.logger"):
                result = watchdog._start_api_server()

        assert result is False


class TestAPIWatchdogReadyCheck:
    """/readyチェックのテスト"""

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
        settings.WATCHDOG_READY_CHECK_INTERVAL = 60.0  # 60秒間隔
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

    def test_ready_check_skipped_when_disabled(self):
        """WATCHDOG_READY_CHECK_INTERVAL=0で/readyチェックがスキップされる"""
        import sys

        # 先にモジュールを削除（キャッシュクリア）
        if "scripts.watchdog" in sys.modules:
            del sys.modules["scripts.watchdog"]

        # 無効設定用のモック
        mock_settings = MagicMock()
        mock_settings.API_HOST = "127.0.0.1"
        mock_settings.API_PORT = 8000
        mock_settings.WATCHDOG_INTERVAL = 10.0
        mock_settings.WATCHDOG_FAILURE_LIMIT = 3
        mock_settings.WATCHDOG_RESTART_COOLDOWN = 60.0
        mock_settings.WATCHDOG_STARTUP_GRACE = 60.0
        mock_settings.WATCHDOG_BACKOFF_MAX = 1800.0
        mock_settings.WATCHDOG_API_STARTUP_TIMEOUT = 15
        mock_settings.WATCHDOG_API_STARTUP_CHECK_INTERVAL = 1.0
        mock_settings.WATCHDOG_READY_CHECK_INTERVAL = 0.0  # 無効

        with patch("config.settings.WatchdogSettings", return_value=mock_settings):
            with patch("scripts.watchdog.logger"):
                from scripts.watchdog import APIWatchdog

                watchdog = APIWatchdog()

                # 内部変数が正しく設定されているか確認
                assert watchdog._ready_check_interval == 0.0

                watchdog._http_client = MagicMock()

                with patch("scripts.watchdog.time.monotonic", return_value=1000.0):
                    watchdog._check_ready_if_due()

                # HTTPリクエストは発生しない
                watchdog._http_client.get.assert_not_called()

    def test_ready_check_skipped_before_interval(self, watchdog):
        """/readyチェックは間隔に達するまでスキップ"""
        with patch("scripts.watchdog.time.monotonic", return_value=1000.0):
            # 前回チェック時刻を設定（30秒前）
            watchdog._last_ready_check_monotonic = 970.0

        watchdog._http_client = MagicMock()

        with patch("scripts.watchdog.time.monotonic", return_value=1000.0):
            watchdog._check_ready_if_due()

        # 60秒間隔に達していないのでリクエストなし
        watchdog._http_client.get.assert_not_called()

    def test_ready_check_executed_after_interval(self, watchdog):
        """/readyチェックは間隔後に実行"""
        watchdog._last_ready_check_monotonic = 900.0  # 100秒前

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "ok",
            "plc_alive": True,
            "plc_service_ready": True,
        }
        watchdog._http_client = MagicMock()
        watchdog._http_client.get.return_value = mock_response

        with patch("scripts.watchdog.time.monotonic", return_value=1000.0):
            watchdog._check_ready_if_due()

        # リクエストが実行される
        watchdog._http_client.get.assert_called_once()
        call_args = watchdog._http_client.get.call_args
        assert "/ready" in call_args[0][0]

    def test_ready_check_first_time(self, watchdog):
        """初回/readyチェックは即実行"""
        watchdog._last_ready_check_monotonic = None  # 初回

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        watchdog._http_client = MagicMock()
        watchdog._http_client.get.return_value = mock_response

        with patch("scripts.watchdog.time.monotonic", return_value=1000.0):
            watchdog._check_ready_if_due()

        # リクエストが実行される
        watchdog._http_client.get.assert_called_once()

    def test_ready_check_degraded_logged_as_warning(self, watchdog):
        """degraded状態は警告ログ出力"""
        watchdog._last_ready_check_monotonic = None

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "degraded",
            "plc_alive": False,
            "plc_service_ready": True,
        }
        watchdog._http_client = MagicMock()
        watchdog._http_client.get.return_value = mock_response

        with patch("scripts.watchdog.time.monotonic", return_value=1000.0):
            with patch("scripts.watchdog.logger") as mock_logger:
                watchdog._check_ready_if_due()

        # 警告ログが出力される
        mock_logger.warning.assert_called()
        # 再起動はトリガーされない（failure countは増えない）
        assert watchdog._consecutive_failures == 0

    def test_ready_check_failure_does_not_increment_failures(self, watchdog):
        """/readyチェック失敗は再起動トリガーにならない"""
        watchdog._last_ready_check_monotonic = None
        watchdog._consecutive_failures = 0

        watchdog._http_client = MagicMock()
        watchdog._http_client.get.side_effect = Exception("connection refused")

        with patch("scripts.watchdog.time.monotonic", return_value=1000.0):
            with patch("scripts.watchdog.logger"):
                watchdog._check_ready_if_due()

        # 失敗カウントは増えない
        assert watchdog._consecutive_failures == 0

    def test_ready_check_updates_last_check_time(self, watchdog):
        """チェック後にlast_ready_check_monotonicが更新"""
        watchdog._last_ready_check_monotonic = None

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        watchdog._http_client = MagicMock()
        watchdog._http_client.get.return_value = mock_response

        with patch("scripts.watchdog.time.monotonic", return_value=1234.5):
            watchdog._check_ready_if_due()

        assert watchdog._last_ready_check_monotonic == 1234.5

    def test_ready_check_non_200_response(self, watchdog):
        """/readyが非200を返した場合は警告ログのみ"""
        watchdog._last_ready_check_monotonic = None
        watchdog._consecutive_failures = 0

        mock_response = MagicMock()
        mock_response.status_code = 503
        watchdog._http_client = MagicMock()
        watchdog._http_client.get.return_value = mock_response

        with patch("scripts.watchdog.time.monotonic", return_value=1000.0):
            with patch("scripts.watchdog.logger") as mock_logger:
                watchdog._check_ready_if_due()

        mock_logger.warning.assert_called()
        # 失敗カウントは増えない
        assert watchdog._consecutive_failures == 0
