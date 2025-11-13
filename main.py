import subprocess
import sys
from src.backend.logging import setup_root_logger


def main():
    """Streamlitアプリケーションを起動する"""
    setup_root_logger(log_file="logs/app.log", level=20)  # INFO
    from src.backend.logging import launcher_logger

    launcher_logger.info("Starting Streamlit application...")
    try:
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", "src/frontend/signage_app.py"],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        launcher_logger.error(f"Error running Streamlit: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        launcher_logger.info("Streamlit stopped by user")
        sys.exit(0)


if __name__ == "__main__":
    main()
