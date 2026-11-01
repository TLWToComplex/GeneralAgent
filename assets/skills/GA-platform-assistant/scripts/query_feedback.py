"""查询 ai_user_feedback 表（用户反馈与改进追溯）。

用法示例：
    python query_feedback.py                            # 列出全部
    python query_feedback.py --keyword 知识库 --limit 5
    python query_feedback.py --priority 高 --status 已上线
    python query_feedback.py --source 培训会
    python query_feedback.py --keyword 知识库 --html      # 同时生成 HTML 报告
    python query_feedback.py --keyword 知识库 --html my.html
"""
import argparse

from _backend import die, http_get, print_json, get_user_name
from _render import render_report


def parse_args():
    parser = argparse.ArgumentParser(description="查询用户反馈与改进追溯记录")
    parser.add_argument("--keyword", help="关键字，匹配反馈内容/改进措施/验证结果/备注")
    parser.add_argument("--priority", choices=["高", "中", "低"], help="需求优先级")
    parser.add_argument("--status", help="当前进度状态，如 需求确认/开发中/已上线")
    parser.add_argument("--source", help="需求来源 模糊匹配")
    parser.add_argument("--skip", type=int, default=0)
    parser.add_argument("--limit", type=int, default=500, help="返回条数（=后端 take 参数）")
    parser.add_argument("--html", nargs="?", const="", default=None,
                        help="生成 HTML 报告；可指定文件名，默认写入 workspace 目录下的 feedback_report_<时间戳>.html")
    return parser.parse_args()


def main():
    args = parse_args()
    username = get_user_name()
    params = {
        "keyword": args.keyword,
        "priority": args.priority,
        "status": args.status,
        "source": args.source,
        "create_by": username if username != "admin" else None,
        "skip": args.skip,
        "take": args.limit,
    }
    resp = http_get("/aiUserFeedback/query", params)
    if resp.get("code") != 200:
        die(f"接口返回错误: {resp.get('message') or resp}")
    data = resp.get("data") or {}
    result = {
        "total": data.get("total", 0),
        "items": data.get("items", []),
    }

    if args.html is not None:
        title_bits = ["用户反馈"]
        if args.keyword: title_bits.append(f"关键词={args.keyword}")
        if args.priority: title_bits.append(f"优先级={args.priority}")
        if args.status: title_bits.append(f"状态={args.status}")
        if args.source: title_bits.append(f"需求来源={args.source}")
        html_path = render_report(
            report_type="feedback",
            title=" · ".join(title_bits),
            data=result,
            out_path=args.html or None,
            default_basename="feedback_report.html",
        )
        result["htmlPath"] = html_path

    print_json(result)


if __name__ == "__main__":
    main()
