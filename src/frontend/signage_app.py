"""Streamlit デジタルサイネージ フロントエンド

FastAPI バックエンドからデータを取得し、表示するUIアプリケーション。
PLC通信はバックエンドに委譲し、フロントエンドは表示に専念。

起動方法:
    streamlit run src/frontend/signage_app.py
"""

import sys
import gc
from pathlib import Path
import tempfile

import streamlit as st
from streamlit_autorefresh import st_autorefresh
from dotenv import load_dotenv
import httpx

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

# .envファイルを読み込む
load_dotenv()

from frontend.styles import get_page_styles
from frontend.components import (
    get_gauge_figure,
    render_header,
    render_production_metrics,
    render_time_and_status,
    render_alarm_bar,
)
from frontend.api_client import (
    fetch_production_from_api,
    check_api_health,
    request_time_sync,
)
from schemas import ProductionData
from config.settings import Settings
from backend.config_helpers import get_refresh_interval
from backend.logging import app_logger as logger

# --------------------------
#  定数定義
# --------------------------
settings = Settings()
REFRESH_INTERVAL = get_refresh_interval()
THEME = settings.THEME  # UIテーマ (dark/light)

# メモリクリーンアップ間隔 (リフレッシュ回数)
GC_INTERVAL = 100  # 100回リフレッシュごとにGC実行 (約5分@3秒間隔)

# 初期化フラグファイル（セッションリセット対策）
# /tmp は再起動でクリアされるので、起動ごとに1回だけ初期化される
_INIT_FLAG_FILE = Path(tempfile.gettempdir()) / "signage_frontend_initialized.flag"


def _is_already_initialized() -> bool:
    """初期化済みかどうかをファイルで確認（セッションリセット対策）"""
    return _INIT_FLAG_FILE.exists()


def _mark_initialized() -> None:
    """初期化完了をファイルに記録"""
    try:
        _INIT_FLAG_FILE.touch()
        logger.debug(f"Frontend initialization flag created: {_INIT_FLAG_FILE}")
    except OSError as e:
        logger.warning(f"Failed to create init flag: {e}")


# --------------------------
#  初期化処理（起動後1回のみ）
# --------------------------
if not _is_already_initialized():
    logger.info("Frontend initializing...")

    # APIサーバーのヘルスチェック
    if check_api_health():
        logger.info("API server is healthy")

        # 時刻同期をAPIに依頼
        sync_result = request_time_sync()
        if sync_result["success"]:
            logger.info(f"Time synced via API: {sync_result['synced_time']}")
        else:
            logger.warning(f"Time sync via API failed: {sync_result['message']}")
    else:
        logger.error("API server is not available!")
        st.error("⚠️ APIサーバーに接続できません。バックエンドが起動しているか確認してください。")

    _mark_initialized()


# --------------------------
#  データ取得部
# --------------------------
def get_production_data() -> ProductionData:
    """APIから生産データを取得する

    Returns:
        ProductionData: 生産データ (計画/実績/アラーム等)
            エラー時はalarm=True、alarm_msgにエラー内容を設定

    Note:
        この関数はStreamlitの自動リフレッシュサイクルごとに
        呼び出される (REFRESH_INTERVAL秒ごと)。
        全ての例外をキャッチしてホワイトアウトを防止。
    """
    try:
        return fetch_production_from_api()
    except httpx.HTTPStatusError as e:
        logger.error(f"API error: {e}")
        error_data = ProductionData.error()
        error_data.alarm_msg = f"APIエラー: {e.response.status_code}"
        return error_data
    except httpx.RequestError as e:
        logger.error(f"API connection error: {e}")
        error_data = ProductionData.error()
        error_data.alarm_msg = "APIサーバー接続エラー"
        return error_data
    except Exception as e:
        logger.critical(f"Unexpected error in get_production_data: {e}")
        error_data = ProductionData.error()
        error_data.alarm_msg = f"システムエラー: {str(e)[:50]}"
        return error_data


# --------------------------
#  ページ基本設定
# --------------------------
st.set_page_config(
    page_title="生産モニタ",
    layout="wide",
)

# --------------------------
#  見た目調整用CSS
# --------------------------
st.markdown(
    get_page_styles(theme=THEME),
    unsafe_allow_html=True,
)

# --------------------------
#  自動更新
# --------------------------
st_autorefresh(interval=REFRESH_INTERVAL * 1000, key="datarefresh")

# --------------------------
#  定期メモリクリーンアップ
# --------------------------
# リフレッシュカウンタを初期化
if "refresh_count" not in st.session_state:
    st.session_state["refresh_count"] = 0

st.session_state["refresh_count"] += 1

# 一定間隔でガベージコレクション実行
if st.session_state["refresh_count"] >= GC_INTERVAL:
    collected = gc.collect()
    logger.debug(f"GC collected {collected} objects")
    st.session_state["refresh_count"] = 0

# --------------------------
#  データ取得
# --------------------------
data = get_production_data()

# --------------------------
#  レンダリング（エラー時も更新継続）
# --------------------------
try:
    # ===== ヘッダ =====
    render_header(data)
    st.markdown("---")

    # 進捗率計算
    progress = min(1.0, data.actual / data.plan) if data.plan else 0

    # ===== メイン: ゲージ =====
    gauge_fig = get_gauge_figure(progress, theme=THEME)
    st.plotly_chart(gauge_fig, width="stretch")

    # ===== 下部: 生産情報 =====
    col_left, col_right = st.columns(2)

    # ---- 左：生産数量 ----
    with col_left:
        render_production_metrics(data, progress)

    # ---- 右：残り時間 ＋ ステータス ----
    with col_right:
        render_time_and_status(data, progress)

    # ===== 下段：異常バー =====
    st.markdown("---")
    render_alarm_bar(data)

except Exception as e:
    # レンダリングエラー時も画面を維持し、更新を継続
    logger.error(f"Rendering error: {e}")
    st.error(f"表示エラー: {e}")
    st.markdown("---")
    st.warning("データ取得は継続中です。最新情報の取得をお待ちください。")

st.markdown(
    f"<div class='footer'>更新間隔：{REFRESH_INTERVAL}秒 / Powered by Streamlit + FastAPI</div>",
    unsafe_allow_html=True,
)
