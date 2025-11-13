from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class ProductionData(BaseModel):
    """生産データのスキーマ

    PLCから取得した生産ラインのリアルタイムデータを保持する。
    フロントエンド表示用の全情報を含む。

    Attributes:
        line_name: ライン名
        production_type: 生産機種番号
        production_name: 生産機種名
        plan: 計画生産数
        actual: 実績生産数
        in_operating: 稼働中フラグ
        remain_min: 残り生産時間(分)
        remain_pallet: 残りパレット数
        alarm: 異常発生フラグ
        alarm_msg: 異常メッセージ
        timestamp: データ取得時刻

    Examples:
        >>> data = ProductionData(
        ...     line_name="LINE_1",
        ...     production_type=1,
        ...     production_name="機種A",
        ...     plan=45000,
        ...     actual=30000,
        ...     in_operating=True,
        ...     remain_min=300,
        ...     remain_pallet=50.5,
        ...     alarm=False,
        ...     alarm_msg=""
        ... )
    """

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
                "fully": 600,
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
    fully: int = Field(..., ge=0, description="満杯パレット数")
    alarm: bool = Field(default=False, description="異常フラグ")
    alarm_msg: str = Field(default="", description="異常メッセージ")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="データ取得時刻"
    )

    @classmethod
    def error(cls) -> "ProductionData":
        """エラー時のデフォルトデータを返す

        PLC通信エラー等でデータ取得に失敗した場合に使用する
        フォールバック用のデータを生成する。

        Returns:
            ProductionData: エラー状態を示すデータ
        """
        return cls(
            line_name="ERROR",
            production_type=0,
            production_name="NONE",
            plan=0,
            actual=0,
            in_operating=False,
            remain_min=0,
            remain_pallet=0,
            fully=0,
            alarm=True,
            alarm_msg="データ取得エラー",
            timestamp=datetime.now(),
        )
