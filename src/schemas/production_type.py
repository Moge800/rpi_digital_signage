from pydantic import BaseModel, Field


class ProductionTypeConfig(BaseModel):
    """生産機種ごとの設定

    各生産機種の特性を定義するデータモデル。
    config/production_types/{LINE_NAME}.jsonから読み込まれる。

    Attributes:
        production_type: 機種番号 (0-32, 0は未定義)
        name: 機種名
        fully: 1パレットあたりの積載数
        seconds_per_product: 1個あたりの生産時間(秒)

    Examples:
        >>> config = ProductionTypeConfig(
        ...     production_type=1,
        ...     name="機種A",
        ...     fully=2800,
        ...     seconds_per_product=1.2
        ... )
    """

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
        """デフォルトの例を返す

        テストやドキュメント用のサンプルデータを生成する。

        Returns:
            ProductionTypeConfig: サンプル機種設定
        """
        return cls(
            production_type=1,
            name="機種A",
            fully=2800,  # 140個 × 20段
            seconds_per_product=1.2,  # 1個あたり1.2秒 (50個/分)
        )
