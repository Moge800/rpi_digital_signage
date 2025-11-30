"""backend.utilsのヘルパー関数テスト"""

from unittest.mock import MagicMock, patch

from backend.config_helpers import get_kiosk_mode
from backend.plc.plc_fetcher import (
    _fetch_bit,
    _fetch_word,
    fetch_actual,
    fetch_alarm_flag,
    fetch_alarm_msg,
    fetch_in_operating,
    fetch_plan,
    fetch_production_type,
    get_plc_device_dict,
)


class TestFetchWordHelper:
    """_fetch_word汎用関数のテスト"""

    @patch("backend.plc.plc_fetcher.logger")
    def test_fetch_word_success(self, mock_logger):
        """正常にワードデータを取得"""
        mock_client = MagicMock()
        mock_client.read_words.return_value = [12345]

        result = _fetch_word(mock_client, "D100", "test field", default=0)

        assert result == 12345
        mock_client.read_words.assert_called_once_with("D100", size=1)
        mock_logger.warning.assert_not_called()

    @patch("backend.plc.plc_fetcher.logger")
    def test_fetch_word_connection_error(self, mock_logger):
        """接続エラー時はデフォルト値を返す"""
        mock_client = MagicMock()
        mock_client.read_words.side_effect = ConnectionError("Connection failed")

        result = _fetch_word(mock_client, "D100", "test field", default=999)

        assert result == 999
        mock_logger.warning.assert_called_once()

    @patch("backend.plc.plc_fetcher.logger")
    def test_fetch_word_index_error(self, mock_logger):
        """データ取得失敗時はデフォルト値を返す"""
        mock_client = MagicMock()
        mock_client.read_words.side_effect = IndexError("No data")

        result = _fetch_word(mock_client, "D100", "test field", default=0)

        assert result == 0
        mock_logger.warning.assert_called_once()


class TestFetchBitHelper:
    """_fetch_bit汎用関数のテスト"""

    @patch("backend.plc.plc_fetcher.logger")
    def test_fetch_bit_success_true(self, mock_logger):
        """正常にビットデータを取得（True）"""
        mock_client = MagicMock()
        mock_client.read_bits.return_value = [1]

        result = _fetch_bit(mock_client, "M100", "test flag", default=False)

        assert result is True
        mock_client.read_bits.assert_called_once_with("M100", size=1)
        mock_logger.warning.assert_not_called()

    @patch("backend.plc.plc_fetcher.logger")
    def test_fetch_bit_success_false(self, mock_logger):
        """正常にビットデータを取得（False）"""
        mock_client = MagicMock()
        mock_client.read_bits.return_value = [0]

        result = _fetch_bit(mock_client, "M100", "test flag", default=False)

        assert result is False
        mock_logger.warning.assert_not_called()

    @patch("backend.plc.plc_fetcher.logger")
    def test_fetch_bit_connection_error(self, mock_logger):
        """接続エラー時はデフォルト値を返す"""
        mock_client = MagicMock()
        mock_client.read_bits.side_effect = ConnectionError("Connection failed")

        result = _fetch_bit(mock_client, "M100", "test flag", default=True)

        assert result is True
        mock_logger.warning.assert_called_once()


