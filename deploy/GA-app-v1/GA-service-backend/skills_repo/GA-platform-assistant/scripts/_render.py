"""HTML 报告渲染：把脚本拿到的 JSON 套进 assets/report_template.html。

写入完成后向 stderr 打印 [HTML] 行（仅用于调试，避免污染脚本 JSON 输出）。
真正给前端下发下载链接由 admin_server 的 FileLinkInjector 完成：它会扫描脚本 JSON
输出里的真实文件路径并自动生成下载链接。
"""
import datetime as _dt
import json
import os
import sys
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo

_TEMPLATE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets",
    "report_template.html",
)

# 不同 reportType 的展示标题
_TYPE_LABELS = {
    "feedback": "用户反馈与改进追溯",
    "kb": "GeneralAgent知识库检索",
    "metrics-summary": "平台使用概览",
    "metrics-top-users": "用户使用排行",
    "metrics-user-activity": "用户活动详情",
}

LOCAL_TZ = ZoneInfo("Asia/Shanghai")

# 默认输出目录：沙盒下落到 /workspace；其他环境（本地调试）落到 cwd
def _default_output_dir() -> str:
    if os.path.isdir("/workspace"):
        return "/workspace"
    return os.getcwd()


def _resolve_output_path(out_path: Optional[str], default_basename: str) -> str:
    """规则：
    - 传绝对路径 -> 原样使用
    - 传相对路径或仅文件名 -> 拼到默认目录下
    - 没传 -> 默认目录 + default_basename（自动插入时间戳）
    """
    if not out_path:
        ts = _dt.datetime.now(LOCAL_TZ).strftime("%Y%m%d_%H%M%S")
        name, ext = os.path.splitext(default_basename)
        return os.path.join(_default_output_dir(), f"{name}_{ts}{ext}")
    if os.path.isabs(out_path):
        return out_path
    return os.path.join(_default_output_dir(), out_path)


def render_report(*,
                  report_type: str,
                  title: str,
                  data: Dict[str, Any],
                  out_path: Optional[str] = None,
                  default_basename: str = "report.html") -> str:
    """渲染并写出 HTML，返回最终文件路径。"""
    target = _resolve_output_path(out_path, default_basename)
    os.makedirs(os.path.dirname(target) or ".", exist_ok=True)

    with open(_TEMPLATE_PATH, "r", encoding="utf-8") as f:
        tpl = f.read()

    payload = {
        "reportType": report_type,
        "generatedAt": _dt.datetime.now(LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S"),
        "data": data,
    }
    payload_json = json.dumps(payload, ensure_ascii=False)
    # 防止数据里出现 </script> 把 inline JSON script 提前关掉
    payload_json = payload_json.replace("</", "<\\/")

    rendered = (tpl
                .replace("__REPORT_TITLE__", _escape_html(title))
                .replace("__REPORT_TYPE_LABEL__", _escape_html(_TYPE_LABELS.get(report_type, report_type)))
                .replace("__REPORT_DATA_JSON__", payload_json))

    with open(target, "w", encoding="utf-8") as f:
        f.write(rendered)

    # 仅打印一个不含 /workspace/ 前缀的提示，避免被 FileLinkInjector 误抓到多余路径
    print(f"[HTML written] {os.path.basename(target)}", file=sys.stderr)
    return target


def _escape_html(text: str) -> str:
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;"))
