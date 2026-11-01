"""日报查询 Skill — 共享工具函数"""

import hashlib
import re
import urllib.parse
from datetime import date

import httpx

from config import MAIN_SYSTEM_BASE


# # ─── Token 提取 ───
#
# def extract_token(context: str) -> str | None:
#     """从对话上下文中提取 token，格式：[当前用户token: <token>]"""
#     match = re.search(r"当前用户token:\s*(\S+)", context)
#     if match:
#         return match.group(1)
#     return None


# ─── 日报 ID 计算 ───

def compute_report_id(author_id: str, date_str: str) -> str:
    """计算日报 ID = md5(author_id_date)"""
    return hashlib.md5(f"{author_id}_{date_str}".encode()).hexdigest()


# ─── 文件名解析 ───

def parse_filename(filename: str) -> dict | None:
    """
    解析知识库文件名格式：{author_id}_{date}_{original_filename}

    author_id: UUID 36 位
    date: YYYY-MM-DD
    original_filename: 原始文件名
    """
    pattern = r"^([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})_(\d{4}-\d{2}-\d{2})_(.+)$"
    match = re.match(pattern, filename)
    if not match:
        return None
    return {
        "author_id": match.group(1),
        "date": date.fromisoformat(match.group(2)),
        "original_filename": match.group(3),
    }


# ─── 用户名称解析 ───

async def resolve_author_name(author_id: str, token: str) -> str:
    """通过主系统 /aiUser/record 接口，根据 user_id 查询用户 realname"""
    url = f"{MAIN_SYSTEM_BASE.rstrip('/')}/aiUser/record"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                url,
                params={"id": author_id},
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == 200 and data.get("data"):
                    return data["data"].get("realname", "")
    except Exception:
        pass
    return ""


# ─── 前端链接生成 ───

def generate_frontend_link(frontend_url: str, token: str, **params) -> str:
    """生成带参数的前端日报页面链接，返回 Markdown 行内代码格式"""
    p = {"token": token}
    for k, v in params.items():
        if v:
            p[k] = v
    qs = "&".join(f"{k}={urllib.parse.quote(str(v), safe='')}" for k, v in p.items())
    return f"`{frontend_url}?{qs}`"


# ─── 日报列表格式化 ───

def format_reports(reports: list[dict], author_names: dict[str, str] | None = None) -> str:
    """将日报 API 响应格式化为可读文本"""
    if not reports:
        return "未找到符合条件的日报记录。"

    names = author_names or {}
    lines = [f"共找到 {len(reports)} 条日报记录：\n"]
    for i, r in enumerate(reports, 1):
        name = r.get("author_name") or names.get(r.get("author_id", ""), r.get("author_id", ""))
        lines.append(f"{i}. **{name}** - {r.get('date', '')}")
        if r.get("content_today"):
            lines.append(f"   今日工作：{r['content_today']}")
        if r.get("content_plan"):
            lines.append(f"   明日计划：{r['content_plan']}")
        if r.get("content_issue"):
            lines.append(f"   问题风险：{r['content_issue']}")
        if r.get("files"):
            files = r["files"]
            if isinstance(files, dict):
                lines.append(f"   附件：{', '.join(files.keys())}")
        lines.append("")
    return "\n".join(lines)