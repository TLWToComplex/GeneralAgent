"""生成用户反馈操作面板（HTML）。

脚本不接收任何业务参数 —— 只输出一份带 列表 / 新增 / 编辑 / 删除 功能的 HTML 操作页。
用户在浏览器里点按钮，由页面 JS 直接 POST 到后台 `/aiUserFeedback/{list,add,update,delete}` 接口。

用法：
    python manage_feedback.py                    # 默认写到 workspace/feedback_form_<时间戳>.html
    python manage_feedback.py --html my.html     # 自定义输出文件名

不需要 --action / --uuid 等参数，所有选择都在 HTML 页面里做。
"""
import argparse
import datetime as _dt
import json
import os
import sys

from zoneinfo import ZoneInfo

from _backend import get_user_name, get_backend_url, http_get, print_json
from _render import _resolve_output_path  # 复用 workspace 路径解析


_TEMPLATE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets",
    "feedback_form_template.html",
)

LOCAL_TZ = ZoneInfo("Asia/Shanghai")


def parse_args():
    parser = argparse.ArgumentParser(description="生成用户反馈操作面板 (HTML)")
    parser.add_argument("--html", nargs="?", const="", default="",
                        help="HTML 输出路径；默认写入 workspace 目录下 feedback_form_<时间戳>.html")
    return parser.parse_args()


def _escape_html(text: str) -> str:
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;"))


def main():
    args = parse_args()
    username = get_user_name()
    target = _resolve_output_path(args.html or None, "feedback_form.html")
    os.makedirs(os.path.dirname(target) or ".", exist_ok=True)

    with open(_TEMPLATE_PATH, "r", encoding="utf-8") as f:
        tpl = f.read()

    # 服务端预拉取反馈列表
    items = []
    try:
        resp = http_get("/aiUserFeedback/list", {"skip": 0, "take": 1000})
        if resp.get("code") == 200:
            data = resp.get("data") or {}
            items = data.get("items", [])
    except Exception:
        pass

    # 普通用户只保留自己创建的记录
    is_admin = (username == "admin")
    if not is_admin:
        items = [it for it in items if (it.get("create_by") or "").lower() == username]

    backend_url = get_backend_url()
    if backend_url.startswith("http://host.docker.internal"):
        backend_url = "http://127.0.0.1:8038"

    payload = {
        "generatedAt": _dt.datetime.now(LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S"),
        "backendUrl": backend_url,
        "backendToken": get_user_name(),
        "currentUser": username,
        "isAdmin": is_admin,
        "items": items,
    }
    payload_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")

    rendered = (tpl
                .replace("__FORM_TITLE__", _escape_html("用户反馈管理面板"))
                .replace("__FORM_DATA_JSON__", payload_json))

    with open(target, "w", encoding="utf-8") as f:
        f.write(rendered)

    print(f"[HTML written] {os.path.basename(target)}", file=sys.stderr)

    print_json({
        "htmlPath": target,
        "currentUser": username,
        "isAdmin": is_admin,
        "itemsCount": len(items),
        "backendUrl": backend_url,
        "endpoints": [
            "/aiUserFeedback/list",
            "/aiUserFeedback/add",
            "/aiUserFeedback/update",
            "/aiUserFeedback/delete",
        ],
    })


if __name__ == "__main__":
    main()
