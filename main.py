import subprocess
import sys
import time
from typing import Optional


def start_streamlit() -> subprocess.Popen:
    """Streamlitサーバーをバックグラウンドで起動

    Returns:
        subprocess.Popen: Streamlitプロセス
    """
    from src.backend.logging import launcher_logger

    launcher_logger.info("Starting Streamlit server...")
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "src/frontend/signage_app.py",
            "--server.headless",
            "true",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Streamlitの起動を待つ
    launcher_logger.info("Waiting for Streamlit to start...")
    time.sleep(3)

    return process


def start_kiosk_browser(
    url: str = "http://localhost:8501",
) -> Optional[subprocess.Popen]:
    """Kioskモードでブラウザを起動

    Args:
        url: 表示するURL

    Returns:
        subprocess.Popen: ブラウザプロセス (起動失敗時はNone)
    """
    from src.backend.logging import launcher_logger

    launcher_logger.info(f"Starting Kiosk mode browser: {url}")

    # Chromiumコマンドの候補
    chromium_commands = [
        "chromium-browser",  # Raspberry Pi
        "chromium",  # Ubuntu
        "google-chrome",  # Chrome
    ]

    kiosk_args = [
        "--kiosk",  # Kioskモード
        "--noerrdialogs",  # エラーダイアログ非表示
        "--disable-infobars",  # 情報バー非表示
        "--no-first-run",  # 初回起動画面スキップ
        "--check-for-update-interval=31536000",  # 更新チェック無効化
        "--disable-translate",  # 翻訳機能無効化
        url,
    ]

    for cmd in chromium_commands:
        try:
            process = subprocess.Popen([cmd] + kiosk_args)
            launcher_logger.info(f"Kiosk browser started with: {cmd}")
            return process
        except FileNotFoundError:
            continue

    launcher_logger.warning("Chromium not found. Please install chromium-browser.")
    launcher_logger.info(f"Opening default browser: {url}")
    return None


def main() -> None:
    """Streamlitアプリケーションを起動する"""
    from src.backend.logging import launcher_logger
    from src.backend.utils import get_kiosk_mode

    # メイン処理
    kiosk_mode = get_kiosk_mode()
    streamlit_process: Optional[subprocess.Popen] = None
    browser_process: Optional[subprocess.Popen] = None

    try:
        # Kioskモード判定 .envにて設定
        if kiosk_mode:
            launcher_logger.info("Kiosk mode enabled")

            # Streamlitをバックグラウンドで起動
            streamlit_process = start_streamlit()

            # Kioskモードでブラウザ起動
            browser_process = start_kiosk_browser()

            # プロセスが終了するまで待機
            if streamlit_process:
                streamlit_process.wait()
        else:
            launcher_logger.info("Normal mode (Kiosk mode disabled)")

            # 通常モード: Streamlitが自動でブラウザを開く
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "streamlit",
                    "run",
                    "src/frontend/signage_app.py",
                ],
                check=True,
            )

    except subprocess.CalledProcessError as e:
        launcher_logger.error(f"Error running Streamlit: {e}")
        sys.exit(1)

    except KeyboardInterrupt:
        launcher_logger.info("Streamlit stopped by user")

    finally:
        # クリーンアップ
        if streamlit_process:
            launcher_logger.info("Stopping Streamlit server...")
            streamlit_process.terminate()
            streamlit_process.wait()

        if browser_process:
            launcher_logger.info("Stopping Kiosk browser...")
            browser_process.terminate()
            browser_process.wait()

        sys.exit(0)


if __name__ == "__main__":
    main()
