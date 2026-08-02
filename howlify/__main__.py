import sys


def run_api():
    import uvicorn
    from howlify.api.main import app

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "api":
        run_api()
    else:
        run_api()
