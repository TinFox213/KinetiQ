import os
import sys

# Add root directory to sys.path so app and src can be imported seamlessly
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app import app as fastapi_app


async def app(scope, receive, send):
    """
    ASGI entrypoint for Vercel Python runtime.
    Restores original URL path when Vercel rewrites incoming requests to /api/index.py.
    """
    if scope["type"] == "http":
        headers = {
            k.decode("latin1").lower(): v.decode("latin1")
            for k, v in scope.get("headers", [])
        }

        # Inspect Vercel routing headers
        matched_path = (
            headers.get("x-matched-path")
            or headers.get("x-vercel-matched-path")
            or headers.get("x-forwarded-uri")
            or headers.get("x-real-path")
            or headers.get("x-rewrite-url")
            or headers.get("x-original-url")
        )

        current_path = scope.get("path", "")
        # If current path is the script itself or root rewrite
        if matched_path and (
            current_path.endswith("index.py")
            or current_path == "/api"
            or current_path == "/api/"
            or current_path == "/"
        ):
            clean_path = matched_path.split("?")[0]
            scope["path"] = clean_path
            scope["raw_path"] = clean_path.encode("latin1")

    await fastapi_app(scope, receive, send)
