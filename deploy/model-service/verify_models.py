"""Verify the three vLLM inference interfaces after deployment."""

import argparse
import json
import math
import os
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def post(base_url, endpoint, payload, timeout, api_key):
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = Request(f"{base_url.rstrip('/')}/{endpoint}",
                      data=json.dumps(payload).encode("utf-8"), headers=headers)
    with urlopen(request, timeout=timeout) as response:
        return json.load(response)


def check_chat(args):
    result = post(args.llm_url, "chat/completions", {
        "model": args.llm_model,
        "messages": [{"role": "user", "content": "Reply with a short greeting."}],
        "max_tokens": 128,
        "temperature": 0,
        "chat_template_kwargs": {"enable_thinking": False},
    }, args.timeout, args.api_key)
    if not any(isinstance(choice.get("message", {}).get("content"), str)
               and choice["message"]["content"].strip() for choice in result["choices"]):
        raise ValueError("No non-empty chat response")


def check_tools(args):
    result = post(args.llm_url, "chat/completions", {
        "model": args.llm_model,
        "messages": [{"role": "user", "content": "Use the lookup_status tool for order A101."}],
        "tools": [{"type": "function", "function": {
            "name": "lookup_status", "description": "Look up a fictional order",
            "parameters": {"type": "object", "properties": {"order_id": {"type": "string"}},
                           "required": ["order_id"]},
        }}],
        "tool_choice": {"type": "function", "function": {"name": "lookup_status"}},
        "temperature": 0, "max_tokens": 128,
        "chat_template_kwargs": {"enable_thinking": False},
    }, args.timeout, args.api_key)
    calls = result["choices"][0]["message"].get("tool_calls", [])
    if not any(call["function"]["name"] == "lookup_status"
               and json.loads(call["function"]["arguments"]).get("order_id") == "A101"
               for call in calls):
        raise ValueError("Expected a structured lookup_status call for A101")


def check_embedding(args):
    result = post(args.embedding_url, "embeddings", {
        "model": args.embedding_model, "input": ["合同审核", "清运订单"],
    }, args.timeout, args.api_key)
    vectors = [row["embedding"] for row in result["data"]]
    if len(vectors) != 2 or not vectors[0] or len(vectors[0]) != len(vectors[1]):
        raise ValueError("Expected two non-empty vectors of the same dimension")
    if not all(isinstance(value, (int, float)) and math.isfinite(value)
               for vector in vectors for value in vector):
        raise ValueError("Embedding contains an invalid number")


def check_rerank(args):
    result = post(args.rerank_url, "rerank", {
        "model": args.rerank_model,
        "query": "合同审批流程",
        "documents": ["合同需要经过法务部门审批。", "今天的天气晴朗。"],
        "top_n": 2,
    }, args.timeout, args.api_key)
    rows = result["results"]
    if len(rows) != 2 or {row["index"] for row in rows} != {0, 1}:
        raise ValueError("Expected distinct results for both documents")
    if not all(isinstance(row["relevance_score"], (int, float))
               and math.isfinite(row["relevance_score"]) for row in rows):
        raise ValueError("Reranker returned an invalid relevance score")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--llm-url", default="http://127.0.0.1:8666/v1")
    parser.add_argument("--embedding-url", default="http://127.0.0.1:6667/v1")
    parser.add_argument("--rerank-url", default="http://127.0.0.1:6657/v1")
    parser.add_argument("--llm-model", default="qwen3.8-27b")
    parser.add_argument("--embedding-model", default="Qwen3-Embedding-4B")
    parser.add_argument("--rerank-model", default="Qwen3-Reranker-4B")
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--llm-only", action="store_true")
    args = parser.parse_args()
    args.api_key = os.environ.get("VLLM_API_KEY", "")
    if args.timeout <= 0:
        parser.error("timeout must be positive")

    checks = [("chat", check_chat), ("tool calling", check_tools)]
    if not args.llm_only:
        checks += [("embedding", check_embedding), ("rerank", check_rerank)]
    failed = False
    for name, check in checks:
        start = time.monotonic()
        try:
            check(args)
            print(f"[OK] {name}: {time.monotonic() - start:.2f}s")
        except HTTPError as exc:
            failed = True
            print(f"[FAIL] {name}: HTTP {exc.code}", file=sys.stderr)
        except (URLError, TimeoutError, ValueError, KeyError, TypeError, IndexError, AttributeError) as exc:
            failed = True
            print(f"[FAIL] {name}: {exc}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
