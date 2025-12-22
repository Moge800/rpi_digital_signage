#!/usr/bin/env python3
"""デジタルサイネージ統合ランチャー

FastAPI (バックエンド) + Streamlit (フロントエンド) + Kioskブラウザを起動。
環境変数KIOSK_MODE=trueでフルスクリーンブラウザを自動起動。

使い方:
    python main.py
    または
    uv run python main.py
"""

import atexit
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional
from logging import Logger

import httpx

# プロジェクトルートをPythonパスに追加（インポートパス解決のため）
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))


# --------------------------
#  設定
# --------------------------
API_HOST = "127.0.0.1"
API_PORT = 8000
STREAMLIT_PORT = 8501
API_STARTUP_TIMEOUT = 30  # 秒
STREAMLIT_STARTUP_DELAY = 3  # 秒

# 初期化フラグファイル
INIT_FLAG_FILE = Path(tempfile.gettempdir()) / "signage_initialized.flag"
FRONTEND_INIT_FLAG_FILE = (
    Path(tempfile.gettempdir()) / "signage_frontend_initialized.flag"
)


# --------------------------
#  プロセス管理
# --------------------------
class ProcessManager:
    """複数プロセスのライフサイクルを管理"""

    def __init__(self, logger: Logger) -> None:
        self.logger = logger
        self.api_process: Optional[subprocess.Popen] = None
        self.streamlit_process: Optional[subprocess.Popen] = None
        self.browser_process: Optional[subprocess.Popen] = None

    def cleanup(self) -> None:
        """全プロセスを安全に停止"""
        self.logger.info("シャットダウン中...")

        # ブラウザ停止
        self._stop_process(self.browser_process, "Kioskブラウザ")

        # Streamlit停止
        self._stop_process(self.streamlit_process, "Streamlit")

        # API停止（シャットダウンエンドポイント経由）
        if self.api_process and self.api_process.poll() is None:
            self.logger.info("APIサーバーを停止中...")
            try:
                httpx.post(
                    f"http://{API_HOST}:{API_PORT}/api/shutdown",
                    timeout=3.0,
                )
                time.sleep(1)
            except Exception:
                pass

            self._stop_process(self.api_process, "APIサーバー")

        self.logger.info("シャットダウン完了")

    def _stop_process(self, process: Optional[subprocess.Popen], name: str) -> None:
        """プロセスを安全に終了"""
        if process and process.poll() is None:
            self.logger.info(f"{name}を停止中...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.logger.warning(f"{name}の停止がタイムアウト、強制終了します")
                process.kill()
                process.wait()


def clear_init_flags() -> None:
    """初期化フラグをクリア（再起動時に初期化を実行するため）"""
    INIT_FLAG_FILE.unlink(missing_ok=True)
    FRONTEND_INIT_FLAG_FILE.unlink(missing_ok=True)


def start_api_server(logger: Logger) -> subprocess.Popen:
    """FastAPI サーバーを起動

    Returns:
        subprocess.Popen: APIサーバープロセス
    """
    logger.info(f"APIサーバーを起動中... ({API_HOST}:{API_PORT})")

    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "src.api.main:app",
            "--host",
            API_HOST,
            "--port",
            str(API_PORT),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    return process


def wait_for_api_ready(logger: Logger) -> bool:
    """APIサーバーの起動を待機

    Returns:
        bool: 起動成功ならTrue
    """
    logger.info("APIサーバーの起動を待機中...")

    for i in range(API_STARTUP_TIMEOUT):
        try:
            response = httpx.get(
                f"http://{API_HOST}:{API_PORT}/health",
                timeout=2.0,
            )
            if response.status_code == 200:
                logger.info("✓ APIサーバー正常起動")
                return True
        except Exception:
            pass
        time.sleep(1)

    logger.error("APIサーバーの起動がタイムアウトしました")
    return False


def start_streamlit(logger: Logger) -> subprocess.Popen:
    """Streamlit サーバーを起動

    Returns:
        subprocess.Popen: Streamlitプロセス
    """
    logger.info(f"Streamlitを起動中... (port {STREAMLIT_PORT})")

    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "src/frontend/signage_app.py",
            "--server.port",
            str(STREAMLIT_PORT),
            "--server.headless",
            "true",
            "--server.address",
            "0.0.0.0",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    # Streamlitの起動を待つ
    time.sleep(STREAMLIT_STARTUP_DELAY)
    logger.info(f"✓ Streamlit起動 (PID: {process.pid})")

    return process


def start_kiosk_browser(
    logger: Logger,
    url: str = f"http://localhost:{STREAMLIT_PORT}",
) -> Optional[subprocess.Popen]:
    """Kioskモードでブラウザを起動

    Args:
        logger: ロガーインスタンス
        url: 表示するURL

    Returns:
        subprocess.Popen: ブラウザプロセス (起動失敗時はNone)
    """
    logger.info(f"Kioskモードでブラウザを起動中: {url}")

    # Chromiumコマンドの候補
    chromium_commands = [
        "chromium-browser",  # Raspberry Pi
        "chromium",  # Ubuntu
        "google-chrome",  # Chrome
    ]

    kiosk_args = [
        "--kiosk",  # Kioskモード（フルスクリーン）
        "--noerrdialogs",  # エラーダイアログ非表示
        "--disable-infobars",  # 情報バー非表示
        "--no-first-run",  # 初回起動画面スキップ
        "--check-for-update-interval=31536000",  # 更新チェック無効化
        "--disable-translate",  # 翻訳機能無効化
        "--disable-features=TranslateUI",  # 翻訳UI無効化
        "--autoplay-policy=no-user-gesture-required",  # 自動再生許可
        url,
    ]

    for cmd in chromium_commands:
        try:
            process = subprocess.Popen(
                [cmd] + kiosk_args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            logger.info(f"✓ Kioskブラウザ起動: {cmd} (PID: {process.pid})")
            return process
        except FileNotFoundError:
            continue

    logger.warning(
        "Chromiumが見つかりません。chromium-browserをインストールしてください。"
    )
    logger.info(f"手動でブラウザを開いてください: {url}")
    return None


def main() -> None:
    """メインエントリーポイント"""
    from src.backend.logging import launcher_logger as logger
    from src.backend.config_helpers import get_kiosk_mode

    print("=" * 50)
    print("デジタルサイネージ起動スクリプト")
    print("(FastAPI + Streamlit 構成)")
    print("=" * 50)
    print()

    # 初期化フラグをクリア
    clear_init_flags()

    # プロセスマネージャー
    manager = ProcessManager(logger)

    # シグナルハンドラとatexit登録
    def signal_handler(signum: int, frame: object) -> None:
        manager.cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    atexit.register(manager.cleanup)

    try:
        # 1. APIサーバー起動
        manager.api_process = start_api_server(logger)

        if not wait_for_api_ready(logger):
            logger.error("APIサーバーの起動に失敗しました")
            manager.cleanup()
            sys.exit(1)

        # 2. Streamlit起動
        manager.streamlit_process = start_streamlit(logger)

        # 3. Kioskモード時はブラウザも起動
        kiosk_mode = get_kiosk_mode()
        if kiosk_mode:
            logger.info("Kioskモード: 有効")
            manager.browser_process = start_kiosk_browser(logger)
        else:
            logger.info("Kioskモード: 無効")

        print()
        print("=" * 50)
        print("起動完了!")
        print("=" * 50)
        print()
        print(f"  API:       http://{API_HOST}:{API_PORT}")
        print(f"  Frontend:  http://localhost:{STREAMLIT_PORT}")
        print()
        print("Ctrl+C で終了")
        print()

        # プロセス監視ループ
        while True:
            # APIプロセスチェック
            if manager.api_process and manager.api_process.poll() is not None:
                logger.error("APIサーバーが予期せず停止しました")
                break

            # Streamlitプロセスチェック
            if (
                manager.streamlit_process
                and manager.streamlit_process.poll() is not None
            ):
                logger.error("Streamlitが予期せず停止しました")
                break

            time.sleep(2)

    except KeyboardInterrupt:
        logger.info("ユーザーによる停止")

    finally:
        manager.cleanup()
        sys.exit(0)


if __name__ == "__main__":
    main()
