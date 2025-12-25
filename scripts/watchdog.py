#!/usr/bin/env python3
"""API Watchdog プロセス

バックエンドAPIサーバーを監視し、応答がない場合に再起動する。

機能:
- 一定間隔 (デフォルト10秒) で /health エンドポイントを監視
- 連続失敗回数 (デフォルト3回) でバックエンドを再起動
- 段階的バックオフで再起動間隔を増加 (60秒 → 5分 → 15分 → 30分)
- プロセスグループ管理で子プロセスも確実に終了

使用方法:
    python scripts/watchdog.py

環境変数 (.env):
    WATCHDOG_INTERVAL: ヘルスチェック間隔 (秒)
    WATCHDOG_FAILURE_LIMIT: 再起動までの失敗回数
    WATCHDOG_RESTART_COOLDOWN: 再起動クールダウン初期値 (秒)
    WATCHDOG_STARTUP_GRACE: 起動後の猶予時間 (秒)
    WATCHDOG_BACKOFF_MAX: バックオフ最大値 (秒)
"""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import httpx

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))
os.chdir(project_root)

from dotenv import load_dotenv

load_dotenv()

from config.settings import WatchdogSettings
from backend.logging import launcher_logger as logger


class APIWatchdog:
    """API Watchdog

    バックエンドAPIを監視し、必要に応じて再起動する。

    設計方針:
    - stdout/stderr は親プロセスに継承（PIPE使用しない）
    - プロセスグループ管理で子プロセスも確実に終了
    - httpx.Client は使い回し
    - 段階的バックオフで再起動間隔を増加
    """

    def __init__(self) -> None:
        """Watchdogを初期化"""
        self._settings = WatchdogSettings()

        # Watchdog設定
        self._check_interval = self._settings.WATCHDOG_INTERVAL
        self._failure_limit = self._settings.WATCHDOG_FAILURE_LIMIT
        self._initial_cooldown = self._settings.WATCHDOG_RESTART_COOLDOWN
        self._startup_grace = self._settings.WATCHDOG_STARTUP_GRACE
        self._backoff_max = self._settings.WATCHDOG_BACKOFF_MAX
        self._api_startup_timeout = self._settings.WATCHDOG_API_STARTUP_TIMEOUT
        self._api_startup_check_interval = (
            self._settings.WATCHDOG_API_STARTUP_CHECK_INTERVAL
        )

        # API接続情報
        self._api_host = self._settings.API_HOST
        self._api_port = self._settings.API_PORT
        self._health_url = f"http://{self._api_host}:{self._api_port}/health"

        # 状態管理
        self._consecutive_failures = 0
        self._last_success_monotonic: float | None = (
            None  # 最後に成功した時刻 (monotonic)
        )
        self._last_restart_monotonic: float | None = (
            None  # 最後に再起動した時刻 (monotonic)
        )
        self._restart_count = 0  # 連続再起動回数（成功でリセット）
        self._last_api_pid: int | None = None  # /healthから取得したPID（ワーカーPID等）
        self._popen_pid: int | None = None  # Popenで起動したPID（親プロセス）
        self._api_process: Optional[subprocess.Popen[bytes]] = None
        self._running = True

        # httpx.Client を使い回す
        self._http_client: Optional[httpx.Client] = None

        logger.info(
            f"Watchdog initialized (interval={self._check_interval}s, "
            f"failure_limit={self._failure_limit}, "
            f"initial_cooldown={self._initial_cooldown}s, "
            f"backoff_max={self._backoff_max}s, "
            f"api_startup_timeout={self._api_startup_timeout}s)"
        )

    def _get_http_client(self) -> httpx.Client:
        """HTTPクライアントを取得（使い回し）"""
        if self._http_client is None:
            self._http_client = httpx.Client(timeout=2.0)
        return self._http_client

    def _close_http_client(self) -> None:
        """HTTPクライアントを閉じる"""
        if self._http_client is not None:
            try:
                self._http_client.close()
            except Exception:
                pass
            self._http_client = None

    def _get_current_cooldown(self) -> float:
        """現在のクールダウン時間を計算（段階的バックオフ）

        Returns:
            float: クールダウン秒数 (initial_cooldown → 5分 → 15分 → 30分)
        """
        # 段階的バックオフ: initial_cooldown → 5分 → 15分 → 30分
        # .env の WATCHDOG_RESTART_COOLDOWN が先頭になる
        backoff_stages = [self._initial_cooldown, 300, 900, 1800]
        stage = min(self._restart_count, len(backoff_stages) - 1)
        cooldown = backoff_stages[stage]
        return min(cooldown, self._backoff_max)

    def start(self) -> None:
        """Watchdogを開始"""
        # シグナルハンドラ設定
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

        logger.info("Watchdog starting...")

        # 初回起動
        if not self._start_api_server():
            logger.error("Initial API server startup failed")
            self._running = False
            return

        # 監視ループ
        while self._running:
            time.sleep(self._check_interval)
            if self._running:  # シャットダウン中でなければチェック
                self._check_health()

        # クリーンアップ
        self._close_http_client()
        logger.info("Watchdog stopped")

    def _handle_signal(self, signum: int, frame: object) -> None:
        """シグナル受信時のハンドラ"""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        self._running = False
        self._stop_api_server()
        self._close_http_client()

    def _check_health(self) -> None:
        """ヘルスチェックを実行"""
        try:
            client = self._get_http_client()
            response = client.get(self._health_url)
            if response.status_code == 200:
                # 成功: 失敗カウンタと再起動カウンタをリセット
                self._consecutive_failures = 0
                self._last_success_monotonic = time.monotonic()
                self._restart_count = 0  # 安定動作中なのでリセット

                # PID変化を検知（再起動やワーカー変更の確認用）
                data = response.json()
                current_pid = data.get("pid")
                if current_pid is not None:
                    if (
                        self._last_api_pid is not None
                        and current_pid != self._last_api_pid
                    ):
                        # Note: /health PID は uvicorn ワーカー等のPID
                        # Popen PID (親プロセス) とは異なる場合がある
                        # (--reload, --workers, gunicorn移行等)
                        logger.info(
                            f"API worker PID changed: {self._last_api_pid} -> {current_pid} "
                            f"(popen_pid={self._popen_pid}, process change detected)"
                        )
                    self._last_api_pid = current_pid

                logger.debug(f"Health check OK: {data} (popen_pid={self._popen_pid})")
                return

            # 非200レスポンス
            logger.warning(f"Health check failed: status={response.status_code}")
            self._handle_health_failure()

        except httpx.RequestError as e:
            logger.warning(f"Health check failed (request error): {e}")
            self._handle_health_failure()
        except Exception as e:
            # JSON decode error や予期しないエラーでもWatchdog自身は死なない
            logger.warning(f"Health check failed (unexpected error): {e}")
            self._handle_health_failure()

    def _handle_health_failure(self) -> None:
        """ヘルスチェック失敗時の処理"""
        self._consecutive_failures += 1
        logger.warning(
            f"Health check failure count: {self._consecutive_failures}/{self._failure_limit}"
        )

        if self._consecutive_failures >= self._failure_limit:
            logger.error(
                f"API server unresponsive after {self._consecutive_failures} failures"
            )
            self._attempt_restart()

    def _attempt_restart(self) -> None:
        """再起動を試みる (段階的バックオフ付き)

        Note:
            - クールダウン中でも failure_count は維持する（0に戻さない）
            - クールダウン判定は monotonic ベース（NTP/手動時刻変更に強い）
            - last_success_monotonic は restart_count リセットのみに使用
        """
        now_monotonic = time.monotonic()
        cooldown = self._get_current_cooldown()

        # クールダウンチェック（前回再起動からの経過時間で判定）
        if self._last_restart_monotonic is not None:
            elapsed_since_restart = now_monotonic - self._last_restart_monotonic

            # 起動直後の猶予期間チェック
            if elapsed_since_restart < self._startup_grace:
                # 起動猶予期間内はスキップ（カウントは維持）
                logger.info(
                    f"Within startup grace period ({elapsed_since_restart:.0f}s < {self._startup_grace}s), "
                    f"waiting... (failures={self._consecutive_failures})"
                )
                return

            # クールダウンチェック（前回再起動からの経過時間）
            if elapsed_since_restart < cooldown:
                remaining = int(cooldown - elapsed_since_restart)
                logger.warning(
                    f"Restart delayed: remaining={remaining}s "
                    f"(stage={self._restart_count}, failures={self._consecutive_failures})"
                )
                # 注意: failure_count は0に戻さない
                return

        logger.info(
            f"Initiating API server restart... "
            f"(restart_count={self._restart_count}, cooldown={cooldown}s)"
        )
        self._last_restart_monotonic = now_monotonic
        self._restart_count += 1
        # 注意: _consecutive_failures は再起動後も維持
        # 起動成功した場合のみ _check_health でリセットされる

        # 再起動前に httpx client を閉じる（古い接続を破棄）
        self._close_http_client()

        self._stop_api_server()
        time.sleep(2)  # 少し待ってから再起動
        if not self._start_api_server():
            logger.error("API server restart failed")

    def _start_api_server(self) -> bool:
        """APIサーバーを起動

        Returns:
            bool: 起動成功（/healthが200を返した）ならTrue
        """
        logger.info("Starting API server...")

        try:
            # uvicornでAPIサーバーを起動
            # stdout/stderr=None で親プロセスに継承（PIPEは使わない）
            # start_new_session=True でプロセスグループを作成
            self._api_process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "src.api.main:app",
                    "--host",
                    str(self._api_host),
                    "--port",
                    str(self._api_port),
                ],
                cwd=str(project_root),
                stdout=None,  # 親プロセスに継承
                stderr=None,  # 親プロセスに継承
                start_new_session=True,  # 新しいプロセスグループを作成
            )
            self._popen_pid = self._api_process.pid
            logger.info(f"API server process started (popen_pid={self._popen_pid})")

            # /health が200を返すまで待機
            if not self._wait_for_api_ready():
                logger.error("API server did not become ready in time")
                self._stop_api_server()
                return False

            logger.info("API server is ready")
            self._consecutive_failures = 0  # 起動成功で失敗カウンタリセット
            return True

        except Exception as e:
            logger.error(f"Failed to start API server: {e}")
            return False

    def _wait_for_api_ready(self) -> bool:
        """APIサーバーが起動完了するまで待機

        Note:
            再起動時は _attempt_restart で client が閉じられているため、
            ここで _get_http_client() を呼ぶと新しい接続が作られる。

        Returns:
            bool: /health が200を返したらTrue
        """
        logger.info(
            f"Waiting for API server to be ready (max {self._api_startup_timeout}s)..."
        )

        for i in range(self._api_startup_timeout):
            try:
                # 使い回しのクライアントを使用
                # （再起動時は _attempt_restart で閉じられているので新規作成される）
                client = self._get_http_client()
                response = client.get(self._health_url)
                if response.status_code == 200:
                    return True
            except httpx.RequestError:
                pass
            except Exception:
                # 接続エラー等は無視して再試行
                pass

            # プロセスが死んでいないかチェック
            if self._api_process and self._api_process.poll() is not None:
                logger.error(
                    f"API server process died during startup "
                    f"(exit code: {self._api_process.returncode})"
                )
                return False

            time.sleep(self._api_startup_check_interval)

        return False

    def _stop_api_server(self) -> None:
        """APIサーバーを停止（プロセスグループごと）"""
        if self._api_process is None:
            return

        pid = self._api_process.pid
        exit_code = self._api_process.poll()

        # 停止前の状態をログ出力（トラブルシュート用）
        if exit_code is not None:
            logger.info(
                f"API server already stopped (PID: {pid}, exit_code: {exit_code})"
            )
            self._api_process = None
            return

        logger.info(f"Stopping API server (PID: {pid})...")

        try:
            # プロセスグループIDを安全に取得
            # start_new_session=True なら通常 pid == pgid だが、念のため取得
            try:
                pgid = os.getpgid(pid)
            except ProcessLookupError:
                logger.debug("Process already terminated")
                self._api_process = None
                return

            # プロセスグループにSIGTERMを送信
            try:
                os.killpg(pgid, signal.SIGTERM)
            except ProcessLookupError:
                # 既に死んでいる場合
                logger.debug("Process group already terminated")
                self._api_process = None
                return

            # 最大5秒待機
            try:
                self._api_process.wait(timeout=5)
                logger.info("API server stopped gracefully")
            except subprocess.TimeoutExpired:
                # タイムアウト時はSIGKILL
                logger.warning("API server did not stop, sending SIGKILL...")
                try:
                    os.killpg(pgid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                self._api_process.wait()
                logger.info("API server killed")

        except Exception as e:
            logger.error(f"Error stopping API server: {e}")

        finally:
            self._api_process = None


def main() -> None:
    """エントリーポイント"""
    watchdog = APIWatchdog()
    watchdog.start()


if __name__ == "__main__":
    main()
