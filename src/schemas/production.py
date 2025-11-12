from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class ProductionData(BaseModel):
    """生産データのスキーマ"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "line_name": "NONE",
                "production_type": 0,
                "production_name": "機種A",
                "plan": 45000,
                "actual": 30000,
                "in_operating": False,
                "remain_min": 300,
                "remain_pallet": 50,
                "alarm": False,
                "alarm_msg": "",
                "timestamp": "2025-11-12T10:30:00",
            }
        }
    )

    line_name: str = Field(..., description="ライン名")
    production_type: int = Field(..., description="生産機種番号")
    production_name: str = Field(..., description="生産機種名")
    plan: int = Field(..., ge=0, description="計画生産数")
    actual: int = Field(..., ge=0, description="実績生産数")
    in_operating: bool = Field(default=False, description="稼働中フラグ")
    remain_min: int = Field(..., ge=0, description="残り時間（分）")
    remain_pallet: float = Field(..., ge=0, description="残りパレット数")
    alarm: bool = Field(default=False, description="異常フラグ")
    alarm_msg: str = Field(default="", description="異常メッセージ")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="データ取得時刻"
    )

    @classmethod
    def error(cls) -> "ProductionData":
        """エラー時のデフォルトデータを返す"""
        return cls(
            line_name="ERROR",
            production_type=0,
            production_name="NONE",
            plan=0,
            actual=0,
            in_operating=False,
            remain_min=0,
            remain_pallet=0,
            alarm=True,
            alarm_msg="データ取得エラー",
            timestamp=datetime.now(),
        )
