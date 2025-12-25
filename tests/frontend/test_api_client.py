"""フロントエンド api_client のテスト

フェイルセーフ機構のテスト。
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
import httpx


class TestApiClientFailsafe:
    """APIクライアントのフェイルセーフテスト"""

    @pytest.fixture(autouse=True)
    def reset_cache(self):
        """テストごとにキャッシュをリセット"""
        import frontend.api_client as api_client

        api_client._last_production_data = None
        yield
        api_client._last_production_data = None

    @pytest.fixture
    def mock_settings(self):
        """モック設定を作成"""
        settings = MagicMock()
        settings.API_HOST = "127.0.0.1"
        settings.API_PORT = 8000
        settings.FRONTEND_API_TIMEOUT = 3.0
        settings.ALLOW_FRONTEND_RESTART = False
        return settings

    def test_fetch_production_caches_success(self, mock_settings):
        """成功時にデータがキャッシュされる"""
        import frontend.api_client as api_client

        mock_response_data = {
            "line_name": "TEST_LINE",
            "production_type": 0,
            "production_name": "テスト機種",
            "plan": 1000,
            "actual": 500,
            "in_operating": True,
            "remain_min": 30,
            "remain_pallet": 5.0,
            "fully": 100,
            "alarm": False,
            "alarm_msg": "",
            "timestamp": "2025-01-01T12:00:00",
        }

        with patch.object(api_client, "_settings", mock_settings):
            with patch("frontend.api_client._get_client") as mock_get_client:
                mock_client = MagicMock()
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_response_data
                mock_client.get.return_value = mock_response
                mock_client.__enter__ = MagicMock(return_value=mock_client)
                mock_client.__exit__ = MagicMock(return_value=False)
                mock_get_client.return_value = mock_client

                result = api_client.fetch_production_from_api()

                assert result.line_name == "TEST_LINE"
                assert api_client._last_production_data is not None

    def test_fetch_production_uses_cache_on_timeout(self, mock_settings):
        """タイムアウト時にキャッシュを使用"""
        import frontend.api_client as api_client
        from schemas import ProductionData

        # 先にキャッシュを設定
        cached_data = ProductionData(
            line_name="CACHED_LINE",
            production_type=0,
            production_name="キャッシュ機種",
            plan=1000,
            actual=500,
            in_operating=True,
            remain_min=30,
            remain_pallet=5.0,
            fully=100,
            alarm=False,
            alarm_msg="",
            timestamp=datetime.now(),
        )
        api_client._last_production_data = cached_data

        with patch.object(api_client, "_settings", mock_settings):
            with patch("frontend.api_client._get_client") as mock_get_client:
                mock_client = MagicMock()
                mock_client.get.side_effect = httpx.TimeoutException("timeout")
                mock_client.__enter__ = MagicMock(return_value=mock_client)
                mock_client.__exit__ = MagicMock(return_value=False)
                mock_get_client.return_value = mock_client

                result = api_client.fetch_production_from_api()

                # キャッシュされたデータが返される
                assert result.line_name == "CACHED_LINE"
                assert "[キャッシュ]" in result.alarm_msg

    def test_fetch_production_returns_error_without_cache(self, mock_settings):
        """キャッシュなしでタイムアウトするとエラーデータを返す"""
        import frontend.api_client as api_client

        api_client._last_production_data = None  # キャッシュなし

        with patch.object(api_client, "_settings", mock_settings):
            with patch("frontend.api_client._get_client") as mock_get_client:
                mock_client = MagicMock()
                mock_client.get.side_effect = httpx.TimeoutException("timeout")
                mock_client.__enter__ = MagicMock(return_value=mock_client)
                mock_client.__exit__ = MagicMock(return_value=False)
                mock_get_client.return_value = mock_client

                result = api_client.fetch_production_from_api()

                # エラーデータが返される
                assert result.alarm is True
                assert "APIタイムアウト" in result.alarm_msg

    def test_is_restart_allowed(self, mock_settings):
        """再起動許可フラグの確認"""
        import frontend.api_client as api_client

        mock_settings.ALLOW_FRONTEND_RESTART = False
        with patch.object(api_client, "_settings", mock_settings):
            assert api_client.is_restart_allowed() is False

        mock_settings.ALLOW_FRONTEND_RESTART = True
        with patch.object(api_client, "_settings", mock_settings):
            assert api_client.is_restart_allowed() is True
