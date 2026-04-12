import os

from app import app


if __name__ == "__main__":
    from waitress import serve

    serve(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "5000")),
        threads=int(os.environ.get("WAITRESS_THREADS", "6")),
    )
