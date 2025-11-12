"""ProductionConfigManagerのテスト"""

import os
from pathlib import Path

import pytest

from config.production_config import ProductionConfigManager
from schemas.production_type import ProductionTypeConfig


class TestProductionConfigManager:
    """ProductionConfigManagerのテストクラス"""

    def test_singleton_pattern(self):
        """シングルトンパターンが機能しているか"""
        manager1 = ProductionConfigManager()
        manager2 = ProductionConfigManager()
        assert manager1 is manager2

    def test_loads_config_file(self, test_config_dir):
        """dev_line_1.jsonが正しく読み込まれるか"""
        manager = ProductionConfigManager()
        assert manager.line_name == "dev_line_1"
        configs = manager.get_all_configs()
        assert len(configs) > 0

    def test_get_config_returns_valid_data(self):
        """機種番号0の設定が正しく取得できるか"""
        manager = ProductionConfigManager()
        config = manager.get_config(0)

        assert isinstance(config, ProductionTypeConfig)
        assert config.production_type == 0
        assert config.name == "SUPER-UNSET"
        assert config.fully == 2800
        assert config.seconds_per_product == 60.0

    def test_get_config_for_type_1(self):
        """機種番号1の設定が正しく取得できるか"""
        manager = ProductionConfigManager()
        config = manager.get_config(1)

        assert config.production_type == 1
        assert config.name == "機種A"
        assert config.fully == 2800
        assert config.seconds_per_product == 1.2

    def test_get_config_raises_error_for_invalid_type(self):
        """存在しない機種番号でValueErrorが発生するか"""
        manager = ProductionConfigManager()
        with pytest.raises(
            ValueError, match="production_type must be between 0 and 15"
        ):
            manager.get_config(99)

    def test_get_all_configs_returns_dict(self):
        """get_all_configs()が辞書を返すか"""
        manager = ProductionConfigManager()
        configs = manager.get_all_configs()

        assert isinstance(configs, dict)
        assert 0 in configs
        assert 1 in configs

    def test_config_file_path_resolution(self, project_root_path):
        """設定ファイルのパス解決が正しいか"""
        manager = ProductionConfigManager()
        expected_path = (
            project_root_path / "config" / "production_types" / "dev_line_1.json"
        )
        assert (
            expected_path.exists()
        ), f"Expected config file not found: {expected_path}"


class TestProductionConfigManagerWithDifferentLine:
    """異なるライン名でのテスト"""

    def test_config_file_not_found_error(self):
        """存在しないライン名でFileNotFoundErrorが発生するか"""
        # 一時的に環境変数を変更
        original_line_name = os.environ.get("LINE_NAME")
        os.environ["LINE_NAME"] = "nonexistent_line"

        # シングルトンインスタンスをリセット
        ProductionConfigManager._instance = None

        try:
            with pytest.raises(
                FileNotFoundError, match="Production type config not found"
            ):
                ProductionConfigManager()
        finally:
            # 環境変数を元に戻す
            if original_line_name:
                os.environ["LINE_NAME"] = original_line_name
            # シングルトンインスタンスをリセット
            ProductionConfigManager._instance = None
