import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str,
    log_file: Optional[str] = None,
    level: int = logging.DEBUG,
    console: bool = True,
    file_encoding: str = "utf-8",
) -> logging.Logger:
    """
    ロガーをセットアップする

    Args:
        name: ロガー名（通常は __name__ を渡す）
        log_file: ログファイルのパス（Noneの場合はファイル出力なし）
        level: ログレベル
        console: コンソール出力するかどうか
        file_encoding: ログファイルのエンコーディング

    Returns:
        設定済みのロガーインスタンス
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 既存のハンドラをクリア（重複防止）
    if logger.handlers:
        logger.handlers.clear()

    # フォーマッタ
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # コンソールハンドラ
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(level)
        logger.addHandler(console_handler)

    # ファイルハンドラ
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding=file_encoding)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        logger.addHandler(file_handler)

    return logger


def setup_root_logger(log_file: str = "app.log", level: int = logging.INFO) -> None:
    """
    ルートロガーを設定する（アプリケーション全体で使う場合）

    Args:
        log_file: ログファイルのパス
        level: ログレベル
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )
