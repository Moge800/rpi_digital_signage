# GitHub Copilot Instructions

## プロジェクト概要
Raspberry Pi向けのデジタルサイネージシステム。三菱電機製PLC(MELSEC)からリアルタイムで生産データを取得し、Streamlitで視覚的に表示する。

## 技術スタック
- **Python**: 3.13+
- **パッケージマネージャ**: uv
- **フロントエンド**: Streamlit 1.51.0, Plotly
- **PLC通信**: pymcprotocol (Type3E)
- **データ検証**: Pydantic 2.x, pydantic-settings
- **環境変数**: python-dotenv
- **開発ツール**: Black, Ruff, pytest

## プロジェクト構造
```
src/
├── backend/          # バックエンドロジック
│   ├── plc/         # PLC通信層
│   │   ├── plc_client.py      # PLCクライアント(シングルトン)
│   │   └── plc_fetcher.py     # データ取得関数群
│   ├── logging/     # ロギング設定
│   ├── config_helpers.py  # 設定アクセス
│   ├── calculators.py     # 計算ロジック
│   └── system_utils.py    # システム操作(時刻同期、プラットフォーム判定)
├── frontend/        # Streamlit UI
├── config/          # 設定管理
└── schemas/         # Pydanticデータモデル
```

**モジュール責務分離 (2025-12-01リファクタリング)**:
- `plc_fetcher.py`: PLC通信・データ取得 (293行)
- `config_helpers.py`: Settings/設定アクセス + Enum導入 (75行)
- `calculators.py`: ビジネスロジック計算 (64行)
- `system_utils.py`: OS操作(システム時刻同期、プラットフォーム判定) (102行)

## コーディング規約

### 1. 型ヒントは必須
```python
# Good
def get_production_data() -> ProductionData:
    return ProductionData(...)

# Bad
def get_production_data():
    return ProductionData(...)
```

### 2. 環境変数の扱い
- `.env`ファイルは必須(`.env.example`をコピー)
- Pydantic Settingsで型安全に管理
- Enum型を活用 (`Theme`, `LogLevel`)
- 設定アクセスは`config_helpers.py`のヘルパー関数経由

### 3. エラーハンドリング
- `Exception`の汎用捕捉は避ける
- 具体的な例外を指定: `ConnectionError`, `OSError`, `TimeoutError`など
```python
# Good
except (ConnectionError, OSError) as e:
    logger.error(f"Connection failed: {e}")

# Bad
except Exception as e:
    pass
```

### 4. マジックナンバーは定数化
```python
# Good
PRODUCTION_RATE_PER_MINUTE = 50
remain_min = (plan - actual) / PRODUCTION_RATE_PER_MINUTE

# Bad
remain_min = (plan - actual) / 50
```

### 5. グローバル変数は避ける
- シングルトンが必要な場合はクラス属性を使用
- `global`キーワードは使わない

### 6. インポート順序
```python
# 標準ライブラリ
import os
import sys

# サードパーティ
from pydantic import BaseModel
import streamlit as st

# ローカル
from schemas import ProductionData
from backend.plc.plc_client import get_plc_client
from backend.config_helpers import get_use_plc
from config import Theme, LogLevel
```

### 7. ロギング
- 共通ロガーを使用(`backend.logging`)
- ログレベル: DEBUG, INFO, WARNING, ERROR
- ファイルとコンソール両方に出力
```python
from backend.logging import plc_logger as logger

logger.info("Connected to PLC")
logger.error(f"Failed to read: {e}")
```

### 8. dotenvの読み込み
```python
# Good
from dotenv import load_dotenv
load_dotenv()

# Bad
import dotenv
dotenv.load_dotenv()
```

### 9. subprocess推奨
```python
# Good
subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py"], check=True)

# Bad
os.system("streamlit run app.py")
```

### 10. type: ignoreは最小限に
- 型を正しく定義すれば不要なはず
- やむを得ない場合のみ使用し、理由をコメント

### 11. ファイルエンコーディング
- **PowerShellスクリプト (`.ps1`)**: UTF-8 BOM付き (Microsoft推奨)
- **その他すべてのファイル**: UTF-8 BOMなし
  - Python (`.py`)
  - Markdown (`.md`)
  - JSON (`.json`)
  - YAML (`.yml`, `.yaml`)
  - Bash (`.sh`)
  - テキストファイル (`.txt`, `.env`)

**理由**: PowerShellは歴史的経緯でBOMなしUTF-8を正しく解釈できない場合があるため、BOM付きを使用する。

## PLC通信の注意点
- `PLCClient`はシングルトンパターン
- 自動再接続機能あり(`AUTO_RECONNECT=true`)
- デバッグ時は`DEBUG_DUMMY_READ=true`でダミーデータ使用可能
- Type3E固定、IP/ポートは`.env`で設定

## Streamlit特有の考慮事項
- スクリプト全体が毎回再実行される
- モジュールレベルの定数定義は推奨(再計算を避ける)
- `@st.cache_resource`でリソース(PLCクライアント等)をキャッシュ
- `st_autorefresh`で自動リフレッシュ実装済み

## セキュリティ
- `.env`はGitにコミットしない(`.gitignore`済み)
- 機密情報(IP、ポート、ライン名等)は環境変数化
- ログファイルも`.gitignore`で除外

## テスト
- pytest使用
- PLC通信テストは`DEBUG_DUMMY_READ=true`で実施

### テスト駆動開発(TDD)の推奨
**新機能追加時は必ずテストも同時作成する**

#### テストの配置
```
tests/
├── config/           # 設定管理のテスト
├── backend/         # バックエンドロジックのテスト
│   └── plc/        # PLC通信のテスト(モック使用)
└── schemas/         # データモデルのテスト
```

