import os
import subprocess
from datetime import datetime
from backend.logging import backend_logger as logger


def set_system_clock(target_time: datetime) -> bool:
    """システム時計を設定する

    Note:
        - Windows: 管理者権限が必要
        - Linux: sudoersでNOPASSWD設定が必要 (Raspberry Pi推奨)
        - 本番環境では慎重に使用すること

    Args:
        target_time: 設定する日時

    Returns:
        bool: 成功した場合True、失敗した場合False

    Raises:
        OSError: システムコマンド実行に失敗した場合
        PermissionError: 権限不足の場合
    """
    try:
        if os.name == "nt":  # Windows
            subprocess.run(
                ["date", target_time.strftime("%Y-%m-%d")],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["time", target_time.strftime("%H:%M:%S")],
                check=True,
                capture_output=True,
            )
        else:  # Unix/Linux (Raspberry Pi)
            # フォーマット: MMDDhhmmYYYY.SS
            time_str = target_time.strftime("%m%d%H%M%Y.%S")
            # sudoersでNOPASSWD設定が必要: pi ALL=(ALL) NOPASSWD: /bin/date
            subprocess.run(
                ["sudo", "date", time_str],
                check=True,
                capture_output=True,
                text=True,
            )

        logger.info(f"System clock set to {target_time.strftime('%Y-%m-%d %H:%M:%S')}")
        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to set system clock (command failed): {e.stderr}")
        return False
    except PermissionError as e:
        logger.error(f"Failed to set system clock (permission denied): {e}")
        return False
    except OSError as e:
        logger.error(f"Failed to set system clock (OS error): {e}")
        return False
