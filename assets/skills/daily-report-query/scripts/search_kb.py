"""Mode 2: 语义搜索知识库中的附件，解析文件名获取关联日报

用法:
    python search_kb.py <query> [--frontend-url URL]

示例:
    python search_kb.py "登录模块"
    python search_kb.py "数据迁移方案" --frontend-url "http://localhost:8038/report-hub"
"""

import argparse
import json
import sys
from datetime import date

import httpx

from config import KB_API_BASE, REPORTS_API_BASE, USER_TOKEN
from utils import compute_report_id, format_reports, generate_frontend_link, parse_filename, resolve_author_name

KB_NAME = "daily-report"

KB_SEARCH_DEFAULTS = {
    "top_k": 5,
    "score_threshold": 0.3,
    "file_name": "",
    "metadata": {},
    "enable_rerank": True,
    "graph_local_search_top_k": 3,
    "graph_global_search_top_k": 5,
}

async def search_knowledge_base(query: str) -> dict:
    """调用知识库搜索 API"""
    payload = {"query": query, "knowledge_base_name": KB_NAME, **KB_SEARCH_DEFAULTS}

    url = f"{KB_API_BASE.rstrip('/')}/knowledge_base/search_docs"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, json=payload)
        if resp.status_code == 200:
            return resp.json()
        return {"error": f"KB API Error: status={resp.status_code}", "body": resp.text}


def parse_search_results(kb_data: dict | list) -> list[dict]:
    """从知识库搜索结果中提取文件信息，解析文件名"""
    results = []
    # 兼容多种响应格式：直接 list、{data: [...]}、{items: [...]}、{data: {documents: [...]}}
    if isinstance(kb_data, list):
        items = kb_data
    elif isinstance(kb_data, dict):
        items = kb_data.get("data", kb_data.get("items", []))
        if isinstance(items, dict):
            items = items.get("documents", [])
    else:
        return results
    if not isinstance(items, list):
        return results

    for item in items:
        filename = item.get("file_path", item.get("file_path", item.get("file_path", "")))
        if not filename:
            continue

        parsed = parse_filename(filename)
        if not parsed:
            continue

        results.append({
            **parsed,
            "score": item.get("score", 0),
            "content": item.get("content", item.get("text", "")),
            "file_name": filename,
        })

    return results


async def fetch_reports_by_ids(
    pairs: list[tuple[str, date]], token: str
) -> list[dict]:
    """通过日报 ID 列表批量精确查询"""
    if not pairs:
        return []

    ids = [compute_report_id(aid, d.isoformat()) for aid, d in pairs]
    ids_param = ",".join(ids)
    url = f"{REPORTS_API_BASE.rstrip('/')}/api/reports?ids={ids_param}&page_size=200"

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, headers={"Authorization": f"Bearer {token}"})
        if resp.status_code != 200:
            return []
        return resp.json().get("items", [])


def format_kb_results(kb_results: list[dict], author_names: dict[str, str]) -> str:
    """格式化知识库搜索结果"""
    if not kb_results:
        return ""

    lines = [f"知识库搜索到 {len(kb_results)} 条相关附件：\n"]
    for i, item in enumerate(kb_results, 1):
        name = author_names.get(item["author_id"], item["author_id"])
        lines.append(f"{i}. **{item['original_filename']}**")
        lines.append(f"   匹配分数：{item['score']:.2f}")
        lines.append(f"   关联日报：{name} - {item['date']}")
        if item.get("content"):
            snippet = item["content"][:200].replace("\n", " ")
            lines.append(f"   相关片段：{snippet}...")
        lines.append("")
    return "\n".join(lines)


async def main():
    parser = argparse.ArgumentParser(description="语义搜索知识库附件并关联日报")
    parser.add_argument("query", help="搜索关键词")
    parser.add_argument("--frontend-url", default="", help="前端页面地址")
    args = parser.parse_args()

    # 1. 搜索知识库
    kb_data = await search_knowledge_base(args.query)

    if "error" in kb_data:
        print(kb_data["error"], file=sys.stderr)
        if "body" in kb_data:
            print(kb_data["body"], file=sys.stderr)
        sys.exit(1)

    # 2. 解析文件名
    kb_results = parse_search_results(kb_data)

    if not kb_results:
        print(f'知识库中未找到与"{args.query}"相关的内容。')
        print("\n知识库原始返回：")
        print(json.dumps(kb_data, ensure_ascii=False, indent=2))
        return

    # 3. 解析作者名称
    unique_author_ids = set(r["author_id"] for r in kb_results)
    author_names: dict[str, str] = {}
    for aid in unique_author_ids:
        name = await resolve_author_name(aid, USER_TOKEN)
        author_names[aid] = name or aid

    # 4. 获取关联日报
    pairs = [(r["author_id"], r["date"]) for r in kb_results]
    reports = await fetch_reports_by_ids(pairs, USER_TOKEN)

    # 5. 输出结果
    print(format_kb_results(kb_results, author_names))

    if reports:
        print("关联日报记录：")
        print(format_reports(reports, author_names))
    else:
        print("未找到关联的日报记录。")

    # 6. 生成前端链接（按 ID 列表）
    if args.frontend_url and pairs:
        report_ids = [compute_report_id(aid, d.isoformat()) for aid, d in pairs]
        link = generate_frontend_link(
            frontend_url=args.frontend_url,
            token=USER_TOKEN,
            ids=",".join(report_ids),
        )
        print(f"\n{link}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
