"""機種マスタ管理モジュール

責務:
- 環境変数LINE_NAMEに基づくJSONファイル読み込み
- 機種設定の取得・キャッシュ管理
- シングルトンパターンによる一元管理
"""

from pathlib import Path
from typing import ClassVar
import json
import os
from schemas.production_type import ProductionTypeConfig


class ProductionConfigManager:
    """機種マスタ管理クラス (シングルトン)

    環境変数LINE_NAMEに対応するJSONファイルから機種マスタを読み込み、
    アプリケーション全体で一元管理する。

    使用例:
        >>> manager = ProductionConfigManager()
        >>> config = manager.get_config(1)
        >>> print(config.name)  # "機種A"
    """

    _instance: ClassVar["ProductionConfigManager | None"] = None
    _configs: dict[int, ProductionTypeConfig]
    _line_name: str

    def __new__(cls, line_name: str | None = None) -> "ProductionConfigManager":
        """シングルトンインスタンスを返す

        Args:
            line_name: ライン名 (Noneの場合は環境変数LINE_NAMEを使用)

        Returns:
            ProductionConfigManager: シングルトンインスタンス
        """
        if cls._instance is None:
            instance = super().__new__(cls)
            # 属性を初期化してからインスタンスに代入
            if line_name is None:
                line_name = os.getenv("LINE_NAME", "LINE_1")
            instance._line_name = line_name
            instance._configs = instance._load_configs()
            cls._instance = instance
        return cls._instance

    def _load_configs(self) -> dict[int, ProductionTypeConfig]:
        """JSONファイルから機種マスタを読み込み

        Returns:
            dict[int, ProductionTypeConfig]: 機種番号をキーとした設定辞書

        Raises:
            FileNotFoundError: 対応するJSONファイルが見つからない場合
            ValueError: JSON形式が不正な場合
        """
        # プロジェクトルート/config/production_types/ を参照
        project_root = Path(__file__).parent.parent.parent
        config_dir = project_root / "config" / "production_types"
        config_file = config_dir / f"{self._line_name}.json"

        if not config_file.exists():
            raise FileNotFoundError(
                f"Production type config not found: {config_file}\n"
                f"Please create config/production_types/{self._line_name}.json"
            )

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Pydanticで検証しながら辞書を構築
            return {int(k): ProductionTypeConfig(**v) for k, v in data.items()}

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format in {config_file}: {e}")
        except Exception as e:
            raise ValueError(f"Failed to load production types from {config_file}: {e}")

    def get_config(self, production_type: int) -> ProductionTypeConfig:
        """機種番号から設定を取得

        Args:
            production_type: 機種番号 (0-15)

        Returns:
            ProductionTypeConfig: 機種設定

        Raises:
            ValueError: 機種番号が範囲外または未定義の場合
        """
        if production_type < 0 or production_type > 15:
            raise ValueError(
                f"production_type must be between 0 and 15, got {production_type}"
            )

        if production_type not in self._configs:
            raise ValueError(
                f"production_type {production_type} is not configured "
                f"in LINE_NAME={self._line_name}"
            )

        return self._configs[production_type]

    def get_all_configs(self) -> dict[int, ProductionTypeConfig]:
        """全機種設定を取得

        Returns:
            dict[int, ProductionTypeConfig]: 全機種設定の辞書
        """
        return self._configs.copy()

    @property
    def line_name(self) -> str:
        """ライン名を取得

        Returns:
            str: 現在のライン名
        """
        return self._line_name


# 後方互換性のためのヘルパー関数
def get_production_type_config(production_type: int) -> ProductionTypeConfig:
    """機種番号から設定を取得 (後方互換性用)

    Note:
        新しいコードではProductionConfigManager().get_config()の使用を推奨

    Args:
        production_type: 機種番号 (0-15)

    Returns:
        ProductionTypeConfig: 機種設定

    Raises:
        ValueError: 機種番号が範囲外または未定義の場合
    """
    manager = ProductionConfigManager()
    return manager.get_config(production_type)
