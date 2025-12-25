"""PLCサービスのテスト

タイムアウト機構、連続失敗処理、フェイルセーフのテスト。
"""

import time
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest


class TestPLCServiceTimeout:
    """PLCサービスのタイムアウト機構テスト"""

    @pytest.fixture
    def mock_settings(self):
        """モック設定を作成"""
        settings = MagicMock()
        settings.PLC_FETCH_TIMEOUT = 1.0  # 短いタイムアウト
        settings.PLC_FETCH_FAILURE_LIMIT = 3
        settings.LINE_NAME = "TEST_LINE"
        return settings

    @pytest.fixture
    def plc_service(self, mock_settings):
        """PLCServiceのモックインスタンスを作成"""
        with patch("api.services.plc_service.Settings", return_value=mock_settings):
            with patch("api.services.plc_service.get_use_plc", return_value=False):
                # シングルトンをリセット
                from api.services.plc_service import PLCService

                PLCService._instance = None
                PLCService._initialized = False
                service = PLCService()
                return service

    def test_execute_with_timeout_success(self, plc_service):
        """タイムアウト内に完了する関数は成功する"""

        def quick_func():
            return "success"

        result = plc_service._execute_with_timeout(quick_func, "test_op")
        assert result == "success"
        assert plc_service._consecutive_failures == 0

    def test_execute_with_timeout_failure(self, plc_service):
        """タイムアウトする関数は失敗としてカウントされる"""

        def slow_func():
            time.sleep(5)  # タイムアウト超過
            return "never_returned"

        from api.services.plc_service import PLCCommunicationTimeoutError

        with pytest.raises(PLCCommunicationTimeoutError):
            plc_service._execute_with_timeout(slow_func, "slow_op")

        assert plc_service._consecutive_failures == 1

    def test_consecutive_failures_increment(self, plc_service):
        """失敗が連続でカウントされる"""
        initial_count = plc_service._consecutive_failures

        # 失敗をシミュレート
        plc_service._handle_failure()
        assert plc_service._consecutive_failures == initial_count + 1

        plc_service._handle_failure()
        assert plc_service._consecutive_failures == initial_count + 2

    def test_success_resets_failure_count(self, plc_service):
        """成功で失敗カウントがリセットされる"""
        plc_service._consecutive_failures = 2

        def quick_func():
            return "success"

        plc_service._execute_with_timeout(quick_func, "test_op")
        assert plc_service._consecutive_failures == 0

    def test_get_status_includes_failure_count(self, plc_service):
        """ステータスに連続失敗回数が含まれる"""
        plc_service._consecutive_failures = 3
        status = plc_service.get_status()
        assert "consecutive_failures" in status
        assert status["consecutive_failures"] == 3


class TestPLCServiceProcessTermination:
    """連続失敗時のプロセス終了テスト"""

    @pytest.fixture
    def mock_settings(self):
        """モック設定を作成"""
        settings = MagicMock()
        settings.PLC_FETCH_TIMEOUT = 1.0
        settings.PLC_FETCH_FAILURE_LIMIT = 3  # 3回で終了
        settings.LINE_NAME = "TEST_LINE"
        return settings

    @pytest.fixture
    def plc_service(self, mock_settings):
        """PLCServiceのモックインスタンスを作成"""
        with patch("api.services.plc_service.Settings", return_value=mock_settings):
            with patch("api.services.plc_service.get_use_plc", return_value=False):
                from api.services.plc_service import PLCService

                PLCService._instance = None
                PLCService._initialized = False
                service = PLCService()
                return service

    def test_terminate_process_called_at_limit(self, plc_service):
        """失敗回数が閾値に達するとプロセス終了が呼ばれる"""
        plc_service._consecutive_failures = 2  # あと1回で閾値

        with patch.object(plc_service, "_terminate_process") as mock_terminate:
            plc_service._handle_failure()
            mock_terminate.assert_called_once()

    def test_terminate_process_not_called_below_limit(self, plc_service):
        """失敗回数が閾値未満ではプロセス終了は呼ばれない"""
        plc_service._consecutive_failures = 0

        with patch.object(plc_service, "_terminate_process") as mock_terminate:
            plc_service._handle_failure()
            mock_terminate.assert_not_called()


class TestPLCServiceDummyData:
    """ダミーデータ生成テスト"""

    @pytest.fixture
    def plc_service(self):
        """USE_PLC=falseのPLCServiceを作成"""
        mock_settings = MagicMock()
        mock_settings.PLC_FETCH_TIMEOUT = 3.0
        mock_settings.PLC_FETCH_FAILURE_LIMIT = 5
        mock_settings.LINE_NAME = "TEST_LINE"

        with patch("api.services.plc_service.Settings", return_value=mock_settings):
            with patch("api.services.plc_service.get_use_plc", return_value=False):
                from api.services.plc_service import PLCService

                PLCService._instance = None
                PLCService._initialized = False
                service = PLCService()
                return service

    def test_get_production_data_returns_dummy(self, plc_service):
        """USE_PLC=falseの場合はダミーデータを返す"""
        # get_config_dataもモック（適切な属性を持つオブジェクトを返す）
        mock_config = MagicMock()
        mock_config.name = "テスト機種"
        mock_config.fully = 100

        with patch(
            "api.services.plc_service.get_config_data", return_value=mock_config
        ):
            data = plc_service.get_production_data()

            assert data.line_name == "TEST_LINE"
            assert data.plan > 0
            assert isinstance(data.timestamp, datetime)
