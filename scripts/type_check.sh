#!/bin/bash
# Lint & Type Checkをまとめて実行

set -e  # エラー時に停止

echo "🔍 Running Ruff..."
uv run ruff check src/ tests/

echo "🎨 Running Black..."
uv run black --check src/ tests/

echo "🔎 Running mypy..."
uv run mypy src/ tests/

echo "✅ All checks passed!"