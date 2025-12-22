"""API エンドポイントのテスト"""

from unittest.mock import patch, MagicMock


class TestProductionEndpoint:
    """生産データエンドポイントのテスト"""

    def test_production_response_model_has_required_fields(self) -> None:
        """ProductionResponseが必要なフィールドを持つこと"""
        from api.routes.production import ProductionResponse

        # 必須フィールドの確認
        fields = ProductionResponse.model_fields
        required_fields = [
            "line_name",
            "production_type",
            "production_name",
            "plan",
            "actual",
            "remain",
            "remain_pallet",
            "remain_min",
            "fully",
            "in_operating",
            "alarm",
            "alarm_msg",
            "timestamp",
        ]
        for field in required_fields:
            assert field in fields, f"Missing field: {field}"

    def test_status_response_model_has_required_fields(self) -> None:
        """StatusResponseが必要なフィールドを持つこと"""
        from api.routes.production import StatusResponse

        fields = StatusResponse.model_fields
        required_fields = ["plc_connected", "use_plc", "line_name", "last_update"]
        for field in required_fields:
            assert field in fields, f"Missing field: {field}"


class TestSystemEndpoint:
    """システムエンドポイントのテスト"""

    def test_sync_time_response_model_has_required_fields(self) -> None:
        """SyncTimeResponseが必要なフィールドを持つこと"""
        from api.routes.system import SyncTimeResponse

        fields = SyncTimeResponse.model_fields
        required_fields = ["success", "synced_time", "message"]
        for field in required_fields:
            assert field in fields, f"Missing field: {field}"

    def test_shutdown_response_model_has_required_fields(self) -> None:
        """ShutdownResponseが必要なフィールドを持つこと"""
        from api.routes.system import ShutdownResponse

        fields = ShutdownResponse.model_fields
        required_fields = ["status", "message"]
        for field in required_fields:
            assert field in fields, f"Missing field: {field}"


class TestPLCService:
    """PLCServiceのテスト"""

    def test_plc_service_is_singleton(self) -> None:
        """PLCServiceがシングルトンであること"""
        from api.services.plc_service import PLCService

        service1 = PLCService()
        service2 = PLCService()
        assert service1 is service2

    def test_get_status_returns_dict(self) -> None:
        """get_statusがdictを返すこと"""
        from api.services.plc_service import plc_service

        status = plc_service.get_status()
        assert isinstance(status, dict)
        assert "plc_connected" in status
        assert "use_plc" in status
        assert "line_name" in status

    @patch("api.services.plc_service.get_config_data")
    def test_generate_dummy_data_returns_production_data(
        self, mock_config: MagicMock
    ) -> None:
        """_generate_dummy_dataがProductionDataを返すこと"""
        from api.services.plc_service import plc_service
        from schemas import ProductionData
        from schemas.production_type import ProductionTypeConfig

        # モックの設定
        mock_config.return_value = ProductionTypeConfig(
            production_type=0, name="テスト機種", fully=2800, seconds_per_product=1.2
        )

        data = plc_service._generate_dummy_data()
        assert isinstance(data, ProductionData)
        assert data.plan == 45000
        assert data.actual >= 0
        assert data.actual <= 45000


class TestAPIClient:
    """APIクライアントのテスト"""

    def test_api_base_url_uses_settings(self) -> None:
        """API_BASE_URLが設定から構築されること"""
        from frontend.api_client import API_BASE_URL

        assert "127.0.0.1" in API_BASE_URL or "localhost" in API_BASE_URL
        assert "8000" in API_BASE_URL

    def test_check_api_health_returns_bool(self) -> None:
        """check_api_healthがboolを返すこと"""
        from frontend.api_client import check_api_health

        # APIサーバーが動いていない場合はFalse
        result = check_api_health()
        assert isinstance(result, bool)
