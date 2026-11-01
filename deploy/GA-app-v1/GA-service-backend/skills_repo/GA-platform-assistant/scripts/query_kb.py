"""通过 kb_chat 代理检索知识库（默认查《GeneralAgent用户手册》一类文档）。

用法：
    python query_kb.py "如何创建知识库"
    python query_kb.py "Canvas 是什么"
    python query_kb.py "Canvas 是什么" --html              # 同时生成 HTML 报告
    python query_kb.py "Canvas 是什么" --html canvas.html

后端会转发到 KBChatConfig.BASE_URL/knowledge_base/search_docs。
"""
import argparse
import os

from _backend import die, http_post, print_json
from _render import render_report

kb_name = "GeneralAgent用户手册"  # 默认知识库名称，除非通过命令行参数或环境变量覆盖

def get_kb_name() -> str:
    return (os.getenv("KB_NAME") or kb_name).strip()

def parse_args():
    parser = argparse.ArgumentParser(description="检索GeneralAgent知识库")
    parser.add_argument("query", help="用户问题或检索关键词")
    parser.add_argument("--html", nargs="?", const="", default=None,
                        help="生成 HTML 报告；可指定文件名，默认写入 workspace 目录下的 kb_report_<时间戳>.html")
    return parser.parse_args()


def _extract_docs(resp):
    """从 kb_chat 返回的 JSON 中尽力提取 docs 列表，统一为 [{file_name, page_content, score, ...}]"""
    if isinstance(resp, list):
        candidates = resp
    elif isinstance(resp, dict):
        candidates = resp.get("docs") or resp.get("source_documents") or resp.get("data") or resp.get("raw")
    else:
        return []
    if isinstance(candidates, dict):
        candidates = candidates.get("docs") or candidates.get("source_documents") or candidates.get("data") or candidates.get("raw") or []
    if not isinstance(candidates, list):
        return []
    normalized = []
    for d in candidates:
        if not isinstance(d, dict):
            continue
        meta = d.get("metadata") if isinstance(d.get("metadata"), dict) else {}
        score = d.get("score")
        if score is None or (isinstance(score, (int, float)) and score > 1):
            score = meta.get("score", meta.get("relevance_score", score))
        normalized.append({
            "file_name": d.get("file_name") or meta.get("source") or meta.get("file_name"),
            "kb_name": d.get("kb_name") or meta.get("kb_name") or meta.get("knowledge_base_name"),
            "score": score,
            "page": d.get("page") or meta.get("page"),
            "page_content": d.get("page_content") or d.get("content") or d.get("text") or "",
        })
    return normalized


def main():
    args = parse_args()
    payload = {
        "query": args.query,
        "knowledge_base_name": get_kb_name(),
        "top_k": 3,
        "score_threshold": 0.3,
        "file_name": "",
        "metadata": {},
        "enable_rerank": True,
        "graph_local_search_top_k": 3,
        "graph_global_search_top_k": 5,
    }
    resp = http_post("/kb_chat/knowledge_base/search_docs", payload)
    if isinstance(resp, dict) and resp.get("code") and resp["code"] not in (200, 0):
        die(f"知识库检索失败: {resp.get('message') or resp}")

    if args.html is not None:
        docs = _extract_docs(resp)
        html_path = render_report(
            report_type="kb",
            title=f"GeneralAgent知识库检索 · {args.query}",
            data={"query": args.query, "kb_name": get_kb_name(), "docs": docs},
            out_path=args.html or None,
            default_basename="kb_report.html",
        )
        if isinstance(resp, dict):
            resp = dict(resp)
            resp["htmlPath"] = html_path
        else:
            resp = {"raw": resp, "htmlPath": html_path}

    print_json(resp)


if __name__ == "__main__":
    main()
