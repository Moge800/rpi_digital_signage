"""frontend.stylesのテスト"""

from frontend.styles import get_theme_colors


class TestGetThemeColors:
    """get_theme_colors関数のテスト"""

    def test_dark_theme_returns_dict(self):
        """ダークテーマで辞書を返す"""
        colors = get_theme_colors(theme="dark")

        assert isinstance(colors, dict)

    def test_light_theme_returns_dict(self):
        """ライトテーマで辞書を返す"""
        colors = get_theme_colors(theme="light")

        assert isinstance(colors, dict)

    def test_default_is_dark_theme(self):
        """引数なしの場合はダークテーマ"""
        colors = get_theme_colors()

        # ダークテーマの特徴的な色をチェック
        assert colors["bg_color"] == "#000000"
        assert colors["text_color"] == "#f5f5f5"

    def test_dark_theme_has_required_keys(self):
        """ダークテーマが必須キーを持つ"""
        colors = get_theme_colors(theme="dark")

        required_keys = [
            "bg_color",
            "text_color",
            "text_secondary",
            "header_color",
            "gauge_bg",
            "gauge_bar",
            "gauge_step_1",
            "gauge_step_2",
            "status_ok_bg",
            "status_ok_border",
            "status_warn_bg",
            "status_warn_border",
            "status_alarm_bg",
            "status_alarm_border",
        ]

        for key in required_keys:
            assert key in colors, f"Missing required key: {key}"

    def test_light_theme_has_required_keys(self):
        """ライトテーマが必須キーを持つ"""
        colors = get_theme_colors(theme="light")

        required_keys = [
            "bg_color",
            "text_color",
            "gauge_bg",
            "gauge_bar",
            "gauge_step_1",
            "gauge_step_2",
        ]

        for key in required_keys:
            assert key in colors, f"Missing required key: {key}"

    def test_dark_theme_colors_are_strings(self):
        """ダークテーマの色値がすべて文字列"""
        colors = get_theme_colors(theme="dark")

        for key, value in colors.items():
            assert isinstance(value, str), f"{key} should be string"

    def test_light_theme_colors_are_strings(self):
        """ライトテーマの色値がすべて文字列"""
        colors = get_theme_colors(theme="light")

        for key, value in colors.items():
            assert isinstance(value, str), f"{key} should be string"

    def test_dark_theme_bg_is_dark(self):
        """ダークテーマの背景色は暗い色"""
        colors = get_theme_colors(theme="dark")

        assert colors["bg_color"] == "#000000"

    def test_light_theme_bg_is_light(self):
        """ライトテーマの背景色は明るい色"""
        colors = get_theme_colors(theme="light")

        assert colors["bg_color"] == "#ffffff"

    def test_both_themes_have_same_keys(self):
        """両テーマが同じキーセットを持つ"""
        dark_colors = get_theme_colors(theme="dark")
        light_colors = get_theme_colors(theme="light")

        assert set(dark_colors.keys()) == set(light_colors.keys())

    def test_gauge_bar_color_is_consistent(self):
        """ゲージバー色は両テーマで同じ（緑系）"""
        dark_colors = get_theme_colors(theme="dark")
        light_colors = get_theme_colors(theme="light")

        # 両方とも #31c77f (緑色)
        assert dark_colors["gauge_bar"] == light_colors["gauge_bar"]
        assert dark_colors["gauge_bar"] == "#31c77f"
