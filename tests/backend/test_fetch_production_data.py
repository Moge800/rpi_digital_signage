"""backend.plc.plc_fetcher.fetch_production_data()のテスト"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from backend.plc.plc_fetcher import fetch_production_data
from schemas.production import ProductionData


class TestFetchProductionData:
    """fetch_production_data()関数のテスト (モック使用)"""

    @patch("backend.plc.plc_fetcher.fetch_production_timestamp")
    @patch("backend.plc.plc_fetcher.fetch_alarm_msg")
    @patch("backend.plc.plc_fetcher.fetch_alarm_flag")
    @patch("backend.plc.plc_fetcher.fetch_in_operating")
    @patch("backend.plc.plc_fetcher.fetch_actual")
    @patch("backend.plc.plc_fetcher.fetch_plan")
    @patch("backend.plc.plc_fetcher.fetch_production_type")
    @patch("backend.plc.plc_fetcher.get_plc_device_dict")
    @patch("backend.config_helpers.get_line_name")
    @patch("backend.config_helpers.get_config_data")
    def test_fetch_production_data_returns_production_data(
        self,
        mock_get_config,
        mock_get_line_name,
        mock_get_device_dict,
        mock_fetch_type,
        mock_fetch_plan,
        mock_fetch_actual,
        mock_fetch_operating,
        mock_fetch_alarm_flag,
        mock_fetch_alarm_msg,
        mock_fetch_timestamp,
    ):
        """fetch_production_data()がProductionDataを返すか"""
        # モックの設定
        mock_get_line_name.return_value = "TEST_LINE"
        mock_config = MagicMock()
        mock_config.name = "テスト機種"
        mock_config.fully = 2800
        mock_config.seconds_per_product = 1.2
        mock_get_config.return_value = mock_config
        mock_get_device_dict.return_value = {
            "TIME_DEVICE": "SD210",
            "PRODUCTION_TYPE_DEVICE": "D200",
            "PLAN_DEVICE": "D210",
            "ACTUAL_DEVICE": "D220",
            "ALARM_FLAG_DEVICE": "M310",
            "ALARM_MSG_DEVICE": "D300",
            "IN_OPERATING_DEVICE": "M300",
        }
        mock_fetch_type.return_value = 1
        mock_fetch_plan.return_value = 30000
        mock_fetch_actual.return_value = 20000
        mock_fetch_operating.return_value = True
        mock_fetch_alarm_flag.return_value = False
        mock_fetch_alarm_msg.return_value = ""
        mock_fetch_timestamp.return_value = datetime(2025, 1, 12, 10, 30, 0)

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

    @patch("backend.plc.plc_fetcher.fetch_production_timestamp")
    @patch("backend.plc.plc_fetcher.fetch_alarm_msg")
    @patch("backend.plc.plc_fetcher.fetch_alarm_flag")
    @patch("backend.plc.plc_fetcher.fetch_in_operating")
    @patch("backend.plc.plc_fetcher.fetch_actual")
    @patch("backend.plc.plc_fetcher.fetch_plan")
    @patch("backend.plc.plc_fetcher.fetch_production_type")
    @patch("backend.plc.plc_fetcher.get_plc_device_dict")
    @patch("backend.config_helpers.get_line_name")
    @patch("backend.config_helpers.get_config_data")
    def test_fetch_production_data_calculates_remain_values(
        self,
        mock_get_config,
        mock_get_line_name,
        mock_get_device_dict,
        mock_fetch_type,
        mock_fetch_plan,
        mock_fetch_actual,
        mock_fetch_operating,
        mock_fetch_alarm_flag,
        mock_fetch_alarm_msg,
        mock_fetch_timestamp,
    ):
        """残り時間とパレット数が計算されるか"""
        mock_get_line_name.return_value = "TEST_LINE"
        mock_config = MagicMock()
        mock_config.name = "テスト機種"
        mock_config.seconds_per_product = 1.2
        mock_config.fully = 2800
        mock_get_config.return_value = mock_config
        mock_get_device_dict.return_value = {
            "TIME_DEVICE": "SD210",
            "PRODUCTION_TYPE_DEVICE": "D200",
            "PLAN_DEVICE": "D210",
            "ACTUAL_DEVICE": "D220",
            "ALARM_FLAG_DEVICE": "M310",
            "ALARM_MSG_DEVICE": "D300",
            "IN_OPERATING_DEVICE": "M300",
        }
        mock_fetch_type.return_value = 1
        mock_fetch_plan.return_value = 30000
        mock_fetch_actual.return_value = 20000
        mock_fetch_operating.return_value = True
        mock_fetch_alarm_flag.return_value = False
        mock_fetch_alarm_msg.return_value = ""
        mock_fetch_timestamp.return_value = datetime(2025, 1, 12, 10, 30, 0)

        mock_client = MagicMock()

        result = fetch_production_data(mock_client)

        # 残り10000個 → 10000 * 1.2 / 60 = 200分
        assert result.remain_min == 200

        # 残り10000個 → 10000 / 2800 = 3.57...
        assert result.remain_pallet == pytest.approx(3.57, rel=0.01)

    @patch("backend.plc.plc_fetcher.fetch_production_timestamp")
    @patch("backend.plc.plc_fetcher.fetch_alarm_msg")
    @patch("backend.plc.plc_fetcher.fetch_alarm_flag")
    @patch("backend.plc.plc_fetcher.fetch_in_operating")
    @patch("backend.plc.plc_fetcher.fetch_actual")
    @patch("backend.plc.plc_fetcher.fetch_plan")
    @patch("backend.plc.plc_fetcher.fetch_production_type")
    @patch("backend.plc.plc_fetcher.get_plc_device_dict")
    @patch("backend.config_helpers.get_line_name")
    @patch("backend.config_helpers.get_config_data")
    def test_fetch_production_data_uses_plc_timestamp(
        self,
        mock_get_config,
        mock_get_line_name,
        mock_get_device_dict,
        mock_fetch_type,
        mock_fetch_plan,
        mock_fetch_actual,
        mock_fetch_operating,
        mock_fetch_alarm_flag,
        mock_fetch_alarm_msg,
        mock_fetch_timestamp,
    ):
        """タイムスタンプがPLCから取得されるか"""
        mock_get_line_name.return_value = "TEST_LINE"
        mock_config = MagicMock()
        mock_config.name = "テスト機種"
        mock_config.fully = 2800
        mock_config.seconds_per_product = 1.2
        mock_get_config.return_value = mock_config
        mock_get_device_dict.return_value = {
            "TIME_DEVICE": "SD210",
            "PRODUCTION_TYPE_DEVICE": "D200",
            "PLAN_DEVICE": "D210",
            "ACTUAL_DEVICE": "D220",
            "ALARM_FLAG_DEVICE": "M310",
            "ALARM_MSG_DEVICE": "D300",
            "IN_OPERATING_DEVICE": "M300",
        }
        mock_fetch_type.return_value = 1
        mock_fetch_plan.return_value = 30000
        mock_fetch_actual.return_value = 20000
        mock_fetch_operating.return_value = True
        mock_fetch_alarm_flag.return_value = False
        mock_fetch_alarm_msg.return_value = ""
        mock_fetch_timestamp.return_value = datetime(2025, 11, 14, 15, 30, 45)

        mock_client = MagicMock()

        result = fetch_production_data(mock_client)

        # PLCから取得したタイムスタンプが使用される
        assert result.timestamp == datetime(2025, 11, 14, 15, 30, 45)
