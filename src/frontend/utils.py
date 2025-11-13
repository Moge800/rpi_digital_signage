"""フロントエンドユーティリティ関数

画面表示に関する汎用的なヘルパー関数を提供する。
"""


def format_time_hhmm(minutes: int) -> str:
    """分を「HH時間MM分」形式にフォーマット

    Args:
        minutes: 分数

    Returns:
        str: フォーマットされた時間文字列

    Examples:
        >>> format_time_hhmm(125)
        '02時間05分'
        >>> format_time_hhmm(45)
        '00時間45分'
        >>> format_time_hhmm(0)
        '00時間00分'
    """
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}時間{mins:02d}分"
