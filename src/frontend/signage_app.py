import sys
from pathlib import Path
import random
from datetime import datetime

import streamlit as st
from streamlit_autorefresh import st_autorefresh
from dotenv import load_dotenv

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
from schemas import ProductionData
from config.settings import Settings
from backend.system_utils import set_system_clock
from backend.plc.plc_client import get_plc_client, PLCClient
from backend.plc.plc_fetcher import (
    fetch_production_data,
    fetch_production_timestamp,
    get_plc_device_dict,
)
from backend.config_helpers import get_refresh_interval, get_use_plc
from backend.logging import app_logger as logger

# --------------------------
#  定数定義
# --------------------------
settings = Settings()
REFRESH_INTERVAL = get_refresh_interval()
USE_PLC = get_use_plc()
THEME = settings.THEME  # UIテーマ (dark/light)

# ダミーデータ生成用の定数
SECONDS_PER_PRODUCT = 1.2  # 1個あたりの生産時間(秒) (50個/分 = 1.2秒/個)
ALARM_THRESHOLD = 8000  # アラーム判定の閾値
ALARM_PROBABILITY = 0.5  # アラーム発生確率
MAX_PRODUCTION_TYPE = 2  # ダミーモードで使用する最大機種番号

# --------------------------
#  PLC接続初期化
# --------------------------
if USE_PLC:

    @st.cache_resource
    def cache_plc_client() -> PLCClient:
        """PLCクライアントをキャッシュする (Streamlit再実行対策)

        Returns:
            PLCClient: キャッシュされたPLCクライアントインスタンス
        """
        return get_plc_client()

    client = cache_plc_client()

    # セッション終了時のクリーンアップ登録（初回のみ）
    if "cleanup_registered" not in st.session_state:
        import atexit

        def cleanup_plc():
            """アプリケーション終了時にPLC接続をクリーンアップ"""
            try:
                if client and client.connected:
                    client.disconnect()
                    logger.info("PLC connection closed on app exit")
            except Exception as e:
                logger.warning(f"Error during PLC cleanup: {e}")

        atexit.register(cleanup_plc)
        st.session_state["cleanup_registered"] = True

    # システム時刻同期（初回のみ実行）
    if "system_clock_synced" not in st.session_state:
        try:
            plc_time = fetch_production_timestamp(
                client, get_plc_device_dict().TIME_DEVICE
            )
            if set_system_clock(plc_time):
                logger.info(f"System clock synced with PLC: {plc_time}")
                st.session_state["system_clock_synced"] = True
            else:
                logger.warning("Failed to sync system clock with PLC")
        except (ConnectionError, OSError, TimeoutError) as e:
            logger.error(f"PLC time sync error: {e}")
            st.error(f"PLC時刻同期に失敗しました: {e}")


# --------------------------
#  データ取得部
# --------------------------
def get_production_data() -> ProductionData:
    """生産データを取得する

    USE_PLC=true時はPLCから実データを取得。
    USE_PLC=false時はダミーデータを生成。

    Returns:
        ProductionData: 生産データ
    """
    if USE_PLC:
        # PLC実データ取得
        try:
            return fetch_production_data(client)
        except (ConnectionError, OSError, TimeoutError) as e:
            logger.error(f"PLC data fetch error: {e}")
            st.error(f"PLCデータ取得エラー: {e}")
            # エラー時はダミーデータにフォールバック
            return _get_dummy_data()
    else:
        # ダミーモード
        return _get_dummy_data()


def _get_dummy_data() -> ProductionData:
    """ダミーデータを生成する (内部使用)

    Returns:
        ProductionData: ランダムなダミーデータ
    """
    from backend.calculators import calculate_remain_pallet
    from backend.config_helpers import get_config_data

    line_name = settings.LINE_NAME
    production_type = random.randint(0, MAX_PRODUCTION_TYPE)
    config = get_config_data(production_type)
    production_name = config.name if config else "NONE"
    fully = config.fully if config else 0  # 満杯パレット数を取得
    plan = 45000
    actual = random.randint(0, plan)
    remain_seconds = max(0, (plan - actual) * SECONDS_PER_PRODUCT)
    remain_min = int(remain_seconds / 60.0)
    alarm_flag = actual > ALARM_THRESHOLD and random.random() < ALARM_PROBABILITY
    alarm_msg = "装置異常発生中" if alarm_flag else ""
    remain_pallet = calculate_remain_pallet(
        plan, actual, production_type=production_type, decimals=1
    )

    return ProductionData(
        line_name=line_name,
        production_type=production_type,
        production_name=production_name,
        plan=plan,
        actual=actual,
        in_operating=True,
        remain_min=remain_min,
        remain_pallet=remain_pallet,
        fully=fully,
        alarm=alarm_flag,
        alarm_msg=alarm_msg,
        timestamp=datetime.now(),
    )


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
#  データ取得
# --------------------------
data = get_production_data()

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

st.markdown(
    f"<div class='footer'>更新間隔：{REFRESH_INTERVAL}秒 / Powered by Streamlit</div>",
    unsafe_allow_html=True,
)
