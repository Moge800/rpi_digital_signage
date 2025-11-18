"""frontend.componentsのテスト"""

from frontend.components import get_status_info


class TestGetStatusInfo:
    """get_status_info関数のテスト"""

    def test_status_alarm_when_alarm_true(self):
        """異常フラグがTrueの時はalarmステータス"""
        css_class, status_text = get_status_info(alarm=True, progress=0.5)

        assert css_class == "status-alarm"
        assert status_text == "⚠ 異常発生"

    def test_status_ok_when_progress_100_percent(self):
        """進捗率100%以上の時はOKステータス"""
        css_class, status_text = get_status_info(alarm=False, progress=1.0)

        assert css_class == "status-ok"
        assert status_text == "✅ 目標進捗"

    def test_status_ok_when_progress_over_100_percent(self):
        """進捗率100%超の時もOKステータス"""
        css_class, status_text = get_status_info(alarm=False, progress=1.2)

        assert css_class == "status-ok"
        assert status_text == "✅ 目標進捗"

    def test_status_warn_when_progress_80_to_99_percent(self):
        """進捗率80-99%の時は警告ステータス"""
        css_class, status_text = get_status_info(alarm=False, progress=0.8)

        assert css_class == "status-warn"
        assert status_text == "▲ 要注意"

    def test_status_warn_at_90_percent(self):
        """進捗率90%でも警告ステータス"""
        css_class, status_text = get_status_info(alarm=False, progress=0.9)

        assert css_class == "status-warn"
        assert status_text == "▲ 要注意"

    def test_status_ok_when_progress_below_80_percent(self):
        """進捗率80%未満の時は稼働中ステータス"""
        css_class, status_text = get_status_info(alarm=False, progress=0.5)

        assert css_class == "status-ok"
        assert status_text == "● 稼働中"

    def test_status_ok_when_progress_zero(self):
        """進捗率0%でも稼働中ステータス"""
        css_class, status_text = get_status_info(alarm=False, progress=0.0)

        assert css_class == "status-ok"
        assert status_text == "● 稼働中"

    def test_alarm_takes_priority_over_progress(self):
        """異常フラグは進捗率より優先される"""
        # 進捗100%でもアラームがあれば異常扱い
        css_class, status_text = get_status_info(alarm=True, progress=1.0)

        assert css_class == "status-alarm"
        assert status_text == "⚠ 異常発生"