#### テスト作成ルール
1. **新しい関数を追加** → 対応するテストを`tests/`に作成
2. **計算ロジック変更** → 既存テストを更新 + 新ケース追加
3. **バグ修正** → 再現テストを追加してから修正

#### PLC通信テストの注意
- 実機PLC接続は不要(モックを使用)
```python
from unittest.mock import MagicMock, patch

@patch("backend.plc.plc_client.Type3E")
def test_plc_read(mock_type3e):
    mock_plc = MagicMock()
    mock_plc.batchread_wordunits.return_value = [100, 200]
    mock_type3e.return_value = mock_plc
    # テスト実行...
```

#### テスト実行コマンド
```bash
# 全テスト実行
pytest tests/ -v

# 特定のテストファイルのみ
pytest tests/backend/test_utils.py -v

# カバレッジ計測
pytest --cov=src tests/
```

#### テストの命名規則
- ファイル: `test_*.py`
- クラス: `Test*` (例: `TestProductionConfigManager`)
- 関数: `test_*` (例: `test_calculate_remain_pallet_basic`)

## デプロイ
- Raspberry Pi上で実行想定
- `uv sync`で依存関係インストール
- `python main.py`または`streamlit run src/frontend/signage_app.py`で起動

## よくある問題と解決策

### インポートエラー
- `sys.path.insert()`は`signage_app.py`のみで使用
- 他のモジュールは絶対インポート(`from backend.xxx import yyy`)

### .envが見つからない
- `.env.example`を`.env`にコピー
- `Settings()`初期化時にチェックされる

### PLC接続エラー
- `DEBUG_DUMMY_READ=true`でダミーモード確認
- IP/ポート設定を`.env`で確認
- ネットワーク疎通確認

## コード品質
- Black: フォーマッター(自動整形)
- Ruff: Linter(静的解析)
- Pylance: VSCode型チェック
- 全てセットアップ済み(`.vscode/settings.json`)

## 命名規則
- クラス: `PascalCase` (例: `PLCClient`, `ProductionData`)
- 関数/変数: `snake_case` (例: `get_plc_client`, `remain_min`)
- 定数: `UPPER_SNAKE_CASE` (例: `REFRESH_INTERVAL`, `USE_PLC`)
- プライベート: `_leading_underscore` (例: `_instance`)

## ドキュメント
- Docstring: Google Style
- 型ヒントで大部分は自己文書化
- 複雑なロジックにはインラインコメント

## 定期メンテナンス手順

### 大きな変更時・仕事終わりのチェックリスト

#### 1. 全スキャンによるテスト項目チェック
大きな機能追加や1日の開発終了時に、テストの過不足をチェック:

```bash
# 全Pythonファイルをスキャン
semantic_search "main application logic business logic functions classes"

# 既存テストと比較して未カバーのコンポーネントを特定
```

**チェック対象**:
- [ ] 新規追加した関数にテストがあるか
- [ ] 修正した計算ロジックのテストケースが十分か
- [ ] 新しいPydanticモデルにバリデーションテストがあるか
- [ ] エラーハンドリングのテストが網羅されているか

**テスト追加が必要な場合**:
1. 該当コンポーネントのテストファイルを作成 (`tests/<module>/test_<component>.py`)
2. モックを活用してPLC未接続でもテスト可能にする
3. `pytest tests/ -v` で全テスト実行し、合格を確認
4. GitHub Actionsでも自動テストが通ることを確認

#### 2. 開発ログの作成
その日の開発内容をまとめた資料を`dev_logs/`フォルダに生成:

```bash
# ファイル名: dev_logs/YYYY-MM-DD.md (例: dev_logs/2025-11-14.md)
```

**ログに記載する内容**:
- **実施内容サマリー**: 何を追加・修正したか
- **テスト結果**: 新規テスト数、全体のテスト実行結果
- **カバレッジ分析**: テスト済みモジュールと未テスト箇所
- **発見した課題と対応**: バグや改善点
- **CI/CD確認**: GitHub Actionsの結果
- **今後の改善案**: 次回以降のTODO

**テンプレート構成例**:
```markdown
# 開発ログ - YYYY-MM-DD

## 📋 実施内容サマリー
...

## 📝 詳細レポート
### A. 新規機能/修正
...

## 🧪 テスト実行結果
...

## 📊 カバレッジ分析
...

## 🔍 発見した課題と対応
...

## ✅ CI/CD確認
...

## 🚀 今後の改善案
...

## 📌 まとめ
...
```

#### 3. GitHub Actions確認
GitHub ActionsのTest/Lintワークフローが合格していることを確認:

```bash
# ローカルで事前確認
uv run pytest tests/ -v
uv run ruff check src/ tests/
uv run black --check src/ tests/

# GitHubで確認
# https://github.com/Moge800/rpi_digital_signage/actions
```

#### 4. コミット前の最終チェック
```bash
# 1. 全テスト実行
pytest tests/ -v --tb=short

# 2. Lint確認
ruff check src/ tests/
black --check src/ tests/

# 3. 型チェック (VSCode Pylance)
# エラーパネルで確認

# 4. 変更差分確認
git status
git diff

# 5. コミット
git add .
git commit -m "feat: <変更内容の要約>"
git push origin main
```

### 推奨頻度
- **テストチェック**: 大きな機能追加時 or 1日の終わり
- **開発ログ作成**: 1日の終わり (複数日にまたがる場合は節目で)
- **CI/CD確認**: 毎pushごと (自動)
- **カバレッジ計測**: 週1回 or リリース前

### メリット
- テストの抜け漏れを早期発見
- 開発履歴が明確に記録される
- チーム共有やレビュー時の資料になる
- 将来の自分が過去の判断を理解できる

---

**このプロジェクトは学習目的で開発されています。質問や改善提案は歓迎します！**
