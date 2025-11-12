import subprocess
import sys


def main():
    """Streamlitアプリケーションを起動する"""
    try:
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", "src/frontend/signage_app.py"],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Error running Streamlit: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nStreamlit stopped by user")
        sys.exit(0)


if __name__ == "__main__":
    main()
