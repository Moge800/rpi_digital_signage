"""フロントエンドUIコンポーネント

デジタルサイネージ画面の各種表示コンポーネントを提供する。
テーマ対応により、ライトモード/ダークモードの切り替えが可能。
"""

import plotly.graph_objects as go
import streamlit as st
from schemas import ProductionData


def get_theme_colors(theme: str = "dark") -> dict[str, str]:
    """テーマに応じた色設定を取得

    Args:
        theme: "dark" または "light"

    Returns:
        dict[str, str]: 色設定辞書
            - bg_color: 背景色
            - text_color: テキスト色
            - gauge_bg: ゲージ背景色
            - gauge_bar: ゲージバー色
            - gauge_step_1: ゲージステップ1色 (0-80%)
            - gauge_step_2: ゲージステップ2色 (80-100%)
            - status_ok_bg: 正常ステータス背景色
            - status_warn_bg: 警告ステータス背景色
            - status_alarm_bg: 異常ステータス背景色
    """
    if theme == "light":
        return {
            "bg_color": "#ffffff",
            "text_color": "#000000",
            "gauge_bg": "#f5f5f5",
            "gauge_bar": "#31c77f",
            "gauge_step_1": "#e0e0e0",
            "gauge_step_2": "#c0c0c0",
            "status_ok_bg": "#c8e6c9",
            "status_ok_border": "#4caf50",
            "status_warn_bg": "#fff9c4",
            "status_warn_border": "#ffc107",
            "status_alarm_bg": "#ffcdd2",
            "status_alarm_border": "#f44336",
        }
    else:  # dark (デフォルト)
        return {
            "bg_color": "#000000",
            "text_color": "#f5f5f5",
            "gauge_bg": "#000000",
            "gauge_bar": "#31c77f",
            "gauge_step_1": "#333333",
            "gauge_step_2": "#555555",
            "status_ok_bg": "#145c32",
            "status_ok_border": "#1f7e46",
            "status_warn_bg": "#744000",
            "status_warn_border": "#f0a000",
            "status_alarm_bg": "#7a0000",
            "status_alarm_border": "#ff3333",
        }


def get_status_info(alarm: bool, progress: float) -> tuple[str, str]:
    """生産状況からステータス情報を取得

    Args:
        alarm: 異常フラグ
        progress: 進捗率 (0.0-1.0)

    Returns:
        tuple[str, str]: (CSSクラス名, ステータステキスト)

    Examples:
        >>> get_status_info(True, 0.5)
        ('status-alarm', '⚠ 異常発生')
        >>> get_status_info(False, 1.0)
        ('status-ok', '✅ 目標進捗')
    """
    if alarm:
        return ("status-alarm", "⚠ 異常発生")
    elif progress >= 1.0:
        return ("status-ok", "✅ 目標進捗")
    elif progress >= 0.8:
        return ("status-warn", "▲ 要注意")
    else:
        return ("status-ok", "● 稼働中")


def get_gauge_figure(progress: float, theme: str = "dark") -> go.Figure:
    """生産進捗率のゲージ図を生成

    Plotlyを使用して、進捗率を視覚的に表示するゲージチャートを作成する。
    テーマに応じて配色を自動調整する。

    Args:
        progress: 進捗率 (0.0-1.0)
        theme: "dark" または "light"

    Returns:
        go.Figure: Plotlyゲージ図オブジェクト

    Examples:
        >>> fig = get_gauge_figure(0.75, theme="dark")
        >>> fig.show()  # Streamlitで表示
    """
    colors = get_theme_colors(theme)

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=progress * 100,
            number={"suffix": "%"},  # パーセント記号を追加
            # title={"text": "生産進捗率"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": colors["gauge_bar"]},
                "steps": [
                    {"range": [0, 80], "color": colors["gauge_step_1"]},
                    {"range": [80, 100], "color": colors["gauge_step_2"]},
                ],
                "threshold": {
                    "line": {"color": "red", "width": 4},
                    "thickness": 0.8,
                    "value": 100,
                },
            },
        )
    )

    fig.update_layout(
        margin=dict(t=30, b=5, l=30, r=30),
        height=350,  # フルHD対応：ゲージの高さを制限
        paper_bgcolor=colors["gauge_bg"],
        font=dict(color=colors["text_color"]),
    )

    return fig


def render_header(data: ProductionData) -> None:
    """ヘッダー部分をレンダリング

    ライン名、機種名、タイムスタンプを表示する。

    Args:
        data: 生産データ
    """
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


def render_production_metrics(data: ProductionData, progress: float) -> None:
    """生産数量メトリクスをレンダリング

    計画数、実績数、進捗率、パレット情報を表示する。

    Args:
        data: 生産データ
        progress: 進捗率 (0.0-1.0)
    """
    st.markdown(
        f"<div class='kpi-value-big' style='text-align: center;'>{data.actual:,d} <span style='font-size: 0.6em; color: #888;'>/ {data.plan:,d}</span></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='kpi-label' style='text-align: center; margin-top: -10px;'>投入数 / 生産数量</div>",
        unsafe_allow_html=True,
    )
    st.progress(progress)

    # パレット情報（最重要）
    required_pallets = data.plan / data.fully
    st.markdown(
        f"<div class='kpi-value-big' style='text-align: center; margin-top: 1rem; color: #31c77f;'>PL {data.remain_pallet:.1f} <span style='font-size: 0.6em; color: #888;'>/ {required_pallets:.1f}</span></div>",
        unsafe_allow_html=True,
    )


def render_time_and_status(data: ProductionData, progress: float) -> None:
    """残り時間とステータスをレンダリング

    残り生産時間と装置ステータスを表示する。

    Args:
        data: 生産データ
        progress: 進捗率 (0.0-1.0)
    """
    hours = data.remain_min // 60
    mins = data.remain_min % 60
    st.markdown(
        f"<div class='kpi-value-big' style='text-align: center;'>{hours:02d}<span style='font-size: 0.6em; color: #888;'>時間</span>{mins:02d}<span style='font-size: 0.6em; color: #888;'>分</span></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='kpi-label' style='text-align: center; margin-top: -10px;'>残り生産時間</div>",
        unsafe_allow_html=True,
    )

    status_class, status_text = get_status_info(data.alarm, progress)
    st.markdown(
        f"<div class='{status_class}' style='text-align: center; margin-top: 1rem;'>{status_text}</div>",
        unsafe_allow_html=True,
    )


def render_alarm_bar(data: ProductionData) -> None:
    """アラームバーをレンダリング

    異常発生時は赤色バー、正常時は緑色バーを表示する。

    Args:
        data: 生産データ
    """
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
