import sys


def run_streamlit():
    import os
    import subprocess
    import sys

    app_path = os.path.join(os.path.dirname(__file__), "..", "app.py")
    cmd = [sys.executable, "-m", "streamlit", "run", os.path.abspath(app_path)]
    sys.exit(subprocess.call(cmd))


def run_api():
    import uvicorn
    from howlify.api.main import app

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "web":
            run_streamlit()
        elif command == "api":
            run_api()
        else:
            print(f"Usage: python -m howlify [web|api]")
    else:
        run_streamlit()
