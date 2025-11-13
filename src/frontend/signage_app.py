import os
import sys
from pathlib import Path
import random
from datetime import datetime
import plotly.graph_objects as go
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

# .envファイルを読み込む
load_dotenv()

from schemas import ProductionData
from backend.plc.plc_client import get_plc_client
from backend.utils import get_refresh_interval, get_use_plc
from backend.logging import app_logger as logger

# --------------------------
#  定数定義
# --------------------------
REFRESH_INTERVAL = get_refresh_interval()
USE_PLC = get_use_plc()

# ダミーデータ生成用の定数
SECONDS_PER_PRODUCT = 1.2  # 1個あたりの生産時間(秒) (50個/分 = 1.2秒/個)
ALARM_THRESHOLD = 8000  # アラーム判定の閾値
ALARM_PROBABILITY = 0.5  # アラーム発生確率

if USE_PLC:

    @st.cache_resource
    def cache_plc_client():
        return get_plc_client()

    client = cache_plc_client()
    try:
        words = client.read_words("D100", size=10)
        bits = client.read_bits("M100", size=10)
    except Exception as e:
        st.error(f"PLCからのデータ取得に失敗: {e}")  # UI上にエラー表示
        logger.error(f"PLC read error: {e}")  # ログファイルに記録
else:
    pass


