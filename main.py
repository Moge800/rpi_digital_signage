#!/usr/bin/env python3
"""デジタルサイネージ統合ランチャー

FastAPI (バックエンド) + Streamlit (フロントエンド) + Kioskブラウザを起動。
環境変数KIOSK_MODE=trueでフルスクリーンブラウザを自動起動。

使い方:
    python main.py              # 通常モード（APIを直接起動）
    python main.py --watchdog   # Watchdogモード（推奨: API監視付き）
    または
    uv run python main.py --watchdog
"""

import argparse
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
        # stdout/stderrをPIPEにするとバッファが詰まる可能性があるためNoneに
        stdout=None,
        stderr=None,
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
        # stdout/stderrをPIPEにするとバッファが詰まる可能性があるためNoneに
        stdout=None,
        stderr=None,
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

    # コマンドライン引数パース
    parser = argparse.ArgumentParser(description="デジタルサイネージ起動スクリプト")
    parser.add_argument(
        "--watchdog",
        action="store_true",
        help="Watchdogモードで起動（API監視付き、推奨）",
    )
    args = parser.parse_args()

    print("=" * 50)
    print("デジタルサイネージ起動スクリプト")
    if args.watchdog:
        print("(Watchdogモード: API監視付き)")
    else:
        print("(FastAPI + Streamlit 構成)")
    print("=" * 50)
    print()

    # Watchdogモードの場合は、APIをWatchdogに委譲
    if args.watchdog:
        _run_watchdog_mode(logger)
    else:
        _run_normal_mode(logger)


def _run_watchdog_mode(logger: Logger) -> None:
    """Watchdogモードで起動

    APIサーバーはWatchdogが管理・監視・再起動を担当。
    フロントエンドとブラウザは直接管理。
    """
    from src.backend.config_helpers import get_kiosk_mode

    # 初期化フラグをクリア
    clear_init_flags()

    # Watchdogプロセス
    watchdog_process: Optional[subprocess.Popen] = None
    streamlit_process: Optional[subprocess.Popen] = None
    browser_process: Optional[subprocess.Popen] = None

    def cleanup() -> None:
        """クリーンアップ"""
        nonlocal watchdog_process, streamlit_process, browser_process
        logger.info("シャットダウン中...")

        # ブラウザ停止
        if browser_process and browser_process.poll() is None:
            browser_process.terminate()
            try:
                browser_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                browser_process.kill()

        # Streamlit停止
        if streamlit_process and streamlit_process.poll() is None:
            streamlit_process.terminate()
            try:
                streamlit_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                streamlit_process.kill()

        # Watchdog停止（これによりAPIも停止）
        if watchdog_process and watchdog_process.poll() is None:
            watchdog_process.terminate()
            try:
                watchdog_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                watchdog_process.kill()

        logger.info("シャットダウン完了")

    def signal_handler(signum: int, frame: object) -> None:
        cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    atexit.register(cleanup)

    try:
        # 1. Watchdog起動（APIサーバーを内部で管理）
        logger.info("Watchdogを起動中...")
        watchdog_process = subprocess.Popen(
            [sys.executable, "scripts/watchdog.py"],
            # stdout/stderrをPIPEにするとバッファが詰まる可能性があるためNoneに
            stdout=None,
            stderr=None,
        )
        logger.info(f"✓ Watchdog起動 (PID: {watchdog_process.pid})")

        # Watchdogが起動してAPIを起動するのを待つ
        if not wait_for_api_ready(logger):
            logger.error("APIサーバーの起動に失敗しました")
            cleanup()
            sys.exit(1)

        # 2. Streamlit起動
        streamlit_process = start_streamlit(logger)

        # 3. Kioskモード時はブラウザも起動
        kiosk_mode = get_kiosk_mode()
        if kiosk_mode:
            logger.info("Kioskモード: 有効")
            browser_process = start_kiosk_browser(logger)
        else:
            logger.info("Kioskモード: 無効")

        print()
        print("=" * 50)
        print("起動完了! (Watchdogモード)")
        print("=" * 50)
        print()
        print(f"  API:       http://{API_HOST}:{API_PORT}")
        print(f"  Frontend:  http://localhost:{STREAMLIT_PORT}")
        print(f"  Watchdog:  有効 (PID: {watchdog_process.pid})")
        print()
        print("Ctrl+C で終了")
        print()

        # プロセス監視ループ
        while True:
            # Watchdogプロセスチェック
            if watchdog_process.poll() is not None:
                logger.error("Watchdogが予期せず停止しました")
                break

            # Streamlitプロセスチェック
            if streamlit_process and streamlit_process.poll() is not None:
                logger.error("Streamlitが予期せず停止しました")
                break

            time.sleep(2)

    except KeyboardInterrupt:
        logger.info("ユーザーによる停止")

    finally:
        cleanup()
        sys.exit(0)


def _run_normal_mode(logger: Logger) -> None:
    """通常モードで起動（従来の動作）"""
    from src.backend.config_helpers import get_kiosk_mode

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
