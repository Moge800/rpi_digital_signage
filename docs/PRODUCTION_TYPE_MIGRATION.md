# 機種マスタ管理の変更

## 変更内容

従来のPythonコード内での機種定義から、**ライン別JSONファイル方式**に変更しました。

### 変更理由

- 他の製造ラインで全く異なる機種マスタを使用する
- ライン追加時にコード変更不要
- 機種情報の更新がJSON編集のみで完結

## 構成

```
config/production_types/
├── README.md          # 設定ガイド
├── LINE_1.json        # ライン1の機種マスタ
├── LINE_2.json        # ライン2の機種マスタ
└── ...                # 追加ライン用JSON
```

### ファイル選択ロジック

`.env`の`LINE_NAME`に対応するJSONを自動読み込み:

```env
LINE_NAME=LINE_1  # → config/production_types/LINE_1.json
```

## 使い方

### 1. ライン用JSONを作成

`config/production_types/{LINE_NAME}.json`:

```json
{
  "0": {
    "production_type": 0,
    "name": "未設定",
    "fully": 1,
    "production_rate_per_minute": 1
  },
  "1": {
    "production_type": 1,
    "name": "機種A",
    "fully": 2800,
    "production_rate_per_minute": 50
  }
}
```

### 2. `.env`設定

```env
LINE_NAME=LINE_1
```

### 3. 自動読み込み

アプリケーション起動時に該当JSONを自動で読み込みます。

## API変更

### 従来

```python
from schemas import PRODUCTION_TYPE_CONFIGS

configs = PRODUCTION_TYPE_CONFIGS  # 固定辞書
```

### 新方式

```python
from schemas import get_production_type_config, load_production_type_configs

# 個別取得 (変更なし)
config = get_production_type_config(1)

# 全件取得 (新規追加)
all_configs = load_production_type_configs()  # 環境変数LINE_NAMEから読み込み
all_configs = load_production_type_configs("LINE_2")  # 明示的にライン指定
```

## 既存コードへの影響

`get_production_type_config(production_type)`の呼び出しは**変更不要**です。

## エラーハンドリング

- JSONファイル未存在 → `FileNotFoundError`
- JSON形式不正 → `ValueError`
- Pydantic検証エラー → `ValueError`

## マイグレーション手順

1. `config/production_types/`に既存の機種データをJSONで作成
2. `.env`で`LINE_NAME`を設定
3. アプリケーション起動でテスト
4. 問題なければデプロイ

## サンプル: 複数ライン展開

### ライン1 (供給装置)

```json
// config/production_types/LINE_1.json
{
  "1": {"production_type": 1, "name": "機種A", "fully": 2800, "production_rate_per_minute": 50}
}
```

### ライン2 (組立ライン)

```json
// config/production_types/LINE_2.json
{
  "1": {"production_type": 1, "name": "別機種X", "fully": 4000, "production_rate_per_minute": 80}
}
```

### 設定

```env
# ライン1用
LINE_NAME=LINE_1

# ライン2用
LINE_NAME=LINE_2
```

## 利点

✅ ライン追加でコード変更不要  
✅ 機種情報の更新がJSON編集のみ  
✅ Pydanticで型安全性維持  
✅ 環境変数で簡単切り替え  
✅ Gitで機種データをバージョン管理

## 注意事項

- JSONファイル名は`LINE_NAME`と完全一致必須
- UTF-8エンコーディングで保存
- 機種番号0-15の範囲を守る
- `fully`と`production_rate_per_minute`は1以上