class TestFetchFunctions:
    """fetch_*関数のテスト（ヘルパー経由）"""

    @patch("backend.plc.plc_fetcher._fetch_word")
    def test_fetch_production_type(self, mock_fetch_word):
        """機種番号取得関数のテスト"""
        mock_fetch_word.return_value = 5
        mock_client = MagicMock()

        result = fetch_production_type(mock_client, "D200")

        assert result == 5
        mock_fetch_word.assert_called_once_with(
            mock_client, "D200", "production type", default=0
        )

    @patch("backend.plc.plc_fetcher._fetch_word")
    def test_fetch_plan(self, mock_fetch_word):
        """計画数取得関数のテスト"""
        mock_fetch_word.return_value = 10000
        mock_client = MagicMock()

        result = fetch_plan(mock_client, "D300")

        assert result == 10000
        mock_fetch_word.assert_called_once_with(
            mock_client, "D300", "production plan", default=0
        )

    @patch("backend.plc.plc_fetcher._fetch_word")
    def test_fetch_actual(self, mock_fetch_word):
        """実績数取得関数のテスト"""
        mock_fetch_word.return_value = 7500
        mock_client = MagicMock()

        result = fetch_actual(mock_client, "D400")

        assert result == 7500
        mock_fetch_word.assert_called_once_with(
            mock_client, "D400", "production actual", default=0
        )

    @patch("backend.plc.plc_fetcher._fetch_bit")
    def test_fetch_in_operating(self, mock_fetch_bit):
        """稼働中フラグ取得関数のテスト"""
        mock_fetch_bit.return_value = True
        mock_client = MagicMock()

        result = fetch_in_operating(mock_client, "M500")

        assert result is True
        mock_fetch_bit.assert_called_once_with(
            mock_client, "M500", "in_operating flag", default=False
        )

    @patch("backend.plc.plc_fetcher._fetch_bit")
    def test_fetch_alarm_flag(self, mock_fetch_bit):
        """アラームフラグ取得関数のテスト"""
        mock_fetch_bit.return_value = False
        mock_client = MagicMock()

        result = fetch_alarm_flag(mock_client, "M600")

        assert result is False
        mock_fetch_bit.assert_called_once_with(
            mock_client, "M600", "alarm flag", default=False
        )


class TestFetchAlarmMsg:
    """fetch_alarm_msg関数のテスト"""

    @patch("backend.plc.plc_fetcher.logger")
    def test_fetch_alarm_msg_success(self, mock_logger):
        """正常にアラームメッセージを取得"""
        mock_client = MagicMock()
        # "ERROR" をワードデータとして表現 (ASCII: E=0x45, R=0x52, O=0x4F, R=0x52)
        mock_client.read_words.return_value = [
            0x4552,  # "ER"
            0x524F,  # "RO"
            0x5200,  # "R\x00"
            0x0000,
            0x0000,
            0x0000,
            0x0000,
            0x0000,
            0x0000,
            0x0000,
        ]

        result = fetch_alarm_msg(mock_client, "D700")

        assert result == "ERROR"
        mock_client.read_words.assert_called_once_with("D700", size=10)
        mock_logger.warning.assert_not_called()

    @patch("backend.plc.plc_fetcher.logger")
    def test_fetch_alarm_msg_connection_error(self, mock_logger):
        """接続エラー時は空文字を返す"""
        mock_client = MagicMock()
        mock_client.read_words.side_effect = ConnectionError("Connection failed")

        result = fetch_alarm_msg(mock_client, "D700")

        assert result == ""
        mock_logger.warning.assert_called_once()


class TestGetKioskMode:
    """get_kiosk_mode関数のテスト"""

    def test_get_kiosk_mode_returns_bool(self):
        """Kioskモード設定がboolで返されるか"""
        result = get_kiosk_mode()
        assert isinstance(result, bool)


class TestGetPlcDeviceDict:
    """get_plc_device_dict関数のテスト"""

    def test_get_plc_device_dict_returns_dict(self):
        """PLCデバイス辞書が正しく返されるか"""
        result = get_plc_device_dict()

        assert isinstance(result, dict)
        assert "TIME_DEVICE" in result
        assert "PRODUCTION_TYPE_DEVICE" in result
        assert "PLAN_DEVICE" in result
        assert "ACTUAL_DEVICE" in result
        assert "ALARM_FLAG_DEVICE" in result
        assert "ALARM_MSG_DEVICE" in result
        assert "IN_OPERATING_DEVICE" in result

    def test_get_plc_device_dict_values_are_strings(self):
        """すべてのデバイスアドレスが文字列か"""
        result = get_plc_device_dict()

        for key, value in result.items():
            assert isinstance(value, str), f"{key} should be string"
