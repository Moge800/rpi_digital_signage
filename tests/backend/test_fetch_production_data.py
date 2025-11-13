"""backend.utils.fetch_production_data()のテスト"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from backend.utils import fetch_production_data
from schemas.production import ProductionData


class TestFetchProductionData:
    """fetch_production_data()関数のテスト (モック使用)"""

    @patch("backend.utils.get_line_name")
    @patch("backend.utils.get_config_data")
    def test_fetch_production_data_returns_production_data(
        self, mock_get_config, mock_get_line_name
    ):
        """fetch_production_data()がProductionDataを返すか"""
        # モックの設定
        mock_get_line_name.return_value = "TEST_LINE"
        mock_config = MagicMock()
        mock_config.name = "テスト機種"
        mock_get_config.return_value = mock_config

        # モックPLCクライアント
        mock_client = MagicMock()

        # 実行
        result = fetch_production_data(mock_client)

        # 検証
        assert isinstance(result, ProductionData)
        assert result.line_name == "TEST_LINE"
        assert result.production_name == "テスト機種"
        assert result.production_type == 1
        assert result.plan == 30000
        assert result.actual == 20000
        assert result.in_operating is True

    @patch("backend.utils.get_line_name")
    @patch("backend.utils.get_config_data")
    def test_fetch_production_data_calculates_remain_values(
        self, mock_get_config, mock_get_line_name
    ):
        """残り時間とパレット数が計算されるか"""
        mock_get_line_name.return_value = "TEST_LINE"
        mock_config = MagicMock()
        mock_config.name = "テスト機種"
        mock_config.seconds_per_product = 1.2
        mock_config.fully = 2800
        mock_get_config.return_value = mock_config

        mock_client = MagicMock()

        result = fetch_production_data(mock_client)

        # 残り10000個 → 10000 * 1.2 / 60 = 200分
        assert result.remain_min == 200

        # 残り10000個 → 10000 / 2800 = 3.57...
        assert result.remain_pallet == pytest.approx(3.57, rel=0.01)

    @patch("backend.utils.get_line_name")
    @patch("backend.utils.get_config_data")
    def test_fetch_production_data_uses_fixed_timestamp(
        self, mock_get_config, mock_get_line_name
    ):
        """タイムスタンプが固定値で返されるか (TODO実装前)"""
        mock_get_line_name.return_value = "TEST_LINE"
        mock_config = MagicMock()
        mock_config.name = "テスト機種"
        mock_get_config.return_value = mock_config

        mock_client = MagicMock()

        result = fetch_production_data(mock_client)

        # 現在は固定値を返すTODO実装
        assert result.timestamp == datetime(2025, 1, 12, 10, 30, 0)
