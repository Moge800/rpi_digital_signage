"""生産データ関連エンドポイント

/api/production - 生産データ取得
/api/status     - PLC接続状態
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.services.plc_service import plc_service
from backend.logging import api_logger as logger

router = APIRouter()


class ProductionResponse(BaseModel):
    """生産データレスポンス"""

    line_name: str
    production_type: int
    production_name: str
    plan: int
    actual: int
    remain: int
    remain_pallet: float
    remain_min: int
    fully: int
    in_operating: bool
    alarm: bool
    alarm_msg: str
    timestamp: str


class StatusResponse(BaseModel):
    """ステータスレスポンス"""

    plc_connected: bool
    use_plc: bool
    line_name: str
    last_update: str | None


@router.get("/production", response_model=ProductionResponse)
async def get_production() -> ProductionResponse:
    """生産データを取得

    PLCから現在の生産データを取得して返す。
    USE_PLC=false の場合はダミーデータを返す。

    Returns:
        ProductionResponse: 生産データ

    Raises:
        HTTPException: PLC通信エラー時 (500)
    """
    try:
        data = plc_service.get_production_data()
        return ProductionResponse(
            line_name=data.line_name,
            production_type=data.production_type,
            production_name=data.production_name,
            plan=data.plan,
            actual=data.actual,
            remain=max(0, data.plan - data.actual),
            remain_pallet=data.remain_pallet,
            remain_min=data.remain_min,
            fully=data.fully,
            in_operating=data.in_operating,
            alarm=data.alarm,
            alarm_msg=data.alarm_msg,
            timestamp=data.timestamp.isoformat(),
        )
    except Exception as e:
        logger.error(f"Failed to get production data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=StatusResponse)
async def get_status() -> StatusResponse:
    """PLC接続状態を取得

    Returns:
        StatusResponse: 接続状態
    """
    status = plc_service.get_status()
    return StatusResponse(
        plc_connected=status["plc_connected"],
        use_plc=status["use_plc"],
        line_name=status["line_name"],
        last_update=status["last_update"],
    )
