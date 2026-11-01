"""Mode 1: 按时间范围和人员直接查询日报 API

用法:
    python query_reports.py [--start DATE] [--end DATE] [--staff NAMES] [--frontend-url URL]

示例:
    python query_reports.py --start 2026-07-01 --end 2026-07-01
    python query_reports.py --staff 张三,李四
    python query_reports.py --start 2026-06-29 --end 2026-07-01 --staff 张三
"""

import argparse
import json
import sys
import urllib.parse

import httpx

from config import REPORTS_API_BASE, USER_TOKEN
from utils import format_reports, generate_frontend_link


async def query_reports(
    token: str,
    start_date: str | None = None,
    end_date: str | None = None,
    staff_names: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """调用日报列表 API"""
    params = {"all": "true", "page": str(page), "page_size": str(page_size)}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    if staff_names:
        params["staff_names"] = staff_names

    qs = "&".join(f"{k}={urllib.parse.quote(v, safe='')}" for k, v in params.items())
    url = f"{REPORTS_API_BASE.rstrip('/')}/api/reports?{qs}"

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, headers={"Authorization": f"Bearer {token}"})
        if resp.status_code == 200:
            return resp.json()
        return {"error": f"API Error: status={resp.status_code}", "body": resp.text}


async def main():
    parser = argparse.ArgumentParser(description="查询日报")
    parser.add_argument("--start", default=None, help="开始日期 YYYY-MM-DD")
    parser.add_argument("--end", default=None, help="结束日期 YYYY-MM-DD")
    parser.add_argument("--staff", default=None, help="员工名称，多个用逗号分隔")
    parser.add_argument("--frontend-url", default="", help="前端页面地址，传入后生成页面链接")
    args = parser.parse_args()

    data = await query_reports(
        token=USER_TOKEN,
        start_date=args.start,
        end_date=args.end,
        staff_names=args.staff,
    )

    if "error" in data:
        print(data["error"], file=sys.stderr)
        if "body" in data:
            print(data["body"], file=sys.stderr)
        sys.exit(1)

    items = data.get("items", [])
    total = data.get("total", 0)

    # 格式化输出
    print(format_reports(items))

    # 生成前端链接
    if args.frontend_url:
        link = generate_frontend_link(
            frontend_url=args.frontend_url,
            token=USER_TOKEN,
            all="true",
            start_date=args.start,
            end_date=args.end,
            staff_names=args.staff,
        )
        print(link)

    # 输出 JSON 供程序化使用
    print("\n--- JSON ---")
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())