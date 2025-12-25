"""pytest設定とフィクスチャ"""

import os
import sys
from pathlib import Path
import shutil

import pytest

# srcディレクトリをパスに追加
project_root = Path(__file__).parent.parent
src_dir = project_root / "src"
sys.path.insert(0, str(src_dir))

# テスト実行前に.envファイルを準備(.env.exampleからコピー)
env_file = project_root / ".env"
env_example = project_root / ".env.example"
if not env_file.exists() and env_example.exists():
    shutil.copy(env_example, env_file)

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


@pytest.fixture(autouse=True)
def reset_plc_service_singleton():
    """PLCServiceシングルトンをテストごとにリセット

    テストがシングルトンを汚染して、実際の起動時に
    テスト用の設定が残るのを防ぐ。
    """
    yield
    # テスト後にリセット
    try:
        from api.services.plc_service import PLCService

        PLCService._instance = None
        PLCService._initialized = False
    except ImportError:
        pass  # インポートできない場合はスキップ
