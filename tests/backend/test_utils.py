"""backend.utilsのテスト"""

import pytest

from backend.calculators import calculate_remain_minutes, calculate_remain_pallet
from backend.config_helpers import (
    get_line_name,
    get_log_level,
    get_refresh_interval,
    get_use_plc,
)


class TestEnvironmentVariableHelpers:
    """環境変数取得関数のテスト"""

    def test_get_use_plc_returns_false(self):
        """USE_PLC=falseが正しく解釈されるか"""
        assert get_use_plc() is False

    def test_get_line_name_returns_dev_line_1(self):
        """LINE_NAMEが正しく取得されるか"""
        assert get_line_name() == "dev_line_1"

    def test_get_refresh_interval_returns_number(self):
        """REFRESH_INTERVALが数値で返されるか"""
        interval = get_refresh_interval()
        assert isinstance(interval, (int, float))
        assert interval > 0

    def test_get_log_level_returns_valid_level(self):
        """LOG_LEVELが有効な値を返すか"""
        level = get_log_level()
        assert level in ("DEBUG", "INFO", "WARNING", "ERROR")


class TestCalculateRemainPallet:
    """残りパレット数計算のテスト"""

    def test_calculate_remain_pallet_basic(self):
        """基本的な残りパレット数計算"""
        # 機種1: fully=2800, seconds_per_product=1.2
        # plan=30000, actual=20000 → 残り10000個
        # 10000 / 2800 = 3.57... → 3.57 (decimals=2)
        result = calculate_remain_pallet(
            plan=30000, actual=20000, production_type=1, decimals=2
        )
        assert result == pytest.approx(3.57, rel=0.01)

    def test_calculate_remain_pallet_no_decimals(self):
        """decimals=Noneで丸めないケース"""
        result = calculate_remain_pallet(
            plan=30000, actual=20000, production_type=1, decimals=None
        )
        expected = 10000 / 2800
        assert result == pytest.approx(expected, rel=0.0001)

    def test_calculate_remain_pallet_zero_remain(self):
        """計画=実績の場合は0"""
        result = calculate_remain_pallet(
            plan=10000, actual=10000, production_type=1, decimals=2
        )
        assert result == 0.0

    def test_calculate_remain_pallet_actual_exceeds_plan(self):
        """実績が計画を超えても0"""
        result = calculate_remain_pallet(
            plan=10000, actual=15000, production_type=1, decimals=2
        )
        assert result == 0.0

    def test_calculate_remain_pallet_decimals_1(self):
        """decimals=1で小数点第1位まで"""
        result = calculate_remain_pallet(
            plan=30000, actual=20000, production_type=1, decimals=1
        )
        assert result == pytest.approx(3.6, rel=0.01)


class TestCalculateRemainMinutes:
    """残り時間計算のテスト"""

    def test_calculate_remain_minutes_basic(self):
        """基本的な残り時間計算"""
        # 機種1: seconds_per_product=1.2秒
        # plan=30000, actual=20000 → 残り10000個
        # 10000 * 1.2 = 12000秒 = 200分
        result = calculate_remain_minutes(
            plan=30000, actual=20000, production_type=1, decimals=2
        )
        assert result == 200.0

    def test_calculate_remain_minutes_no_decimals(self):
        """decimals=Noneで丸めないケース"""
        # 機種3: seconds_per_product=1.333秒
        # 残り10000個 → 10000 * 1.333 / 60 = 222.166...分
        result = calculate_remain_minutes(
            plan=30000, actual=20000, production_type=3, decimals=None
        )
        expected = 10000 * 1.333 / 60.0
        assert result == pytest.approx(expected, rel=0.0001)

    def test_calculate_remain_minutes_zero_remain(self):
        """計画=実績の場合は0分"""
        result = calculate_remain_minutes(
            plan=10000, actual=10000, production_type=1, decimals=2
        )
        assert result == 0.0

    def test_calculate_remain_minutes_decimals_1(self):
        """decimals=1で小数点第1位まで"""
        # 機種2: seconds_per_product=1.0秒
        # 残り6000個 → 6000 * 1.0 / 60 = 100.0分
        result = calculate_remain_minutes(
            plan=16000, actual=10000, production_type=2, decimals=1
        )
        assert result == 100.0
