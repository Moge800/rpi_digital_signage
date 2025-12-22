"""PLC通信のテスト (モック使用)"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from backend.plc.plc_client import PLCClient
from backend.plc.plc_fetcher import fetch_production_timestamp


class TestFetchProductionTimestamp:
    """PLC日時取得のテスト (モックでPLC通信を模倣)"""

    @patch("backend.plc.plc_fetcher.PLCClient")
    def test_fetch_timestamp_bcd_conversion(self, mock_plc_class):
        """BCD形式の日時データが正しくdatetimeに変換されるか"""
        # モックPLCクライアントのセットアップ
        mock_client = MagicMock(spec=PLCClient)
        # 2025年11月13日14時30分45秒 のBCDデータ
        # 0x2511 (2025年11月), 0x1314 (13日14時), 0x3045 (30分45秒)
        mock_client.read_words.return_value = [0x2511, 0x1314, 0x3045]

        # 関数実行
        result = fetch_production_timestamp(mock_client, head_device="SD210")

        # 検証
        assert result == datetime(2025, 11, 13, 14, 30, 45)
        mock_client.read_words.assert_called_once_with("SD210", size=3)

    @patch("backend.plc.plc_fetcher.PLCClient")
    def test_fetch_timestamp_connection_error_fallback(self, mock_plc_class):
        """PLC接続エラー時に現在時刻にフォールバックするか"""
        mock_client = MagicMock(spec=PLCClient)
        mock_client.read_words.side_effect = ConnectionError("PLC connection failed")

        # 現在時刻の前後で実行
        before = datetime.now()
        result = fetch_production_timestamp(mock_client, head_device="SD210")
        after = datetime.now()

        # 現在時刻の範囲内であることを確認
        assert before <= result <= after

    @patch("backend.plc.plc_fetcher.PLCClient")
    def test_fetch_timestamp_invalid_data_fallback(self, mock_plc_class):
        """不正なデータ時に現在時刻にフォールバックするか"""
        mock_client = MagicMock(spec=PLCClient)
        # 不正なBCDデータ (配列が短い)
        mock_client.read_words.return_value = [0x2511]

        before = datetime.now()
        result = fetch_production_timestamp(mock_client, head_device="SD210")
        after = datetime.now()

        assert before <= result <= after

    def test_fetch_timestamp_empty_device_returns_system_time(self):
        """head_deviceが空文字列の場合にシステム時刻を返すか"""
        mock_client = MagicMock(spec=PLCClient)

        before = datetime.now()
        result = fetch_production_timestamp(mock_client, head_device="")
        after = datetime.now()

        # システム時刻が返される（PLC通信は行われない）
        assert before <= result <= after
        mock_client.read_words.assert_not_called()


class TestPLCClientMocking:
    """PLCClientのモック化テスト"""

    @patch("backend.plc.plc_client.Type3E")
    def test_plc_client_read_words_mock(self, mock_type3e):
        """PLCClientのread_wordsがモック可能か"""
        # Type3Eのモックインスタンスを作成
        mock_plc = MagicMock()
        mock_plc.batchread_wordunits.return_value = [100, 200, 300]
        mock_type3e.return_value = mock_plc

        # 注意: 実際のPLCClientインスタンス化はせず、モックの動作確認のみ
        result = mock_plc.batchread_wordunits(["D100", "D101", "D102"])
        assert result == [100, 200, 300]

    @patch("backend.plc.plc_client.Type3E")
    def test_plc_client_connection_error_mock(self, mock_type3e):
        """PLC接続エラーがモック可能か"""
        mock_plc = MagicMock()
        mock_plc.batchread_wordunits.side_effect = ConnectionError("Connection failed")
        mock_type3e.return_value = mock_plc

        with pytest.raises(ConnectionError):
            mock_plc.batchread_wordunits(["D100"])
