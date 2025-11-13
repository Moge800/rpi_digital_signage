"""ProductionTypeConfigスキーマのテスト"""

import pytest
from pydantic import ValidationError

from schemas.production_type import ProductionTypeConfig


class TestProductionTypeConfig:
    """ProductionTypeConfigスキーマのテスト"""

    def test_create_valid_production_type_config(self):
        """正常なProductionTypeConfigが作成できるか"""
        config = ProductionTypeConfig(
            production_type=1,
            name="機種A",
            fully=2800,
            seconds_per_product=1.2,
        )

        assert config.production_type == 1
        assert config.name == "機種A"
        assert config.fully == 2800
        assert config.seconds_per_product == pytest.approx(1.2)

    def test_production_type_negative_raises_error(self):
        """production_typeが負の場合にValidationErrorが発生するか"""
        with pytest.raises(ValidationError):
            ProductionTypeConfig(
                production_type=-1,  # 負の値
                name="機種A",
                fully=2800,
                seconds_per_product=1.2,
            )

    def test_production_type_exceeds_limit_raises_error(self):
        """production_typeが上限を超える場合にValidationErrorが発生するか"""
        with pytest.raises(ValidationError):
            ProductionTypeConfig(
                production_type=33,  # 32を超えている
                name="機種A",
                fully=2800,
                seconds_per_product=1.2,
            )

    def test_fully_zero_raises_error(self):
        """fullyが0の場合にValidationErrorが発生するか"""
        with pytest.raises(ValidationError):
            ProductionTypeConfig(
                production_type=1,
                name="機種A",
                fully=0,  # 0は不正
                seconds_per_product=1.2,
            )

    def test_fully_negative_raises_error(self):
        """fullyが負の場合にValidationErrorが発生するか"""
        with pytest.raises(ValidationError):
            ProductionTypeConfig(
                production_type=1,
                name="機種A",
                fully=-100,  # 負の値
                seconds_per_product=1.2,
            )

    def test_seconds_per_product_zero_raises_error(self):
        """seconds_per_productが0の場合にValidationErrorが発生するか"""
        with pytest.raises(ValidationError):
            ProductionTypeConfig(
                production_type=1,
                name="機種A",
                fully=2800,
                seconds_per_product=0.0,  # 0は不正
            )

    def test_seconds_per_product_negative_raises_error(self):
        """seconds_per_productが負の場合にValidationErrorが発生するか"""
        with pytest.raises(ValidationError):
            ProductionTypeConfig(
                production_type=1,
                name="機種A",
                fully=2800,
                seconds_per_product=-1.2,  # 負の値
            )

    def test_example_factory_method(self):
        """example()ファクトリメソッドが正しく動作するか"""
        config = ProductionTypeConfig.example()

        assert config.production_type == 1
        assert config.name == "機種A"
        assert config.fully == 2800
        assert config.seconds_per_product == pytest.approx(1.2)

    def test_production_type_config_json_serialization(self):
        """JSON形式にシリアライズできるか"""
        config = ProductionTypeConfig(
            production_type=2,
            name="機種B",
            fully=3000,
            seconds_per_product=1.0,
        )

        json_data = config.model_dump()
        assert json_data["production_type"] == 2
        assert json_data["name"] == "機種B"
        assert json_data["fully"] == 3000
        assert json_data["seconds_per_product"] == pytest.approx(1.0)
