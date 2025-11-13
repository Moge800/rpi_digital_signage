from pydantic import BaseModel, Field


class ProductionTypeConfig(BaseModel):
    """生産機種ごとの設定"""

    production_type: int = Field(ge=0, le=32, description="機種番号 (0-32)")
    name: str = Field(description="機種名")
    fully: int = Field(gt=0, description="1パレットあたりの積載数")
    seconds_per_product: float = Field(gt=0, description="1個あたりの生産時間(秒)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "production_type": 1,
                "name": "機種A",
                "fully": 2800,  # 140個 × 20段
                "seconds_per_product": 1.2,  # 1個あたり1.2秒 (50個/分)
            }
        }
    }

    @classmethod
    def example(cls) -> "ProductionTypeConfig":
        """デフォルトの例を返す"""
        return cls(
            production_type=1,
            name="機種A",
            fully=2800,  # 140個 × 20段
            seconds_per_product=1.2,  # 1個あたり1.2秒 (50個/分)
        )
