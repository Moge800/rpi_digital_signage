"""ProductionDataスキーマのテスト"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from schemas.production import ProductionData


class TestProductionData:
    """ProductionDataスキーマのテスト"""

    def test_create_valid_production_data(self):
        """正常なProductionDataが作成できるか"""
        data = ProductionData(
            line_name="LINE_1",
            production_type=1,
            production_name="機種A",
            plan=30000,
            actual=20000,
            in_operating=True,
            remain_min=200,
            remain_pallet=3.57,
            alarm=False,
            alarm_msg="",
            timestamp=datetime(2025, 11, 13, 10, 30, 0),
        )

        assert data.line_name == "LINE_1"
        assert data.production_type == 1
        assert data.production_name == "機種A"
        assert data.plan == 30000
        assert data.actual == 20000
        assert data.in_operating is True
        assert data.remain_min == 200
        assert data.remain_pallet == pytest.approx(3.57)
        assert data.alarm is False
        assert data.alarm_msg == ""

    def test_production_data_with_defaults(self):
        """デフォルト値付きでProductionDataが作成できるか"""
        data = ProductionData(
            line_name="LINE_1",
            production_type=0,
            production_name="NONE",
            plan=10000,
            actual=5000,
            remain_min=100,
            remain_pallet=5.0,
        )

        # デフォルト値の確認
        assert data.in_operating is False
        assert data.alarm is False
        assert data.alarm_msg == ""
        assert isinstance(data.timestamp, datetime)

    def test_production_data_negative_plan_raises_error(self):
        """計画数が負の場合にValidationErrorが発生するか"""
        with pytest.raises(ValidationError):
            ProductionData(
                line_name="LINE_1",
                production_type=0,
                production_name="NONE",
                plan=-1000,  # 負の値
                actual=0,
                remain_min=0,
                remain_pallet=0.0,
            )

    def test_production_data_negative_actual_raises_error(self):
        """実績数が負の場合にValidationErrorが発生するか"""
        with pytest.raises(ValidationError):
            ProductionData(
                line_name="LINE_1",
                production_type=0,
                production_name="NONE",
                plan=10000,
                actual=-500,  # 負の値
                remain_min=0,
                remain_pallet=0.0,
            )

    def test_production_data_error_factory(self):
        """error()メソッドがエラー用データを返すか"""
        error_data = ProductionData.error()

        assert error_data.line_name == "ERROR"
        assert error_data.production_type == 0
        assert error_data.production_name == "NONE"
        assert error_data.plan == 0
        assert error_data.actual == 0
        assert error_data.alarm is True
        assert error_data.alarm_msg == "データ取得エラー"

    def test_production_data_json_serialization(self):
        """JSON形式にシリアライズできるか"""
        data = ProductionData(
            line_name="LINE_1",
            production_type=1,
            production_name="機種A",
            plan=30000,
            actual=20000,
            remain_min=200,
            remain_pallet=3.57,
            timestamp=datetime(2025, 11, 13, 10, 30, 0),
        )

        json_data = data.model_dump()
        assert json_data["line_name"] == "LINE_1"
        assert json_data["production_type"] == 1
        assert json_data["production_name"] == "機種A"
        assert json_data["plan"] == 30000
