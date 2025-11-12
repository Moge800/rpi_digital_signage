# 機種マスタファイル

各製造ラインごとに機種マスタを定義します。

## ファイル命名規則

`{LINE_NAME}.json` (環境変数の`LINE_NAME`と一致させる)

例:
- `LINE_1` → `line_1.json`
- `生産ライン1` → `生産ライン1.json`

## JSONフォーマット

```json
{
  "機種番号(0-15)": {
    "production_type": 機種番号,
    "name": "機種名",
    "fully": パレット積載数,
    "seconds_per_product": 1個あたりの生産時間(秒, float)
  }
}
```

## 使い方

1. `.env`ファイルで`LINE_NAME`を設定
   ```env
   LINE_NAME=LINE_1
   ```

2. 対応するJSONファイルを作成
   ```
   config/production_types/LINE_1.json
   ```

3. アプリケーション起動時に自動読み込み

## サンプル

### line_1.json (供給装置)

```json
{
  "1": {
    "production_type": 1,
    "name": "機種A",
    "fully": 2800,
    "seconds_per_product": 1.2
  }
}
```

### line_2.json (別ライン)

```json
{
  "1": {
    "production_type": 1,
    "name": "別機種X",
    "fully": 4000,
    "seconds_per_product": 0.75
  }
}
```

## 注意事項

- 機種番号は0-15の範囲
- `fully`は1以上の整数
- `seconds_per_product`は0より大きいfloat値 (例: 50個/分 = 60÷50 = 1.2秒/個)
- ファイル名は`LINE_NAME`と正確に一致させる
- UTF-8エンコーディングで保存
