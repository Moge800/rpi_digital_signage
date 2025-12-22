"""フロントエンドUIコンポーネント

デジタルサイネージ画面の各種表示コンポーネントを提供する。
テーマ対応により、ライトモード/ダークモードの切り替えが可能。
"""

import plotly.graph_objects as go
import streamlit as st
from schemas import ProductionData
from frontend.styles import get_theme_colors


def get_status_info(
    alarm: bool, progress: float, in_operating: bool
) -> tuple[str, str]:
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
    elif not in_operating:
        return ("status-warn", "● 停止中")
    elif progress >= 1.0:
        return ("status-ok", "✅ 目標進捗")
    elif progress >= 0.8:
        return ("status-warn", "▲ 要注意")
    elif in_operating:
        return ("status-ok", "● 稼働中")
    else:
        return ("status-unknown", "？ 不明")


def get_gauge_figure(
    progress: float, theme: str = "dark", alarm: bool = False
) -> go.Figure:
    """生産進捗率のゲージ図を生成

    Plotlyを使用して、進捗率を視覚的に表示するゲージチャートを作成する。
    テーマに応じて配色を自動調整する。

    Args:
        progress: 進捗率 (0.0-1.0)
        theme: "dark" または "light"
        alarm: 異常フラグ (Trueの場合、ゲージバーが赤くなる)

    Returns:
        go.Figure: Plotlyゲージ図オブジェクト

    Examples:
        >>> fig = get_gauge_figure(0.75, theme="dark")
        >>> fig.show()  # Streamlitで表示
    """
    colors = get_theme_colors(theme)

    # 異常時はstatus_alarm_bg、通常時は緑
    bar_color = colors["status_alarm_bg"] if alarm else colors["gauge_bar"]

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=progress * 100,
            number={"suffix": "%"},  # パーセント記号を追加
            # title={"text": "生産進捗率"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": bar_color},
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
        height=350,  # 1920x1080対応：ゲージの高さ
        paper_bgcolor=colors["gauge_bg"],
        font=dict(color=colors["text_color"]),
    )

    return fig


def render_header(data: ProductionData) -> None:
    """ヘッダー部分をレンダリング

    ライン名・機種名・現在時刻を大きく表示する。
    デジタルサイネージの最上部に配置されるセクション。

    Args:
        data: 生産データ (line_name, production_name, timestampを使用)

    Note:
        Streamlitのst.markdown()でHTMLを直接レンダリング。
        CSSはget_page_styles()で定義されたスタイルを参照。
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


def render_production_metrics(
    data: ProductionData, progress: float, alarm: bool = False, theme: str = "dark"
) -> None:
    """生産数量メトリクスをレンダリング

    計画数・実績数・進捗バー・残りパレット数を表示する。
    各KPIは大きな数値とラベルで視認性を高める。

    Args:
        data: 生産データ (plan, actual, remain_pallet, fullyを使用)
        progress: 進捗率 (0.0-1.0)
        alarm: 異常フラグ (Trueの場合、進捗バーが赤くなる)
        theme: "dark" または "light"

    Note:
        パレット情報 = 残りパレット数 / 必要総パレット数
        必要総パレット数 = plan / fully (1パレットあたりの積載数)
    """
    colors = get_theme_colors(theme)

    st.markdown(
        f"<div class='kpi-value-big' style='text-align: center;'>{data.actual:,d} <span style='font-size: 0.6em; color: #888;'>/ {data.plan:,d}</span></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='kpi-label' style='text-align: center; margin-top: -10px;'>投入数 / 生産数量</div>",
        unsafe_allow_html=True,
    )

    # 異常時はstatus_alarm_bg、通常時は緑のプログレスバー
    bar_color = colors["status_alarm_bg"] if alarm else colors["gauge_bar"]
    percent = min(progress * 100, 100)
    st.markdown(
        f"""
        <div style="background-color: #333; border-radius: 5px; height: 20px; margin: 10px 0;">
            <div style="background-color: {bar_color}; width: {percent}%; height: 100%; border-radius: 5px; transition: width 0.3s ease;"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # パレット情報（最重要）
    # ゼロ除算防止: fully=0の場合は0を返す
    required_pallets = data.plan / data.fully if data.fully > 0 else 0
    st.markdown(
        f"<div class='kpi-value-big' style='text-align: center; margin-top: 1rem;'>{data.remain_pallet:.1f} <span style='font-size: 0.6em; color: #888;'>/ {required_pallets:.1f}</span></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='kpi-label' style='text-align: center; margin-top: -10px;'>残PL / 総PL</div>",
        unsafe_allow_html=True,
    )


def render_time_and_status(data: ProductionData, progress: float) -> None:
    """残り時間とステータスをレンダリング

    残り生産時間(HH時間MM分形式)と稼働ステータス(稼働中/要注意/異常)を表示。
    ステータス色はget_status_info()で判定され、CSS classで制御。

    Args:
        data: 生産データ (remain_min, in_operating, alarmを使用)
        progress: 進捗率 (0.0-1.0, ステータス判定に使用)

    Note:
        ステータス判定:
        - alarm=True → 異常 (赤)
        - progress>=1.0 → 目標進捗 (緑)
        - progress>=0.8 → 要注意 (黄)
        - progress<0.8 → 稼働中 (緑)
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

    status_class, status_text = get_status_info(data.alarm, progress, data.in_operating)
    st.markdown(
        f"<div class='{status_class}' style='text-align: center; margin-top: 1rem;'>{status_text}</div>",
        unsafe_allow_html=True,
    )


def render_alarm_bar(data: ProductionData) -> None:
    """アラームバーをレンダリング

    画面最下部に配置される全幅のステータスバー。
    アラーム発生時は赤色グラデーション+メッセージ表示、
    正常時は緑色で「正常」表示。

    Args:
        data: 生産データ (alarm, alarm_msgを使用)

    Note:
        アラーム時はアニメーション効果付きで視認性を高める。
        CSSはget_page_styles()で定義されたalarm-barクラスを使用。
    """
    if data.alarm:
        if False:
            st.markdown(
                f"<div class='alarm-bar'>【異常】{data.alarm_msg}</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div class='alarm-bar' style='background:#7f1d1d;'>異常発生中、装置を確認してください。</div>",
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            "<div class='alarm-bar' style='background:#145c32;'>現在、異常はありません。</div>",
            unsafe_allow_html=True,
        )
