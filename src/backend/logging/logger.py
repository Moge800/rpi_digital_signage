import logging
import sys
from pathlib import Path
from typing import Optional
from logging.handlers import TimedRotatingFileHandler, RotatingFileHandler


def setup_logger(
    name: str,
    log_file: Optional[str] = None,
    level: int = logging.DEBUG,
    console: bool = True,
    file_encoding: str = "utf-8",
    file_handler_type: str = "rotating",
    file_max_bytes: int = 10 * 1024 * 1024,
    file_backup_count: int = 5,
) -> logging.Logger:
    """ロガーをセットアップする

    コンソール出力とファイル出力の両方に対応したロガーを構築。
    既存のハンドラは自動的にクリアされ、重複を防ぐ。

    Args:
        name: ロガー名 (通常は __name__ を渡す)
        log_file: ログファイルのパス (Noneの場合はファイル出力なし)
        level: ログレベル (logging.DEBUG, INFO, WARNING, ERROR)
        console: コンソール出力するかどうか
        file_encoding: ログファイルのエンコーディング (デフォルト: utf-8)
        file_handler_type: ファイルハンドラの種類 ("rotating" or "timed", その他はFileHandler)
        file_max_bytes: ログファイルの最大サイズ (バイト単位, デフォルト: 10MB)
        file_backup_count: バックアップファイルの数 (デフォルト: 5)

    Returns:
        logging.Logger: 設定済みのロガーインスタンス

    Examples:
        >>> from backend.logging import setup_logger
        >>> logger = setup_logger(__name__, log_file="app.log", level=logging.INFO)
        >>> logger.info("Application started")
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 既存のハンドラをクリア（重複防止 + ファイルハンドル解放）
    if logger.handlers:
        for handler in logger.handlers[:]:
            handler.close()  # ファイルハンドルを明示的に閉じる
            logger.removeHandler(handler)
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

        if file_handler_type == "rotating":
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=file_max_bytes,
                backupCount=file_backup_count,
                encoding=file_encoding,
            )
        elif file_handler_type == "timed":
            file_handler = TimedRotatingFileHandler(
                log_file,
                when="midnight",
                interval=1,
                backupCount=file_backup_count,
                encoding=file_encoding,
            )
        else:
            file_handler = logging.FileHandler(log_file, encoding=file_encoding)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        logger.addHandler(file_handler)

    return logger


def setup_root_logger(log_file: str = "app.log", level: int = logging.INFO) -> None:
    """ルートロガーを設定する (アプリケーション全体で使う場合)

    logging.basicConfig()を使用して、全モジュール共通のロガーを設定。
    コンソールとファイルの両方に出力する。

    Args:
        log_file: ログファイルのパス (デフォルト: "app.log")
        level: ログレベル (logging.INFO, WARNING, ERROR等)

    Note:
        setup_logger()の方が柔軟性が高いため、
        複数モジュールで個別設定が必要な場合はそちらを推奨。

    Examples:
        >>> from backend.logging import setup_root_logger
        >>> setup_root_logger(log_file="main.log", level=logging.DEBUG)
        >>> import logging
        >>> logging.info("Root logger initialized")
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
