"""pytest設定とフィクスチャ"""

import os
import sys
from pathlib import Path

import pytest

# srcディレクトリをパスに追加
project_root = Path(__file__).parent.parent
src_dir = project_root / "src"
sys.path.insert(0, str(src_dir))

# テスト用環境変数を設定
os.environ["LINE_NAME"] = "dev_line_1"
os.environ["USE_PLC"] = "false"
os.environ["DEBUG_DUMMY_READ"] = "true"
os.environ["PLC_IP"] = "127.0.0.1"
os.environ["PLC_PORT"] = "5000"
os.environ["AUTO_RECONNECT"] = "false"


@pytest.fixture
def project_root_path():
    """プロジェクトルートのパスを返す"""
    return Path(__file__).parent.parent


@pytest.fixture
def test_config_dir(project_root_path):
    """テスト用の設定ディレクトリパスを返す"""
    return project_root_path / "config" / "production_types"
