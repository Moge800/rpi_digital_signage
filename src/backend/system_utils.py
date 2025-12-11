import os
import platform
import subprocess
from datetime import datetime
from backend.logging import backend_logger as logger


def is_raspberry_pi() -> bool:
    """Raspberry Pi上で動作しているかを判定する

    Returns:
        bool: Raspberry Pi上であればTrue、そうでなければFalse
    """
    try:
        with open("/proc/device-tree/model", "r") as f:
            model = f.read().lower()
            return "raspberry pi" in model
    except FileNotFoundError:
        return False


def is_windows() -> bool:
    """Windows上で動作しているかを判定する

    Returns:
        bool: Windows上であればTrue、そうでなければFalse
    """
    return os.name == "nt"


def is_linux() -> bool:
    """Linux上で動作しているかを判定する

    Returns:
        bool: Linux上であればTrue、そうでなければFalse
    """
    return os.name == "posix" and not is_raspberry_pi()


def is_mac() -> bool:
    """macOS上で動作しているかを判定する

    Returns:
        bool: macOS上であればTrue、そうでなければFalse
    """
    return platform.system() == "Darwin"


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
        if is_windows():  # Windows
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


def restart_system() -> bool:
    """システムを再起動する

    Returns:
        bool: 再起動コマンドの実行に成功した場合True、失敗した場合False

    Raises:
        OSError: システムコマンド実行に失敗した場合
        PermissionError: 権限不足の場合
    """
    try:
        if is_windows():  # Windows
            subprocess.run(
                ["shutdown", "/r", "/t", "0"],
                check=True,
                capture_output=True,
            )
        else:  # Unix/Linux (Raspberry Pi)
            # sudoersでNOPASSWD設定が必要: pi ALL=(ALL) NOPASSWD: /sbin/reboot
            subprocess.run(
                ["sudo", "reboot"],
                check=True,
                capture_output=True,
                text=True,
            )

        logger.info("System restart command executed.")
        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to restart system (command failed): {e.stderr}")
        return False
    except PermissionError as e:
        logger.error(f"Failed to restart system (permission denied): {e}")
        return False
    except OSError as e:
        logger.error(f"Failed to restart system (OS error): {e}")
        return False