# --------------------------
#  ダミーデータ取得部
#  （ここをPLC / DB / APIに差し替え）
# --------------------------
def get_production_data() -> ProductionData:
    from backend.utils import calculate_remain_pallet, get_config_data

    line_name = os.getenv("LINE_NAME", "NONAME")
    production_type = 0
    config = get_config_data(production_type)
    production_name = config.production_name if config else "NONE"
    plan = 45000
    actual = random.randint(0, plan)
    remain_seconds = max(0, (plan - actual) * SECONDS_PER_PRODUCT)
    remain_min = int(remain_seconds / 60.0)
    alarm_flag = actual > ALARM_THRESHOLD and random.random() < ALARM_PROBABILITY
    alarm_msg = "装置異常発生中" if alarm_flag else ""
    remain_pallet = calculate_remain_pallet(plan, actual, production_type=0, decimals=1)

    return ProductionData(
        line_name=line_name,
        production_type=production_type,
        production_name=production_name,
        plan=plan,
        actual=actual,
        in_operating=True,
        remain_min=remain_min,
        remain_pallet=remain_pallet,
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
#  見た目調整用CSS(軽め)
# --------------------------
st.markdown(
    """
    <style>
    /* Streamlitのヘッダーを非表示 */
    header {
        visibility: hidden;
    }
    /* Streamlitのメニューボタンを非表示 */
    #MainMenu {
        visibility: hidden;
    }
    /* Streamlitのフッターを非表示 */
    footer {
        visibility: hidden;
    }
    /* 全体を黒背景に */
    .stApp {
        background-color: #000000;
    }
    /* 上部の余白を確保 */
    .main > div {
        padding-top: 2rem;
    }
    body {
        background-color: #000000;
        color: #f5f5f5;
    }
    .block-container {
        padding-top: 1rem;
        padding-bottom: 0.2rem;
        max-width: 95%;
        background-color: #000000;
    }
    .header-title {
        font-size: 5.2rem;
        font-weight: 700;
        padding: 0.2rem 0;
        color: #ffffff;
    }
    .header-time {
        font-size: 1.1rem;
        text-align: right;
        color: #d0d0d0;
    }
    .kpi-label {
        font-size: 5rem;
        color: #bbbbbb;
    }
    .kpi-value-big {
        font-size: 8.0rem;
        font-weight: 800;
        color: #ffffff;
    }
    .kpi-sub {
        font-size: 4.0rem;
        color: #cccccc;
    }
    .status-ok {
        font-size: 3rem;
        background: #145c32;
        padding: 0.8rem;
        border-radius: 0.6rem;
        border: 1px solid #1f7e46;
        color: #ffffff;
        font-weight: 600;
    }
    .status-warn {
        font-size: 3rem;
        background: #744000;
        padding: 0.8rem;
        border-radius: 0.6rem;
        border: 1px solid #f0a000;
        color: #ffffff;
        font-weight: 600;
    }
    .status-alarm {
        font-size: 3rem;
        background: #7a0000;
        padding: 0.8rem;
        border-radius: 0.6rem;
        border: 1px solid #ff3333;
        color: #ffffff;
        font-weight: 600;
    }
    .alarm-bar {
        background: linear-gradient(90deg, #ff0000, #ff8800);
        color: white;
        font-size: 4.4rem;
        font-weight: 700;
        padding: 0.4rem 1.0rem;
        border-radius: 0.5rem;
        text-align: left;
    }
    .footer {
        font-size: 0.8rem;
        color: #888888;
        text-align: right;
        padding-top: 0.2rem;
    }
    /* プログレスバーのスタイル調整 */
    .stProgress > div > div > div > div {
        background-color: #31c77f;
    }
    /* 区切り線を見やすく */
    hr {
        border-color: #333333;
    }
    </style>
""",
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
col_head_l, col_head_r = st.columns([3, 1])
with col_head_l:
    st.markdown(
        f"<div class='header-title'>{data.line_name} 生産進捗 - {data.production_name}</div>",
        unsafe_allow_html=True,
    )
with col_head_r:
    st.markdown(
        f"<div class='header-time'>{data.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</div>",
        unsafe_allow_html=True,
    )

st.markdown("---")

# ===== 上段：生産数量 ＋ 残り時間 =====
col_left, col_right = st.columns([2, 1])

# ---- 左：生産数量 ----
with col_left:
    st.markdown(
        "<div class='kpi-label'>投入数/生産数量 [残りPL数]</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='kpi-value-big'>{data.actual:,d} / {data.plan:,d} [{data.remain_pallet:,.1f}PL]</div>",
        unsafe_allow_html=True,
    )
    progress = min(1.0, data.actual / data.plan) if data.plan else 0
    st.progress(progress)
    st.markdown(
        f"<div class='kpi-sub'>進捗率：{progress*100:,.1f}%</div>",
        unsafe_allow_html=True,
    )

# ---- 右：残り時間 ＋ ステータス ----
with col_right:
    st.markdown("<div class='kpi-label'>残り生産時間</div>", unsafe_allow_html=True)
    h = data.remain_min // 60
    m = data.remain_min % 60
    st.markdown(
        f"<div class='kpi-value-big'>{h:02d}時間{m:02d}分</div>",
        unsafe_allow_html=True,
    )

    if data.alarm:
        status_class = "status-alarm"
        status_text = "⚠ 異常発生"
    elif progress >= 1.0:
        status_class = "status-ok"
        status_text = "✅ 目標進捗"
    elif progress >= 0.8:
        status_class = "status-warn"
        status_text = "▲ 要注意"
    else:
        status_class = "status-ok"
        status_text = "● 稼働中"

    st.markdown(
        f"<div class='{status_class}'><b>装置ステータス：</b> {status_text}</div>",
        unsafe_allow_html=True,
    )

# ===== 中段：ゲージ =====
gauge_fig = go.Figure(
    go.Indicator(
        mode="gauge+number",
        value=progress * 100,
        title={"text": "生産進捗率（%）"},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": "#31c77f"},
            "steps": [
                {"range": [0, 80], "color": "#333333"},
                {"range": [80, 100], "color": "#555555"},
            ],
            "threshold": {
                "line": {"color": "red", "width": 4},
                "thickness": 0.8,
                "value": 100,
            },
        },
    )
)
gauge_fig.update_layout(
    margin=dict(t=40, b=10, l=40, r=40),
    paper_bgcolor="#000000",
    font=dict(color="#f5f5f5"),
)
st.plotly_chart(gauge_fig, width="stretch")

# ===== 下段：異常バー =====
st.markdown("---")
if data.alarm:
    st.markdown(
        f"<div class='alarm-bar'>【異常】{data.alarm_msg}</div>",
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        "<div class='alarm-bar' style='background:#145c32;'>現在、異常はありません。</div>",
        unsafe_allow_html=True,
    )

st.markdown(
    "<div class='footer'>更新間隔：10秒 / Powered by Streamlit</div>",
    unsafe_allow_html=True,
)
