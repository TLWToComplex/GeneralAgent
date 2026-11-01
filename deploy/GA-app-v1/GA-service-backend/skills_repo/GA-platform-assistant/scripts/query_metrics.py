"""查询GeneralAgent平台使用追踪指标（基于 Langfuse traces 聚合）。

子命令：
    summary       — 默认 30 天概览（总 trace 数、去重用户数、活跃天数）
    top-users     — 按 trace 计数排序的用户榜单
    user-activity — 单用户的活动详情

例：
    python query_metrics.py summary
    python query_metrics.py summary --from 2026-05-01 --to 2026-06-15
    python query_metrics.py top-users --limit 5
    python query_metrics.py user-activity --user-name alice --sample 10

附加：
    所有子命令都支持 --html，会同时生成 HTML 报告（默认放到 /workspace）。
"""
import argparse

from _backend import die, http_get, print_json
from _render import render_report


def parse_args():
    parser = argparse.ArgumentParser(description="查询平台使用追踪指标")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_sum = sub.add_parser("summary", help="整体概览")
    p_sum.add_argument("--from", dest="from_date", default=None, help="起始时间（ISO 或 YYYY-MM-DD），默认 None")
    p_sum.add_argument("--to", dest="to_date", help="结束时间，默认现在")
    p_sum.add_argument("--html", nargs="?", const="", default=None,
                       help="生成 HTML 报告；可指定文件名，默认写入 workspace 目录下的 metrics_summary_<时间戳>.html")

    p_top = sub.add_parser("top-users", help="使用次数排行榜")
    p_top.add_argument("--from", dest="from_date", default=None, help="起始时间（ISO 或 YYYY-MM-DD），默认 None")
    p_top.add_argument("--to", dest="to_date", help="结束时间，默认现在")
    p_top.add_argument("--limit", type=int, default=20)
    p_top.add_argument("--html", nargs="?", const="", default=None,
                       help="生成 HTML 报告；可指定文件名，默认写入 workspace 目录下的 metrics_top_users_<时间戳>.html")

    p_user = sub.add_parser("user-activity", help="单用户活动")
    p_user.add_argument("--user-name", required=True)
    p_user.add_argument("--from", dest="from_date", default=None, help="起始时间（ISO 或 YYYY-MM-DD），默认 None")
    p_user.add_argument("--to", dest="to_date", help="结束时间，默认现在")
    p_user.add_argument("--sample", type=int, default=5)
    p_user.add_argument("--html", nargs="?", const="", default=None,
                       help="生成 HTML 报告；可指定文件名，默认写入 workspace 目录下的 metrics_user_activity_<时间戳>.html")

    return parser.parse_args()


def _maybe_render(args, data):
    html_flag = getattr(args, "html", None)
    if html_flag is None:
        return None
    if args.cmd == "summary":
        return render_report(
            report_type="metrics-summary",
            title="平台使用概览",
            data=data, out_path=html_flag or None,
            default_basename="metrics_summary.html",
        )
    if args.cmd == "top-users":
        return render_report(
            report_type="metrics-top-users",
            title=f"用户使用排行 · TOP {args.limit}",
            data=data, out_path=html_flag or None,
            default_basename="metrics_top_users.html",
        )
    if args.cmd == "user-activity":
        return render_report(
            report_type="metrics-user-activity",
            title=f"用户活动详情 · {args.user_name}",
            data=data, out_path=html_flag or None,
            default_basename="metrics_user_activity.html",
        )
    return None


def main():
    args = parse_args()
    if args.cmd == "summary":
        resp = http_get("/aiUsageMetrics/summary", {"fromDate": args.from_date, "toDate": args.to_date})
    elif args.cmd == "top-users":
        resp = http_get("/aiUsageMetrics/topUsers", {
            "fromDate": args.from_date,
            "toDate": args.to_date,
            "limit": args.limit,
        })
    elif args.cmd == "user-activity":
        resp = http_get("/aiUsageMetrics/userActivity", {
            "userName": args.user_name,
            "fromDate": args.from_date,
            "toDate": args.to_date,
            "sample": args.sample,
        })
    else:
        die(f"未知子命令: {args.cmd}")

    if resp.get("code") not in (200, 0):
        die(f"接口返回错误: {resp.get('message') or resp}")

    data = resp.get("data") if "data" in resp else resp
    html_path = _maybe_render(args, data)
    if html_path:
        if isinstance(data, dict):
            data = dict(data)
            data["htmlPath"] = html_path
        else:
            data = {"raw": data, "htmlPath": html_path}
    print_json(data)


if __name__ == "__main__":
    main()
