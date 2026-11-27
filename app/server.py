"""Container entrypoint for the planner HTTP service."""

import os
from wsgiref.simple_server import make_server

from app.llm import LLMClient, http_post
from app.web import create_app


def main():
    base_url = os.environ.get("FACTCHAT_BASE_URL")
    model = os.environ.get("FACTCHAT_MODEL")
    client = LLMClient(http_post, base_url=base_url, model=model) if base_url and model else None
    with make_server("0.0.0.0", 8080, create_app(client, commit_sha=os.environ.get("APP_COMMIT_SHA", "unknown"))) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
