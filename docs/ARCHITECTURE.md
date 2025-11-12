# アーキテクチャ設計ドキュメント

## 現状の問題点

### 🔥 緊急: production_type.pyの重複定義
- `ProductionTypeConfig`クラスが2回定義されている
- importも2回記述されている
- フォーマッター/リンターがエラーを出す状態

### 🤔 設計方針の混乱
1. 最初: Pythonコード内で機種定義 (PRODUCTION_TYPE_CONFIGS)
2. 次: JSONファイル方式に変更
3. 結果: 中途半端な状態で両方が混在

### 📦 依存関係の不明瞭さ
- `utils.py` → `get_production_type_config()` 呼び出し
- グローバル変数 `_PRODUCTION_TYPE_CONFIGS` を使用
- 環境変数 `LINE_NAME` に依存
- ファイルパスをハードコード (`config/production_types/`)

## 正しいアーキテクチャ設計

### レイヤー構成

```
┌─────────────────────────────────────┐
│  Frontend (Streamlit)               │  ← UI層
│  src/frontend/signage_app.py        │
└─────────────┬───────────────────────┘
              │
┌─────────────▼───────────────────────┐
│  Backend (Business Logic)           │  ← ビジネスロジック層
│  src/backend/utils.py               │
│  - fetch_production_data()          │
│  - fetch_production_timestamp()     │
│  - remain_pallet_calculation()      │
│  - calculate_remain_minutes()       │
└─────────────┬───────────────────────┘
              │
    ┌─────────┴─────────┐
    │                   │
┌───▼──────────┐  ┌────▼──────────────┐
│ PLC Client   │  │ Config Manager    │  ← インフラ層
│ plc_client.py│  │ production_config │
└──────────────┘  └───────────────────┘
    │                   │
┌───▼──────────┐  ┌────▼──────────────┐
│ PLC Device   │  │ JSON Files        │  ← データソース
│ (MELSEC)     │  │ config/production_│
└──────────────┘  │     types/*.json  │
                  └───────────────────┘
```

### データフロー

```
1. アプリ起動
   ↓
2. ConfigManager初期化 (LINE_NAME読み込み)
   ↓
3. 対応するJSON読み込み (1回のみ、キャッシュ)
   ↓
4. PLCClientから生産データ取得
   ↓
5. ConfigManagerから機種設定取得
   ↓
6. 計算処理 (残パレット、残時間)
   ↓
7. Streamlitで表示
```

### 責務分離

#### 1. schemas/production_type.py (データモデル)
**責務**: 機種設定のデータ構造定義のみ
```python
class ProductionTypeConfig(BaseModel):
    """機種設定のデータモデル"""
    production_type: int
    name: str
    fully: int
    production_rate_per_minute: int
```

#### 2. config/production_config.py (新規作成)
**責務**: 機種マスタの読み込み・管理
```python
class ProductionConfigManager:
    """機種マスタ管理クラス (シングルトン)"""
    
    def __init__(self, line_name: str | None = None):
        """JSONファイルから機種マスタを読み込み"""
        
    def get_config(self, production_type: int) -> ProductionTypeConfig:
        """機種設定を取得"""
        
    def get_all_configs(self) -> dict[int, ProductionTypeConfig]:
        """全機種設定を取得"""
```

#### 3. backend/utils.py (計算ロジック)
**責務**: 生産データの取得・計算
- ConfigManagerに依存
- PLCClientに依存
- 純粋な計算処理

#### 4. frontend/signage_app.py (表示)
**責務**: UIの描画のみ
- utils経由でデータ取得
- 表示ロジックに専念

## リファクタリング計画

### フェーズ1: 緊急修正 (即実施)
- [ ] production_type.pyの重複定義を削除
- [ ] importを整理
- [ ] リンターエラーを解消

### フェーズ2: ConfigManager導入 (次回)
- [ ] config/production_config.py作成
- [ ] ProductionConfigManagerクラス実装
- [ ] シングルトンパターンで実装
- [ ] ユニットテスト作成

### フェーズ3: 既存コード移行
- [ ] utils.pyを修正 (ConfigManager使用)
- [ ] schemas/__init__.pyを修正
- [ ] signage_app.pyを修正 (必要に応じて)

