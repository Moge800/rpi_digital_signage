"""生産データ計算ロジック

残りパレット数、残り時間などの計算を行う関数群。
機種設定(ProductionTypeConfig)を使用して計算を実行。
"""

from backend.config_helpers import get_config_data


def calculate_remain_pallet(
    plan: int, actual: int, production_type: int, decimals: int | None = 2
) -> float:
    """残りパレット数を計算する

    Args:
        plan: 計画生産数
        actual: 実績生産数
        production_type: 機種番号 (0-15)
        decimals: 小数点以下の桁数 (Noneの場合は丸めない)

    Returns:
        float: 残りパレット数

    Examples:
        >>> calculate_remain_pallet(plan=30000, actual=20000, production_type=1)
        3.57
    """
    config = get_config_data(production_type)

    remaining_units = max(0, plan - actual)
    remain_pallet = remaining_units / config.fully

    return round(remain_pallet, decimals) if decimals is not None else remain_pallet


def calculate_remain_minutes(
    plan: int, actual: int, production_type: int, decimals: int | None = 2
) -> float:
    """残り時間(分)を計算

    Args:
        plan: 計画数
        actual: 実績数
        production_type: 機種番号
        decimals: 小数点以下の桁数 (Noneの場合は丸めない)

    Returns:
        float: 残り時間(分)

    Examples:
        >>> calculate_remain_minutes(plan=30000, actual=20000, production_type=1)
        200.0
    """
    config = get_config_data(production_type)

    remain = plan - actual
    remain_seconds = remain * config.seconds_per_product  # 残り個数 × 1個あたりの秒数
    remain_minute = remain_seconds / 60.0

    return round(remain_minute, decimals) if decimals is not None else remain_minute
