# Draft: PLC値揺らぎに対するバリデーション緩和方針

## 背景
現状は厳密バリデーション寄りのため、PLC値の一時的な揺らぎで `default_error_data()` へ倒れやすい。
その結果、画面/APIが過剰に ERROR 表示になり、運用ノイズが増える。

## 方針（段階的）
1. **取得層で sanitize**（落とさない）
   - `production_type`: 範囲外は「前回有効値」優先、なければ 0
   - 数値項目: 負数は 0 に clamp
2. **ドメイン層で計算**
   - 計算不能時のみ warning ログ、可能な範囲で継続
3. **表示層で状態可視化**
   - `degraded` / `sanitized` フラグを追加検討
   - 全体 ERROR への即時フォールバックを減らす

## 最小変更案（Phase 1）
- `plc_fetcher.py`
  - `sanitize_production_fields(...)` を追加
  - `config not found` 時は `UNKNOWN` で継続（完全停止回避）
- `schemas/production.py`
  - スキーマ厳密性は維持（入力前 sanitize を前提）

## 受け入れ条件
- PLC一時異常時に画面が即 ERROR 固定化しない
- warning ログで追跡可能
- 既存テストが通過 + sanitize 追加テストを新設

## 次のPRで実装する内容
- sanitize 関数実装
- `default_error_data()` 直行条件の見直し
- 単体テスト追加（揺らぎデータケース）

（OpenClaw代行）