### フェーズ4: テスト・検証
- [ ] 動作確認
- [ ] エラーハンドリング確認
- [ ] ドキュメント更新

## 設計原則

### SOLID原則の適用

#### Single Responsibility (単一責任)
- 各クラス/モジュールは1つの責務のみ
- データモデル ≠ データ取得 ≠ ビジネスロジック

#### Open/Closed (オープン/クローズド)
- 新しいラインの追加はJSON追加のみ
- コード変更不要

#### Dependency Inversion (依存性逆転)
- utils.pyは抽象に依存 (ConfigManagerインターフェース)
- 具体的な実装(JSON読み込み)に依存しない

### その他の原則

#### DRY (Don't Repeat Yourself)
- グローバル変数によるキャッシュは1箇所のみ
- 機種設定の取得ロジックは1箇所に集約

#### 設定の外部化
- 環境変数: .env
- 機種マスタ: JSON
- コードには定数のみ

#### エラーハンドリング
- 各層で適切な例外を定義
- 上位層で適切にハンドリング
- ユーザーフレンドリーなエラーメッセージ

## ディレクトリ構造 (理想形)

```
src/
├── frontend/
│   └── signage_app.py           # UI層
│
├── backend/
│   ├── utils.py                 # ビジネスロジック
│   ├── plc/
│   │   ├── plc_client.py        # PLC通信
│   │   └── base.py
│   └── logging/
│       └── logger.py
│
├── config/
│   ├── settings.py              # 環境変数管理
│   └── production_config.py     # 機種マスタ管理 (新規)
│
└── schemas/
    ├── production.py            # ProductionData
    └── production_type.py       # ProductionTypeConfig (データモデルのみ)
```

## 実装ガイドライン

### ConfigManager実装例

```python
# config/production_config.py
from pathlib import Path
from typing import ClassVar
import json
import os
from schemas.production_type import ProductionTypeConfig


class ProductionConfigManager:
    """機種マスタ管理クラス (シングルトン)"""
    
    _instance: ClassVar["ProductionConfigManager | None"] = None
    _configs: dict[int, ProductionTypeConfig]
    _line_name: str
    
    def __new__(cls, line_name: str | None = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize(line_name)
        return cls._instance
    
    def _initialize(self, line_name: str | None = None) -> None:
        """初期化処理"""
        self._line_name = line_name or os.getenv("LINE_NAME", "LINE_1")
        self._configs = self._load_configs()
    
    def _load_configs(self) -> dict[int, ProductionTypeConfig]:
        """JSONから機種マスタを読み込み"""
        config_dir = Path(__file__).parent.parent / "config" / "production_types"
        config_file = config_dir / f"{self._line_name}.json"
        
        if not config_file.exists():
            raise FileNotFoundError(
                f"Config not found: {config_file}"
            )
        
        with open(config_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return {
            int(k): ProductionTypeConfig(**v)
            for k, v in data.items()
        }
    
    def get_config(self, production_type: int) -> ProductionTypeConfig:
        """機種設定を取得"""
        if production_type not in self._configs:
            raise ValueError(
                f"production_type {production_type} not found in {self._line_name}"
            )
        return self._configs[production_type]
    
    @property
    def line_name(self) -> str:
        """ライン名を取得"""
        return self._line_name
```

### utils.py での使用例

```python
# backend/utils.py
from config.production_config import ProductionConfigManager

def remain_pallet_calculation(
    plan: int, actual: int, production_type: int
) -> int:
    """残パレット数を計算"""
    config_manager = ProductionConfigManager()
    config = config_manager.get_config(production_type)
    
    remain = plan - actual
    return remain // config.fully
```

## まとめ

### やるべきこと
1. **今すぐ**: production_type.pyの重複削除
2. **次**: ProductionConfigManager実装
3. **その後**: 既存コード移行
4. **最後**: テスト・ドキュメント

### やらないこと
- グローバル変数の乱用
- 責務の混在
- ハードコーディング
- 行き当たりばったりの実装

### 成功の指標
✅ 各モジュールの責務が明確  
✅ 新ライン追加がJSON追加のみで完結  
✅ ユニットテストが書ける構造  
✅ エラーハンドリングが適切  
✅ ドキュメントと実装が一致
