"""config.settingsのテスト"""

from unittest.mock import patch

import pytest
from pydantic import ValidationError

from config.settings import Settings, PLCDeviceList


class TestSettings:
    """Settings設定クラスのテスト"""

    def test_settings_loads_from_env(self):
        """環境変数から正しく設定を読み込めるか"""
        settings = Settings()

        assert settings.PLC_IP is not None
        assert settings.PLC_PORT == 5000
        assert settings.AUTO_RECONNECT is False  # conftest.pyで設定
        assert settings.LINE_NAME == "dev_line_1"
        assert settings.REFRESH_INTERVAL == 10.0
        assert settings.LOG_LEVEL == "INFO"

    def test_settings_debug_dummy_read_flag(self):
        """DEBUG_DUMMY_READフラグが正しく読み込まれるか"""
        settings = Settings()
        assert settings.DEBUG_DUMMY_READ is True  # conftest.pyで設定

    def test_settings_use_plc_flag(self):
        """USE_PLCフラグが正しく読み込まれるか"""
        settings = Settings()
        assert settings.USE_PLC is False  # conftest.pyで設定

    def test_settings_invalid_port_raises_error(self):
        """不正なポート番号でValidationErrorが発生するか"""
        with pytest.raises(ValidationError):
            Settings(
                PLC_IP="192.168.0.10",
                PLC_PORT=99999,  # 65535を超えている
                RECONNECT_RETRY=3,
                RECONNECT_DELAY=2.0,
            )

    def test_settings_invalid_retry_raises_error(self):
        """不正なリトライ回数でValidationErrorが発生するか"""
        with pytest.raises(ValidationError):
            Settings(
                PLC_IP="192.168.0.10",
                PLC_PORT=5000,
                RECONNECT_RETRY=20,  # 10を超えている
                RECONNECT_DELAY=2.0,
            )

    def test_settings_invalid_log_level_raises_error(self):
        """不正なログレベルでValidationErrorが発生するか"""
        with pytest.raises(ValidationError):
            Settings(
                PLC_IP="192.168.0.10",
                PLC_PORT=5000,
                RECONNECT_RETRY=3,
                RECONNECT_DELAY=2.0,
                LOG_LEVEL="INVALID",  # 不正なログレベル
            )


class TestPLCDeviceList:
    """PLCデバイスリスト設定のテスト"""

    def test_plc_device_list_defaults(self):
        """デフォルト値が正しく設定されるか"""
        device_list = PLCDeviceList()

        assert device_list.TIME_DEVICE == "D210"
        assert device_list.PRODUCTION_TYPE_DEVICE == "D100"
        assert device_list.PLAN_DEVICE == "D101"
        assert device_list.ACTUAL_DEVICE == "D102"
        assert device_list.ALARM_FLAG_DEVICE == "D103"
        assert device_list.ALARM_MSG_DEVICE == "D104"
        assert device_list.IN_OPERATING_DEVICE == "D105"

    def test_plc_device_list_custom_values(self):
        """カスタム値を設定できるか"""
        device_list = PLCDeviceList(
            TIME_DEVICE="SD210",
            PRODUCTION_TYPE_DEVICE="D100",
            PLAN_DEVICE="D200",
            ACTUAL_DEVICE="D300",
        )

        assert device_list.TIME_DEVICE == "SD210"
        assert device_list.PRODUCTION_TYPE_DEVICE == "D100"
        assert device_list.PLAN_DEVICE == "D200"
        assert device_list.ACTUAL_DEVICE == "D300"


class TestSettingsEnvFileNotFound:
    """環境変数ファイルが見つからない場合のテスト"""

    @patch("os.path.exists")
    def test_settings_raises_error_when_env_file_missing(self, mock_exists):
        """環境変数ファイルが見つからない場合にFileNotFoundErrorが発生するか"""
        mock_exists.return_value = False

        with pytest.raises(FileNotFoundError, match=r".env file not found"):
            Settings()

    @patch("os.path.exists")
    def test_plc_device_list_raises_error_when_env_file_missing(self, mock_exists):
        """環境変数ファイルが見つからない場合にFileNotFoundErrorが発生するか"""
        mock_exists.return_value = False

        with pytest.raises(FileNotFoundError, match=r".env file not found"):
            PLCDeviceList()
