"""フロントエンドスタイル管理

ページ全体のCSSスタイルとテーマ設定を管理する。
ライトモード/ダークモードの切り替えに対応。
"""


def get_theme_colors(theme: str = "dark") -> dict[str, str]:
    """テーマに応じた色設定を取得

    Args:
        theme: "dark" または "light"

    Returns:
        dict[str, str]: 色設定辞書
    """
    if theme == "light":
        return {
            "bg_color": "#ffffff",
            "text_color": "#000000",
            "text_secondary": "#555555",
            "header_color": "#1a1a1a",
            "kpi_label_color": "#666666",
            "kpi_value_color": "#000000",
            "kpi_sub_color": "#333333",
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
            "alarm_bar_ok_bg": "#81c784",
            "alarm_bar_error_bg": "linear-gradient(90deg, #ff5252, #ff9800)",
            "hr_color": "#e0e0e0",
            "progress_color": "#31c77f",
        }
    else:  # dark (デフォルト)
        return {
            "bg_color": "#000000",
            "text_color": "#f5f5f5",
            "text_secondary": "#d0d0d0",
            "header_color": "#ffffff",
            "kpi_label_color": "#bbbbbb",
            "kpi_value_color": "#ffffff",
            "kpi_sub_color": "#cccccc",
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
            "alarm_bar_ok_bg": "#145c32",
            "alarm_bar_error_bg": "linear-gradient(90deg, #ff0000, #ff8800)",
            "hr_color": "#333333",
            "progress_color": "#31c77f",
        }


def get_page_styles(theme: str = "dark") -> str:
    """ページ全体のカスタムCSSスタイルを取得 (テーマ対応)

    Streamlitのデフォルトスタイルを上書きし、
    デジタルサイネージ用の表示を実現する。

    Args:
        theme: "dark" または "light"

    Returns:
        str: HTML <style>タグを含むCSS文字列
    """
    colors = get_theme_colors(theme)

    return f"""
    <style>
    /* Streamlitのヘッダーを非表示 */
    header {{
        visibility: hidden;
    }}
    /* Streamlitのメニューボタンを非表示 */
    #MainMenu {{
        visibility: hidden;
    }}
    /* Streamlitのフッターを非表示 */
    footer {{
        visibility: hidden;
    }}
    /* 全体を背景色に */
    .stApp {{
        background-color: {colors["bg_color"]};
    }}
    /* 上部の余白を確保 */
    .main > div {{
        padding-top: 2rem;
    }}
    body {{
        background-color: {colors["bg_color"]};
        color: {colors["text_color"]};
    }}
    .block-container {{
        padding-top: 0.8rem;
        padding-bottom: 0.2rem;
        max-width: 95%;
        background-color: {colors["bg_color"]};
    }}
    .header-title {{
        font-size: 3.0rem;
        font-weight: 700;
        padding: 0.1rem 0;
        color: {colors["header_color"]};
    }}
    .header-time {{
        font-size: 3.0rem;
        text-align: right;
        color: {colors["text_secondary"]};
    }}
    .kpi-label {{
        font-size: 1.1rem;
        color: {colors["kpi_label_color"]};
    }}
    .kpi-value-big {{
        font-size: 4.2rem;
        font-weight: 800;
        color: {colors["kpi_value_color"]};
    }}
    .kpi-sub {{
        font-size: 1.4rem;
        color: {colors["kpi_sub_color"]};
    }}
    .kpi-value-norm {{
        font-size: 3.2rem;
        font-weight: 800;
        color: {colors["kpi_value_color"]};
    }}
    .status-ok {{
        font-size: 1.6rem;
        background: {colors["status_ok_bg"]};
        padding: 0.6rem;
        border-radius: 0.5rem;
        border: 1px solid {colors["status_ok_border"]};
        color: {colors["text_color"]};
        font-weight: 600;
    }}
    .status-warn {{
        font-size: 1.6rem;
        background: {colors["status_warn_bg"]};
        padding: 0.6rem;
        border-radius: 0.5rem;
        border: 1px solid {colors["status_warn_border"]};
        color: {colors["text_color"]};
        font-weight: 600;
    }}
    .status-alarm {{
        font-size: 1.6rem;
        background: {colors["status_alarm_bg"]};
        padding: 0.6rem;
        border-radius: 0.5rem;
        border: 1px solid {colors["status_alarm_border"]};
        color: {colors["text_color"]};
        font-weight: 600;
    }}
    .status-unknown {{
        font-size: 1.6rem;
        background: #555555;
        padding: 0.6rem;
        border-radius: 0.5rem;
        border: 1px solid #777777;
        color: {colors["text_color"]};
        font-weight: 600;
    }}
    .alarm-bar {{
        background: {colors["alarm_bar_error_bg"]};
        color: white;
        font-size: 2.2rem;
        font-weight: 700;
        padding: 0.3rem 0.8rem;
        border-radius: 0.4rem;
        text-align: left;
    }}
    .footer {{
        font-size: 0.7rem;
        color: #888888;
        text-align: right;
        padding-top: 0.2rem;
    }}
    /* プログレスバーのスタイル調整 */
    .stProgress > div > div > div > div {{
        background-color: {colors["progress_color"]};
    }}
    /* 区切り線を見やすく */
    hr {{
        border-color: {colors["hr_color"]};
    }}
    </style>
"""
