"""
Raspberry Pi Digital Signage - PLC生産データ表示システム

## アーキテクチャ概要

レイヤー構造 (依存関係は下位→上位のみ):

┌─────────────────────────────────────────────────────┐
│ frontend/                                           │  最上位層
│  └── signage_app.py - Streamlit UI                 │
├─────────────────────────────────────────────────────┤
│ backend/                                            │  中間層
│  ├── utils.py - ビジネスロジック・データ取得       │
│  ├── plc/ - PLC通信クライアント (Type3E)           │
│  └── logging/ - アプリケーションロガー             │
├─────────────────────────────────────────────────────┤
│ config/                                             │  設定層
│  ├── settings.py - 環境変数管理 (Pydantic Settings)│
│  └── production_config.py - 機種マスタ管理         │
├─────────────────────────────────────────────────────┤
│ schemas/                                            │  最下位層
│  ├── production.py - ProductionData                │
│  └── production_type.py - ProductionTypeConfig     │
└─────────────────────────────────────────────────────┘

## 依存ルール

1. **上位層 → 下位層**: 許可 (frontend → backend → config → schemas)
2. **下位層 → 上位層**: 禁止 (循環参照防止)
3. **schemas/**: 外部ライブラリ (pydantic) のみに依存
4. **同一層内**: 相互依存は最小限に (必要なら分割を検討)

## 使用例

```python
# 推奨: 各層から必要なものだけimport
from schemas import ProductionData
from config import Settings
from backend.plc.plc_client import get_plc_client
```

## 設計原則

- **Single Responsibility**: 各モジュールは単一の責務を持つ
- **Dependency Inversion**: 具象ではなく抽象に依存 (BasePLCClient等)
- **Open/Closed**: 拡張に開き、修正に閉じる
"""

__version__ = "0.1.0"
__author__ = "Moge800"
