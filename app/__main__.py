"""Run with python -m app --base-url URL --model MODEL."""

import argparse
import os
from datetime import datetime

from app.cli import run_cli
from app.llm import LLMClient, http_post


parser = argparse.ArgumentParser(description="이번 주 할 일 플래너")
parser.add_argument("--base-url", default=os.environ.get("FACTCHAT_BASE_URL"), help="ChatKHU OpenAI 호환 v1 기본 URL")
parser.add_argument("--model", default=os.environ.get("FACTCHAT_MODEL"), help="ChatKHU 모델 이름")
args = parser.parse_args()
client = LLMClient(http_post, base_url=args.base_url, model=args.model) if args.base_url and args.model else None
run_cli(datetime.now().astimezone(), client)
