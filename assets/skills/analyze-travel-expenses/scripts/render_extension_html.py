#!/usr/bin/env python3
"""把配置启用的分析模块结果按 templates/ 下的模板渲染，组装生成 财务分析报告.html。

本脚本不重新计算任何统计：只读取 analyze_expenses.py 生成的 财务分析报告.html
（主报告）与 run_extensions.py 生成的 extension_analysis.json（模块结果），
按模板填充占位符，以纯 HTML/CSS 组装完整报告（不引入任何图表依赖包）。

约定：
- 每个可渲染模块在 templates/ 下有一个同名模板：<模块名>.html（完整 <section> 块）。
- 报告外壳为 templates/report_shell.html，主报告正文填充到 {{MAIN_REPORT}}，
  各模块章节插入到 </body> 之前。
- 模板占位符为 {{名称}}，可用占位符由本脚本的填充函数（BUILDERS）定义。
- 渲染前执行总分平衡校验；校验不通过时退出码 2 且不改动报告。

用法（固定流程中 run_extensions.py 之后执行）：
    python scripts/render_extension_html.py --output-dir <输出目录> --config config/config.json
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config_loader import load_config  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_NAME = "财务分析报告.html"
SHELL_NAME = "report_shell.html"
BANDS = ["95%以上", "90%-95%", "80%-90%", "70%-80%", "70%以下"]


def _esc(value) -> str:
    return html.escape(str(value), quote=True)


def _fmt_amount(value: float) -> str:
    return f"{value:,.2f}"


def _bar(share: float, color: str) -> str:
    width = max(0.0, min(share, 1.0)) * 100
    return (f'<span class="cr-bar" style="--w:{width:.1f}%;--c:{color}">'
            f'<i></i><b>{share * 100:.1f}%</b></span>')


# ---------------- ceiling_reimbursement ----------------

def build_ceiling(result: dict, config: dict) -> dict[str, str]:
    """由 ceiling_reimbursement 模块结果构造模板占位符，并执行总分平衡校验。"""
    department_rows = result.get("department_bands", [])
    top_people = result.get("top_50_people", [])
    dept_col = config.get("department_column", "报账部门")

    depts: dict[str, list[dict]] = {}
    for row in department_rows:
        depts.setdefault(row["department"], []).append(row)
    for rows in depts.values():
        rows.sort(key=lambda r: BANDS.index(r["band"]) if r["band"] in BANDS else 99)

    def dept_amount(rows: list[dict]) -> float:
        return sum(r["amount"] for r in rows)

    ordered_depts = sorted(depts.items(), key=lambda kv: (-dept_amount(kv[1]), kv[0]))

    grand_count = sum(r["count"] for r in department_rows)
    grand_amount = sum(r["amount"] for r in department_rows)

    overall = {b: {"count": 0, "amount": 0.0} for b in BANDS}
    for r in department_rows:
        if r["band"] in overall:
            overall[r["band"]]["count"] += r["count"]
            overall[r["band"]]["amount"] += r["amount"]

    # 平衡校验：部门分段行数 = 部门数 × 分段数；分段加总 = 总计；TopN 分段加总 = 合计
    problems = []
    if len(department_rows) != len(depts) * len(BANDS):
        problems.append(f"分段行数 {len(department_rows)} ≠ 部门数 {len(depts)} × 分段数 {len(BANDS)}")
    for dept, rows in depts.items():
        missing = set(BANDS) - {r["band"] for r in rows}
        if missing:
            problems.append(f"部门 {dept} 分段缺失: {sorted(missing)}")
    if sum(v["count"] for v in overall.values()) != grand_count:
        problems.append("分段次数加总与总次数不平")
    if round(sum(v["amount"] for v in overall.values()), 2) != round(grand_amount, 2):
        problems.append("分段金额加总与总金额不平")
    for p in top_people:
        band_sum = sum(p.get(b, 0) for b in BANDS)
        if band_sum != p.get("count", 0):
            problems.append(f"人员 {p.get('person')} 分段次数加总 {band_sum} ≠ 合计 {p.get('count')}")
    if problems:
        raise SystemExit("平衡校验未通过: " + "; ".join(problems))

    top95 = overall["95%以上"]
    top90 = overall["90%-95%"]
    ceil_count = top95["count"] + top90["count"]
    ceil_amount = top95["amount"] + top90["amount"]
    overall_rows = []
    for b in BANDS:
        v = overall[b]
        overall_rows.append(
            f'<tr><td class="cr-left">{_esc(b)}</td><td>{v["count"]:,}</td>'
            f'<td>{_bar(v["count"] / grand_count if grand_count else 0.0, "#17365d")}</td>'
            f'<td class="cr-num">{_fmt_amount(v["amount"])}</td>'
            f'<td>{_bar(v["amount"] / grand_amount if grand_amount else 0.0, "#8a2f2f")}</td></tr>')
    overall_rows.append(
        f'<tr class="cr-sub"><td class="cr-left">合计</td><td>{grand_count:,}</td><td>100.0%</td>'
        f'<td class="cr-num">{_fmt_amount(grand_amount)}</td><td>100.0%</td></tr>')

    dept_rows = []
    for dept, rows in ordered_depts:
        d_count = sum(r["count"] for r in rows)
        d_amount = sum(r["amount"] for r in rows)
        span = len(rows) + 1
        for i, r in enumerate(rows):
            dept_cell = (f'<td class="cr-dept" rowspan="{span}">{_esc(dept)}</td>' if i == 0 else "")
            dept_rows.append(
                f'<tr>{dept_cell}<td class="cr-left">{_esc(r["band"])}</td>'
                f'<td>{r["count"]:,}</td>'
                f'<td>{_bar(r["count"] / d_count if d_count else 0.0, "#17365d")}</td>'
                f'<td class="cr-num">{_fmt_amount(r["amount"])}</td>'
                f'<td>{_bar(r["amount"] / d_amount if d_amount else 0.0, "#8a2f2f")}</td></tr>')
        dept_rows.append(
            f'<tr class="cr-sub"><td class="cr-left">小计</td><td>{d_count:,}</td><td>100.0%</td>'
            f'<td class="cr-num">{_fmt_amount(d_amount)}</td><td>100.0%</td></tr>')

    top_rows = []
    for idx, p in enumerate(top_people, start=1):
        hot = p.get("95%以上", 0)
        other_cells = "".join(f'<td>{p.get(b, 0):,}</td>' for b in BANDS[1:])
        cls = ' class="cr-hot"' if hot else ""
        top_rows.append(
            f'<tr{cls}><td>{idx}</td>'
            f'<td class="cr-left">{_esc(p["person"])}</td>'
            f'<td class="cr-left">{_esc(p["department"])}</td>'
            f'<td>{p["count"]:,}</td><td class="cr-num">{_fmt_amount(p["amount"])}</td>'
            f'<td class="cr-hot-num">{hot:,}</td>{other_cells}</tr>')

    return {
        "DEPT_COL": _esc(dept_col),
        "NOTE": "有效住宿记录 = 消费类型为住宿且金额&gt;0、住宿天数&gt;0、住宿标准&gt;0；"
                "标准使用率 = 单晚住宿费(金额/住宿天数) ÷ 住宿标准；",
        "DEPT_COUNT": str(len(ordered_depts)),
        "TOP_N": str(len(top_people)),
        "GRAND_COUNT": f"{grand_count:,}",
        "GRAND_AMOUNT": _fmt_amount(grand_amount),
        "TOP95_SHARE": (f'{top95["count"] / grand_count * 100:.1f}% / '
                        f'{top95["amount"] / grand_amount * 100:.1f}%'
                        if grand_count and grand_amount else "-"),
        "CEIL90_COUNT": f"{ceil_count:,}",
        "CEIL90_COUNT_SHARE": f"{ceil_count / grand_count * 100:.1f}%" if grand_count else "-",
        "CEIL90_AMOUNT": _fmt_amount(ceil_amount),
        "CEIL90_AMOUNT_SHARE": f"{ceil_amount / grand_amount * 100:.1f}%" if grand_amount else "-",
        "OVERALL_ROWS": "".join(overall_rows),
        "DEPT_ROWS": "".join(dept_rows),
        "TOP50_ROWS": "".join(top_rows),
        "GENERATED_AT": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }




def _fmt_int(value) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "—"


def _pct_str(value) -> str:
    return "—" if value is None else f"{value * 100:.1f}%"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------------- agreement_ratio ----------------

def build_agreement(result: dict, config: dict) -> dict[str, str]:
    departments = result.get("departments", [])
    top = result.get("top_50_people", [])
    total = result.get("total", {})
    problems = []
    if round(sum(d["total_nights"] for d in departments), 2) != round(total.get("total_nights", 0), 2):
        problems.append("部门总间夜加总与总计不平")
    if round(sum(d["agreement_nights"] for d in departments), 2) != round(total.get("agreement_nights", 0), 2):
        problems.append("部门协议间夜加总与总计不平")
    for d in departments:
        if d["total_nights"] and d.get("agreement_share") is not None:
            if abs(d["agreement_share"] - d["agreement_nights"] / d["total_nights"]) > 1e-6:
                problems.append(f"部门 {d['department']} 协议占比复算不符")
    if len(top) > 50:
        problems.append(f"按人明细 {len(top)} 行超过 50")
    if problems:
        raise SystemExit("平衡校验失败(agreement_ratio): " + "; ".join(problems))

    dept_rows = []
    for d in departments:
        share = d.get("agreement_share") or 0
        dept_rows.append(
            f'<tr><td class="cr-left">{_esc(d["department"])}</td><td class="cr-num">{_fmt_int(d["total_nights"])}</td>'
            f'<td class="cr-num">{_fmt_int(d["agreement_nights"])}</td><td>{_bar(share, "#2f6fb2")}</td>'
            f'<td class="cr-num">{_fmt_amount(d["amount"])}</td></tr>')
    dept_rows.append(
        f'<tr class="cr-sub"><td class="cr-left">合计</td><td class="cr-num">{_fmt_int(total.get("total_nights"))}</td>'
        f'<td class="cr-num">{_fmt_int(total.get("agreement_nights"))}</td><td>{_bar(total.get("agreement_share") or 0, "#2f6fb2")}</td>'
        f'<td class="cr-num">{_fmt_amount(total.get("amount", 0))}</td></tr>')
    top_rows = []
    for i, p in enumerate(top, 1):
        share = p.get("agreement_share") or 0
        top_rows.append(
            f'<tr><td>{i}</td><td class="cr-left">{_esc(p["person"])}</td><td class="cr-left">{_esc(p["department"])}</td>'
            f'<td class="cr-num">{_fmt_int(p["total_nights"])}</td><td class="cr-num">{_fmt_int(p["agreement_nights"])}</td>'
            f'<td>{_bar(share, "#5aa469")}</td></tr>')
    return {
        "DEPT_COUNT": str(len(departments)),
        "TOTAL_NIGHTS": _fmt_int(total.get("total_nights")),
        "AGR_NIGHTS": _fmt_int(total.get("agreement_nights")),
        "AGR_SHARE": _pct_str(total.get("agreement_share")),
        "EXCLUDED_FEE": _fmt_int(result.get("excluded_missing_fee", 0)),
        "DEPT_ROWS": "".join(dept_rows),
        "TOP50_ROWS": "".join(top_rows),
        "NOTE": _esc(result.get("definition", "")),
        "GENERATED_AT": _now(),
    }


# ---------------- hotel_level ----------------

LEVEL_ORDER = ["豪华型", "高端型", "高档型", "舒适型", "经济型", "未指定"]


def build_hotel_level(result: dict, config: dict) -> dict[str, str]:
    rows = result.get("rows", [])
    if not rows:
        raise SystemExit("平衡校验失败(hotel_level): 无行数据")
    total_count = sum(r["count"] for r in rows)
    total_amount = sum(r["amount"] for r in rows)

    def level_key(level: str):
        return LEVEL_ORDER.index(level) if level in LEVEL_ORDER else 99

    depts: dict[str, list[dict]] = {}
    for r in rows:
        depts.setdefault(r["department"], []).append(r)
    ordered = sorted(depts.items(), key=lambda kv: (-sum(x["amount"] for x in kv[1]), kv[0]))
    dept_rows = []
    for dept, items in ordered:
        items = sorted(items, key=lambda v: level_key(v["hotel_level"]))
        d_count = sum(x["count"] for x in items)
        d_amount = sum(x["amount"] for x in items)
        for j, x in enumerate(items):
            share = (x["amount"] / total_amount) if total_amount else 0
            dept_cell = (f'<td class="cr-dept" rowspan="{len(items) + 1}">{_esc(dept)}</td>' if j == 0 else "")
            dept_rows.append(
                f'<tr>{dept_cell}<td class="cr-left">{_esc(x["hotel_level"])}</td>'
                f'<td class="cr-num">{_fmt_int(x["count"])}</td><td class="cr-num">{_fmt_amount(x["amount"])}</td>'
                f'<td>{_bar(share, "#2f6fb2")}</td></tr>')
        dept_rows.append(
            f'<tr class="cr-sub"><td class="cr-left">小计</td>'
            f'<td class="cr-num">{_fmt_int(d_count)}</td><td class="cr-num">{_fmt_amount(d_amount)}</td>'
            f'<td>{_bar((d_amount / total_amount) if total_amount else 0, "#8fa3b8")}</td></tr>')
    return {
        "DEPT_COUNT": str(len(depts)),
        "RECORD_COUNT": _fmt_int(total_count),
        "TOTAL_AMOUNT": _fmt_amount(total_amount),
        "LEVEL_COUNT": str(len({r["hotel_level"] for r in rows})),
        "DEPT_ROWS": "".join(dept_rows),
        "NOTE": "按“报账部门 × 酒店等级”统计记录数与金额；等级缺失记为“未指定”；占比为该单元格金额占全部记录金额之比",
        "GENERATED_AT": _now(),
    }


# ---------------- top_cities ----------------

def build_top_cities(result: dict, config: dict) -> dict[str, str]:
    rows = result.get("rows", [])
    total = result.get("total", {})
    problems = []
    if round(sum(r["nights"] for r in rows), 2) != round(total.get("nights", 0), 2):
        problems.append("城市间夜加总与总计不平")
    if round(sum(r["amount"] for r in rows), 2) != round(total.get("amount", 0), 2):
        problems.append("城市金额加总与总计不平")
    if len(rows) > 21:
        problems.append(f"城市行数 {len(rows)} 超过 21（前20+其他）")
    if problems:
        raise SystemExit("平衡校验失败(top_cities): " + "; ".join(problems))
    city_rows = []
    for i, r in enumerate(rows, 1):
        rank = str(i) if not r.get("is_other") else "—"
        cls = ' class="cr-sub"' if r.get("is_other") else ""
        city_rows.append(
            f'<tr{cls}><td>{rank}</td><td class="cr-left">{_esc(r["city"])}</td>'
            f'<td class="cr-num">{_fmt_int(r["nights"])}</td><td>{_bar(r.get("nights_share") or 0, "#2f6fb2")}</td>'
            f'<td class="cr-num">{_fmt_amount(r["amount"])}</td><td>{_bar(r.get("amount_share") or 0, "#e08a2e")}</td>'
            f'<td class="cr-num">{_fmt_amount(r.get("avg_rate") or 0)}</td><td class="cr-num">{_fmt_int(r["count"])}</td></tr>')
    avg_all = (total.get("amount", 0) / total["nights"]) if total.get("nights") else 0
    return {
        "CITY_COUNT": str(result.get("city_count", 0)),
        "TOTAL_NIGHTS": _fmt_int(total.get("nights")),
        "TOTAL_AMOUNT": _fmt_amount(total.get("amount", 0)),
        "AVG_RATE": _fmt_amount(avg_all),
        "CITY_ROWS": "".join(city_rows),
        "NOTE": _esc(result.get("note", "")),
        "GENERATED_AT": _now(),
    }


# ---------------- hotel_ranking ----------------

def build_hotel_ranking(result: dict, config: dict) -> dict[str, str]:
    rows = result.get("rows", [])
    by_city = result.get("hotel_count_by_city", [])
    problems = []
    if len(rows) > 20:
        problems.append(f"酒店行数 {len(rows)} 超过 20")
    if problems:
        raise SystemExit("平衡校验失败(hotel_ranking): " + "; ".join(problems))
    hotel_rows = []
    for i, r in enumerate(rows, 1):
        hotel_rows.append(
            f'<tr><td>{i}</td><td class="cr-left">{_esc(r["city"])}</td><td class="cr-left">{_esc(r["hotel"])}</td>'
            f'<td class="cr-num">{_fmt_int(r["nights"])}</td><td class="cr-num">{_fmt_amount(r["amount"])}</td>'
            f'<td class="cr-num">{_fmt_int(r["count"])}</td></tr>')
    city_rows = []
    for c in by_city:
        city_rows.append(
            f'<tr><td class="cr-left">{_esc(c["city"])}</td><td class="cr-num">{_fmt_int(c["nights"])}</td>'
            f'<td class="cr-num">{_fmt_int(c["hotel_count"])}</td></tr>')
    return {
        "TOP_CITY_N": str(result.get("top_city_n", 20)),
        "TOP_HOTEL_N": str(result.get("top_hotel_n", 20)),
        "CITY_COUNT": str(len(by_city)),
        "TOP20_NIGHTS": _fmt_int(sum(r["nights"] for r in rows)),
        "CITY_HOTEL_ROWS": "".join(city_rows),
        "HOTEL_ROWS": "".join(hotel_rows),
        "NOTE": _esc(result.get("note", "")),
        "GENERATED_AT": _now(),
    }


# ---------------- department_expenses ----------------

def build_department_expenses(result: dict, config: dict) -> dict[str, str]:
    rows = result.get("rows", [])
    total = result.get("total", {})
    problems = []
    if round(sum(r["hotel"] for r in rows), 2) != total.get("hotel", 0):
        problems.append("部门住宿金额加总与总计不平")
    if round(sum(r["flight"] for r in rows), 2) != total.get("flight", 0):
        problems.append("部门机票金额加总与总计不平")
    if round(sum(r["train"] for r in rows), 2) != total.get("train", 0):
        problems.append("部门火车金额加总与总计不平")
    if problems:
        raise SystemExit("平衡校验失败(department_expenses): " + "; ".join(problems))
    dept_rows = []
    for r in rows:
        dept_rows.append(
            f'<tr><td class="cr-left">{_esc(r["department"])}</td>'
            f'<td class="cr-num">{_fmt_amount(r["hotel"])}</td><td class="cr-num">{_fmt_amount(r["flight"])}</td>'
            f'<td class="cr-num">{_fmt_amount(r["train"])}</td><td class="cr-num"><b>{_fmt_amount(r["total"])}</b></td>'
            f'<td>{_bar(r.get("share") or 0, "#2f6fb2")}</td><td class="cr-num">{_fmt_int(r["count"])}</td></tr>')
    dept_rows.append(
        f'<tr class="cr-sub"><td class="cr-left">合计</td>'
        f'<td class="cr-num">{_fmt_amount(total.get("hotel", 0))}</td><td class="cr-num">{_fmt_amount(total.get("flight", 0))}</td>'
        f'<td class="cr-num">{_fmt_amount(total.get("train", 0))}</td><td class="cr-num">{_fmt_amount(total.get("grand", 0))}</td>'
        f'<td></td><td class="cr-num">{_fmt_int(total.get("count", 0))}</td></tr>')
    return {
        "DEPT_COUNT": str(len(rows)),
        "GRAND": _fmt_amount(total.get("grand", 0)),
        "HOTEL_TOTAL": _fmt_amount(total.get("hotel", 0)),
        "FLIGHT_TOTAL": _fmt_amount(total.get("flight", 0)),
        "TRAIN_TOTAL": _fmt_amount(total.get("train", 0)),
        "RECORD_COUNT": _fmt_int(total.get("count", 0)),
        "DEPT_ROWS": "".join(dept_rows),
        "NOTE": _esc(result.get("note", "")),
        "GENERATED_AT": _now(),
    }


# ---------------- monthly_trend ----------------

def _svg_trend(months: list[dict]) -> str:
    w, h, pad_l, pad_r, pad_t, pad_b = 860, 320, 78, 24, 30, 46
    n = len(months)
    if n == 0:
        return '<svg viewBox="0 0 860 320" xmlns="http://www.w3.org/2000/svg"><text x="430" y="160" text-anchor="middle" fill="#8a97a8">无月份数据</text></svg>'
    max_v = max([m["total"] for m in months] + [1])
    step = max_v / 4
    mag = 10 ** max(0, int(len(str(int(step))) - 1))
    step = max(1, int(round(step / mag)) * mag)
    top_v = step * 4
    if n == 1:
        xs = [pad_l + (w - pad_l - pad_r) / 2]
    else:
        xs = [pad_l + i * (w - pad_l - pad_r) / (n - 1) for i in range(n)]

    def y_of(v: float) -> float:
        return pad_t + (1 - v / top_v) * (h - pad_t - pad_b)

    for m in months:
        m["_ft"] = m["flight"] + m["train"]

    def line(key: str, color: str, width: float) -> str:
        pts = " ".join(f"{xs[i]:.1f},{y_of(m[key]):.1f}" for i, m in enumerate(months))
        return (f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="{width}" '
                f'stroke-linejoin="round" stroke-linecap="round"/>')

    dots = []
    for i, m in enumerate(months):
        dots.append(f'<circle cx="{xs[i]:.1f}" cy="{y_of(m["total"]):.1f}" r="3.2" fill="#17365d"/>')
        if m["hotel"]:
            dots.append(f'<circle cx="{xs[i]:.1f}" cy="{y_of(m["hotel"]):.1f}" r="2.4" fill="#2f6fb2"/>')
        if m["_ft"]:
            dots.append(f'<circle cx="{xs[i]:.1f}" cy="{y_of(m["_ft"]):.1f}" r="2.4" fill="#e08a2e"/>')
    grid = []
    for k in range(5):
        v = step * k
        gy = y_of(v)
        grid.append(f'<line x1="{pad_l}" y1="{gy:.1f}" x2="{w - pad_r}" y2="{gy:.1f}" stroke="#dde4ec" stroke-width="1"/>')
        grid.append(f'<text x="{pad_l - 8}" y="{gy + 4:.1f}" text-anchor="end" font-size="11" fill="#5a6b80">{v:,.0f}</text>')
    labels = [f'<text x="{xs[i]:.1f}" y="{h - pad_b + 18}" text-anchor="middle" font-size="11" fill="#5a6b80">{m["month"]}</text>'
              for i, m in enumerate(months)]
    legend = (
        f'<g font-size="12"><rect x="{pad_l}" y="6" width="12" height="12" fill="#17365d"/>'
        f'<text x="{pad_l + 17}" y="16" fill="#172033">合计</text>'
        f'<rect x="{pad_l + 70}" y="6" width="12" height="12" fill="#2f6fb2"/>'
        f'<text x="{pad_l + 87}" y="16" fill="#172033">住宿</text>'
        f'<rect x="{pad_l + 140}" y="6" width="12" height="12" fill="#e08a2e"/>'
        f'<text x="{pad_l + 157}" y="16" fill="#172033">机票/火车</text></g>')
    return (
        f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" class="mt-svg" role="img">'
        + "".join(grid) + legend
        + line("_ft", "#e08a2e", 1.8)
        + line("hotel", "#2f6fb2", 2.4)
        + line("total", "#17365d", 2.8)
        + "".join(dots)
        + f'<line x1="{pad_l}" y1="{y_of(0):.1f}" x2="{w - pad_r}" y2="{y_of(0):.1f}" stroke="#8a97a8" stroke-width="1.2"/>'
        + "".join(labels)
        + f'<text x="{w / 2}" y="{h - 4}" text-anchor="middle" font-size="12" fill="#5a6b80">金额单位：元</text>'
        + "</svg>")


def build_monthly_trend(result: dict, config: dict) -> dict[str, str]:
    months = result.get("months", [])
    total = result.get("total", {})
    problems = []
    if abs(sum(m["total"] for m in months) - total.get("grand", 0)) > 0.05:
        problems.append("月份合计加总与总计不平")
    for m in months:
        if abs((m["hotel"] + m["flight"] + m["train"]) - m["total"]) > 0.01:
            problems.append(f"月份 {m['month']} 分项加总 ≠ 合计")
    if problems:
        raise SystemExit("平衡校验失败(monthly_trend): " + "; ".join(problems))
    month_rows = []
    for m in months:
        month_rows.append(
            f'<tr><td class="cr-left">{m["month"]}</td><td class="cr-num">{_fmt_amount(m["hotel"])}</td>'
            f'<td class="cr-num">{_fmt_amount(m["flight"])}</td><td class="cr-num">{_fmt_amount(m["train"])}</td>'
            f'<td class="cr-num"><b>{_fmt_amount(m["total"])}</b></td></tr>')
    month_rows.append(
        f'<tr class="cr-sub"><td class="cr-left">合计</td><td class="cr-num">{_fmt_amount(total.get("hotel", 0))}</td>'
        f'<td class="cr-num">{_fmt_amount(total.get("flight", 0))}</td><td class="cr-num">{_fmt_amount(total.get("train", 0))}</td>'
        f'<td class="cr-num">{_fmt_amount(total.get("grand", 0))}</td></tr>')
    peak = max(months, key=lambda m: m["total"]) if months else None
    return {
        "MONTH_COUNT": str(len(months)),
        "GRAND": _fmt_amount(total.get("grand", 0)),
        "PEAK_MONTH": (peak["month"] + "（" + _fmt_amount(peak["total"]) + " 元）") if peak else "—",
        "MISSING": _fmt_int(result.get("missing_date_records", 0)),
        "SVG": _svg_trend(months),
        "MONTH_ROWS": "".join(month_rows),
        "NOTE": _esc(result.get("note", "")),
        "GENERATED_AT": _now(),
    }


# ---------------- hotel_price_spread ----------------

def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _amt(v) -> str:
    n = _num(v)
    return _fmt_amount(n) if n is not None else "—"


def _d10(v) -> str:
    s = str(v or "").strip()[:10]
    return _esc(s) if s else "—"


def _spread_full(v: dict) -> str:
    """单条订单的全部信息（record_info 全字段），用于最高/最低单晚明细行。"""
    return " / ".join([
        f"乘机人 {_esc(v.get('乘机人') or '—')}",
        f"部门 {_esc(v.get('报账部门') or '—')}",
        f"城市 {_esc(v.get('到达地') or '—')}",
        f"入住 {_d10(v.get('出发时间'))}→{_d10(v.get('到达时间'))}（{_fmt_int(v.get('住宿天数'))}晚）",
        f"预订 {_d10(v.get('预订时间'))}",
        f"实收实付 {_amt(v.get('实收实付'))}元（票面 {_amt(v.get('票面价'))} / 服务费 {_amt(v.get('服务费'))}）",
        f"住宿标准 {_amt(v.get('住宿标准'))}元/晚",
        f"订单 {_esc(v.get('订单号') or '—')}",
        f"记录 {_esc(str(v.get('消费记录唯一值') or '—')[:8])}",
        f"{_esc(v.get('退改签类型') or '—')}",
    ])


def build_hotel_spread(result: dict, config: dict) -> dict[str, str]:
    rows = result.get("rows", [])
    problems = []
    if len(rows) > 20:
        problems.append(f"酒店行数 {len(rows)} 超过 20")
    for r in rows:
        if abs((r["max"]["nightly"] - r["min"]["nightly"]) - r["spread"]) > 0.01:
            problems.append(f"酒店 {r['hotel']} 偏离度复算不符")
    if problems:
        raise SystemExit("平衡校验失败(hotel_price_spread): " + "; ".join(problems))
    hotel_rows = []
    for i, r in enumerate(rows, 1):
        hotel_rows.append(
            f'<tr><td>{i}</td><td class="cr-left">{_esc(r["hotel"])}</td><td class="cr-left">{_esc(r["city"])}</td>'
            f'<td class="cr-num">{_fmt_int(r["record_count"])}</td><td class="cr-num">{_fmt_int(r["total_nights"])}</td>'
            f'<td class="cr-num">{_fmt_amount(r.get("avg_rate") or 0)}</td>'
            f'<td class="cr-num cr-hot-num">{_fmt_amount(r["max"]["nightly"])}</td>'
            f'<td class="cr-num">{_fmt_amount(r["min"]["nightly"])}</td>'
            f'<td class="cr-num cr-hot-num">{_fmt_amount(r["spread"])}</td>'
            f'<td class="cr-num">{_pct_str(r.get("spread_ratio"))}</td></tr>'
            f'<tr class="mt-detail"><td></td><td class="cr-left" colspan="9">'
            f'<b style="color:#d93025">▲最高单晚 {_fmt_amount(r["max"]["nightly"])}元/晚</b>：{_spread_full(r["max"])}</td></tr>'
            f'<tr class="mt-detail"><td></td><td class="cr-left" colspan="9">'
            f'<b style="color:#1e8e3e">▼最低单晚 {_fmt_amount(r["min"]["nightly"])}元/晚</b>：{_spread_full(r["min"])}</td></tr>')
    return {
        "HOTEL_TOTAL": _fmt_int(result.get("hotel_total", 0)),
        "TOP_N": str(result.get("top_n", 20)),
        "MAX_SPREAD": _fmt_amount(rows[0]["spread"]) if rows else "—",
        "PAIR_COUNT": str(len(result.get("watch_pairs", []))),
        "HOTEL_ROWS": "".join(hotel_rows),
        "NOTE": _esc(result.get("note", "")),
        "GENERATED_AT": _now(),
    }


# ---------------- city_ten_day_high_price ----------------
TEN_DAY_HTML_LIMIT = 100


def build_city_ten_day(result: dict, config: dict) -> dict[str, str]:
    details = result.get("details", [])
    limit_all = int(config.get("comparison_max_details", 500))
    problems = []
    if len(details) > limit_all:
        problems.append(f"明细行数 {len(details)} 超过上限 {limit_all}")
    for d in details[:300]:
        ba, nr, ni = _num(d.get("batch_average")), _num(d.get("higher_rate")), _num(d.get("nightly"))
        if ba is None or ba <= 0 or nr is None or ni is None:
            problems.append("存在窗口均价/高出比例缺失的明细")
            break
        if abs(ni / ba - 1 - nr) > 0.005:
            problems.append(f"订单 {d['order'].get('订单号')} 高出比例复算不符")
            break
    if problems:
        raise SystemExit("平衡校验失败(city_ten_day_high_price): " + "; ".join(problems[:5]))
    rows_html = []
    for i, d in enumerate(details[:TEN_DAY_HTML_LIMIT], 1):
        o = d["order"]
        std = _num(o.get("住宿标准"))
        if std is None or std <= 0:
            badge = '<span style="color:#8a97a8">无标准</span>'
        elif d["nightly"] > std:
            badge = '<span style="color:#d93025;font-weight:600">超标</span>'
        else:
            badge = '<span style="color:#1e8e3e">达标</span>'
        rows_html.append(
            f'<tr><td>{i}</td><td class="cr-left">{_esc(d["city"])}</td><td class="cr-left">{_esc(o.get("服务商") or "—")}</td>'
            f'<td class="cr-left">{_esc(o.get("乘机人") or "—")} / {_esc(o.get("报账部门") or "—")}</td>'
            f'<td class="cr-left">{_esc(d["stay_date"])}</td><td class="cr-num">{_fmt_int(o.get("住宿天数"))}</td>'
            f'<td class="cr-num cr-hot-num">{_fmt_amount(d["nightly"])}</td>'
            f'<td class="cr-num">{_amt(o.get("实收实付"))}</td><td class="cr-num">{_amt(o.get("住宿标准"))}</td>'
            f'<td class="cr-left">{badge}</td>'
            f'<td class="cr-num">{_fmt_int(d["batch_count"])}</td><td class="cr-num">{_fmt_amount(d["batch_average"])}</td>'
            f'<td class="cr-num cr-hot-num">+{_fmt_amount(d["higher_by"])}（{_pct_str(d["higher_rate"])}）</td></tr>'
            f'<tr class="mt-detail"><td></td><td class="cr-left" colspan="13">'
            f'预订 {_d10(o.get("预订时间"))} / 离店 {_d10(o.get("到达时间"))} / '
            f'订单 {_esc(o.get("订单号") or "—")} / 记录 {_esc(str(o.get("消费记录唯一值") or "—")[:8])} / '
            f'票面 {_amt(o.get("票面价"))} / 服务费 {_amt(o.get("服务费"))} / '
            f'{_esc(o.get("退改签类型") or "—")}</td></tr>')
    definition = (f"口径：同一城市内、入住日（出发时间）距当前订单 {result.get('window_days', 10)} 天以内"
                  f"（含当前订单，窗口至少2笔）的订单构成一个窗口；当前订单单晚价（实收实付÷住宿天数）"
                  f"＞窗口内平均单晚价×{result.get('threshold_ratio', 1.0)} 即判定为偏高，按高出比例降序展示")
    return {
        "MATCHED": _fmt_int(result.get("matched_count", 0)),
        "SHOW_COUNT": str(min(TEN_DAY_HTML_LIMIT, len(details))),
        "WINDOW_DAYS": str(result.get("window_days", 10)),
        "DETAIL_ROWS": "".join(rows_html),
        "DEFINITION": _esc(definition),
        "GENERATED_AT": _now(),
    }


# ---------------- cancel_rebook_gap ----------------

def build_cancel_rebook(result: dict, config: dict) -> dict[str, str]:
    details = result.get("details", [])
    problems = []
    if len(details) > int(config.get("comparison_max_details", 500)):
        problems.append("明细行数超过上限")
    if problems:
        raise SystemExit("平衡校验失败(cancel_rebook_gap): " + "; ".join(problems))
    detail_rows = []
    for d in details:
        c, nw = d["cancelled"], d["new"]
        gap = "同日" if d["same_day"] else f'{d["gap_days"]}天'
        detail_rows.append(
            f'<tr><td class="cr-left">{_esc(d["person"])}</td><td class="cr-left">{_esc(d["department"])}</td>'
            f'<td class="cr-left">{_esc(d["city"])}</td><td class="cr-left">{_esc(d["stay_date"])}</td>'
            f'<td class="cr-left">{_esc(c["booking_date"])} 订 {_esc(c["order"])}（{c["nights"]}晚 / '
            f'{_fmt_amount(c["total"])} / 单晚{_fmt_amount(c["nightly"])}）</td>'
            f'<td class="cr-left">{_esc(nw["booking_date"])} 重订 {_esc(nw["order"])}（{nw["nights"]}晚 / '
            f'{_fmt_amount(nw["total"])} / 单晚{_fmt_amount(nw["nightly"])}）</td>'
            f'<td class="cr-num">{gap}</td>'
            f'<td class="cr-num cr-hot-num">{d["direction"]} {_fmt_amount(abs(d["diff"]))}</td></tr>')
    return {
        "MATCHED": _fmt_int(result.get("matched_count", 0)),
        "SAME_DAY": _fmt_int(result.get("same_day_count", 0)),
        "UP_COUNT": _fmt_int(result.get("up_count", 0)),
        "DOWN_COUNT": _fmt_int(result.get("down_count", 0)),
        "EXCLUDED": _fmt_int(result.get("excluded_no_nights", 0)),
        "DETAIL_ROWS": "".join(detail_rows),
        "DEFINITION": _esc(result.get("definition", "")),
        "GENERATED_AT": _now(),
    }


# ---------------- watch_persons ----------------

def build_watch_persons(result: dict, config: dict) -> dict[str, str]:
    persons = result.get("persons", [])
    pairs = result.get("pairs", [])
    problems = []
    if len(pairs) != sum(len(p["hotels"]) for p in persons):
        problems.append("人员酒店数加总与组合数不平")
    if problems:
        raise SystemExit("平衡校验失败(watch_persons): " + "; ".join(problems))
    person_rows = []
    for i, p in enumerate(persons, 1):
        person_rows.append(
            f'<tr><td>{i}</td><td class="cr-left">{_esc(p["person"])}</td>'
            f'<td class="cr-num">{_fmt_int(p["hotel_count"])}</td>'
            f'<td class="cr-left">{_esc("、".join(p["hotels"][:6]))}{"…" if len(p["hotels"]) > 6 else ""}</td>'
            f'<td class="cr-left">{_esc("、".join(p["tables"]))}</td></tr>')
    pair_rows = []
    for p in pairs:
        pair_rows.append(
            f'<tr><td class="cr-left">{_esc(p["person"])}</td><td class="cr-left">{_esc(p["hotel"])}</td>'
            f'<td class="cr-num">{p["table_count"]}</td><td class="cr-left">{_esc("、".join(p["tables"]))}</td></tr>')
    tables = result.get("tables", {})
    sizes = result.get("set_sizes", {})
    set_sizes = "、".join(f"{label} {sizes.get(key, 0)}组" for key, label in tables.items())
    return {
        "PERSON_COUNT": _fmt_int(result.get("person_count", 0)),
        "PAIR_COUNT": _fmt_int(result.get("pair_count", 0)),
        "THRESHOLD": str(result.get("threshold", 3)),
        "SET_SIZES": _esc(set_sizes),
        "PERSON_ROWS": "".join(person_rows),
        "PAIR_ROWS": "".join(pair_rows),
        "DEFINITION": _esc(result.get("definition", "")),
        "GENERATED_AT": _now(),
    }


# ---------------- price_deviation ----------------


def _deviation_cells(d: dict) -> str:
    amt = d["deviation_amount"]
    amt_color = "#8a2f2f" if amt > 0 else ("#2f6fb2" if amt < 0 else "#555")
    amt_cell = (f'<td class="cr-num" style="color:{amt_color}">'
                f'{"+" if amt > 0 else ""}{_fmt_amount(amt)}</td>')
    rate = d.get("deviation_rate")
    if rate is None:
        rate_cell = '<td class="cr-num">—</td>'
    else:
        color = "#8a2f2f" if rate > 0 else ("#2f6fb2" if rate < 0 else "#555")
        rate_cell = (f'<td class="cr-num" style="color:{color};font-weight:bold">'
                     f'{"+" if rate > 0 else ""}{rate * 100:.1f}%</td>')
    return amt_cell + rate_cell


def build_price_deviation(result: dict, config: dict) -> dict[str, str]:
    overall = result.get("overall_average_nightly", 0.0) or 0.0
    depts = result.get("departments", [])
    people = result.get("top_50_people", [])
    pairs = result.get("watch_pairs", [])

    dept_rows = "".join(
        f'<tr><td>{i}</td><td class="cr-left">{_esc(d["name"])}</td>'
        f'<td class="cr-num">{_fmt_int(d["count"])}</td>'
        f'<td class="cr-num">{_fmt_amount(d["average_nightly"])}</td>'
        f'{_deviation_cells(d)}</tr>'
        for i, d in enumerate(depts, 1))

    person_rows = "".join(
        f'<tr><td>{i}</td><td class="cr-left">{_esc(p["name"])}</td>'
        f'<td class="cr-left">{_esc(p.get("department") or "—")}</td>'
        f'<td class="cr-num">{_fmt_int(p["count"])}</td>'
        f'<td class="cr-num">{_fmt_amount(p["average_nightly"])}</td>'
        f'{_deviation_cells(p)}</tr>'
        for i, p in enumerate(people, 1))

    person_hotels: dict[str, list[str]] = {}
    for person, hotel in pairs:
        person_hotels.setdefault(person, []).append(hotel)
    top_ph = sorted(person_hotels.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:20]
    ph_rows = "".join(
        f'<tr><td>{i}</td><td class="cr-left">{_esc(person)}</td>'
        f'<td class="cr-num">{len(hotels)}</td>'
        f'<td class="cr-left">{"、".join(_esc(h) for h in hotels[:5])}'
        f'{"…" if len(hotels) > 5 else ""}</td></tr>'
        for i, (person, hotels) in enumerate(top_ph, 1))

    unique_hotels = {h for _, h in pairs}
    return {
        "OVERALL_NIGHTLY": _fmt_amount(overall),
        "DEPT_COUNT": str(len(depts)),
        "PERSON_COUNT": str(len(people)),
        "DEPT_ROWS": dept_rows,
        "PERSON_ROWS": person_rows,
        "PH_ROWS": ph_rows,
        "PAIR_TOTAL": _fmt_int(len(pairs)),
        "HOTEL_UNIQUE": _fmt_int(len(unique_hotels)),
        "NOTE": "有效记录 = 住宿消费且金额&gt;0、住宿天数&gt;0；每间夜价 = 金额（按配置优先取实收实付）÷ 住宿天数；"
                "偏离 = 对象平均每间夜价 − 总体平均每间夜价（正值为高于总体、负值为低于总体），按偏离幅度降序。"
                "关注交叉名单为 Top50 人员与其使用酒店的“人员 × 酒店”组合集合，供关注人员交叉分析引用。",
        "GENERATED_AT": _now(),
    }


# ---------------- advance_no_service_fee ----------------


def build_advance_no_service_fee(result: dict, config: dict) -> dict[str, str]:
    buckets = result.get("buckets", [])
    total_count = sum(b["count"] for b in buckets)
    total_amount = sum(b["amount"] for b in buckets)
    rows = "".join(
        f'<tr><td class="cr-left">{_esc(b["lead_time"])}</td>'
        f'<td class="cr-num">{_fmt_int(b["count"])}</td>'
        f'<td>{_bar(b["count"] / total_count if total_count else 0.0, "#2f6fb2")}</td>'
        f'<td class="cr-num">{_fmt_amount(b["amount"])}</td>'
        f'<td>{_bar(b["amount"] / total_amount if total_amount else 0.0, "#8a2f2f")}</td></tr>'
        for b in buckets)
    return {
        "RULE": _esc(result.get("agreement_rule", "")),
        "TOTAL_COUNT": _fmt_int(total_count),
        "TOTAL_AMOUNT": _fmt_amount(total_amount),
        "BUCKET_ROWS": rows,
        "NOTE": "本章节仅统计非协议酒店订单（服务费=0）且金额&gt;0、预订时间与出发时间齐全的记录；"
                "提前窗口 = 出发时间（入住）日期 − 预订时间日期，“当天预订”即入住日当天才预订，"
                "“日期异常”为出发早于预订的脏数据。当天/提前1天的占比越高，说明非协议酒店预订越不提前，"
                "价格与合规风险越高。",
        "GENERATED_AT": _now(),
    }


BUILDERS = {
    "ceiling_reimbursement": build_ceiling,
    "agreement_ratio": build_agreement,
    "hotel_level": build_hotel_level,
    "top_cities": build_top_cities,
    "hotel_ranking": build_hotel_ranking,
    "department_expenses": build_department_expenses,
    "monthly_trend": build_monthly_trend,
    "hotel_price_spread": build_hotel_spread,
    "city_ten_day_high_price": build_city_ten_day,
    "cancel_rebook_gap": build_cancel_rebook,
    "watch_persons": build_watch_persons,
    "price_deviation": build_price_deviation,
    "advance_no_service_fee": build_advance_no_service_fee,
}
TEMPLATE_FILES = {
    "ceiling_reimbursement": "ceiling_reimbursement.html",
    "agreement_ratio": "agreement_ratio.html",
    "hotel_level": "hotel_level.html",
    "top_cities": "top_cities.html",
    "hotel_ranking": "hotel_ranking.html",
    "department_expenses": "department_expenses.html",
    "monthly_trend": "monthly_trend.html",
    "hotel_price_spread": "hotel_price_spread.html",
    "city_ten_day_high_price": "city_ten_day_high_price.html",
    "cancel_rebook_gap": "cancel_rebook_gap.html",
    "watch_persons": "watch_persons.html",
    "price_deviation": "price_deviation.html",
    "advance_no_service_fee": "advance_no_service_fee.html",
}


def extract_main(report_text: str) -> str:
    """从旧版（无外壳）或新版（外壳）报告中提取主报告正文，并移除已渲染的扩展章节。"""
    text = report_text.lstrip()
    m = re.match(r"^<!doctype\s+html>.*?<body[^>]*>(.*)</body>\s*</html>\s*$",
                 text, flags=re.S | re.I)
    if m:
        body = m.group(1)
    else:
        body = re.sub(r"^<!doctype\s+html>", "", text, flags=re.I)
        body = re.sub(r"<meta[^>]*>", "", body, flags=re.I)
        body = re.sub(r"<title>.*?</title>", "", body, flags=re.S | re.I)
        body = re.sub(r"<style>.*?</style>", "", body, count=1, flags=re.S | re.I)
    body = re.sub(r'<section class="cr-section".*?</section>\s*', "", body, flags=re.S)
    return body.strip()


def render(output_dir: Path, config: dict, templates_dir: Path,
           report_path: Path, ext_path: Path) -> None:
    if not report_path.exists():
        raise SystemExit(f"未找到 {report_path}，请先运行 analyze_expenses.py analyze。")
    if not ext_path.exists():
        raise SystemExit(f"未找到 {ext_path}，请先运行 run_extensions.py。")
    shell_path = templates_dir / SHELL_NAME
    if not shell_path.exists():
        raise SystemExit(f"未找到外壳模板 {shell_path}。")

    ext = json.loads(ext_path.read_text(encoding="utf-8"))
    results = ext.get("results", {})
    errors = ext.get("errors", {})
    if errors:
        raise SystemExit("扩展分析存在错误模块，先处理再渲染: " + json.dumps(errors, ensure_ascii=False))

    main = extract_main(report_path.read_text(encoding="utf-8"))
    sections = []
    for name in config.get("enabled_modules", []):
        if name not in results or name not in BUILDERS:
            continue
        template = (templates_dir / TEMPLATE_FILES[name]).read_text(encoding="utf-8")
        placeholders = BUILDERS[name](results[name], config)
        for key, value in placeholders.items():
            template = template.replace("{{" + key + "}}", value)
        sections.append((name, template))
        print(f"已渲染模块章节: {name}")

    if not sections:
        print("没有可渲染的模块章节（检查“启用分析模块”与 templates/）。", file=sys.stderr)
        sys.exit(2)

    shell = shell_path.read_text(encoding="utf-8")
    doc = shell.replace("{{MAIN_REPORT}}", main)
    for _name, section in sections:
        doc = doc.replace("</body>", f"{section}\n</body>")
    report_path.write_text(doc, encoding="utf-8")
    print(f"报告已生成: {report_path} （扩展章节 {len(sections)} 个）")


def main() -> None:
    parser = argparse.ArgumentParser(description="将扩展分析模块结果渲染进 HTML 报告（纯 HTML/CSS）。")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--config", default=str(PROJECT_ROOT / "config" / "config.json"))
    parser.add_argument("--report", default=None)
    parser.add_argument("--extensions", default=None)
    parser.add_argument("--templates", default=str(PROJECT_ROOT / "templates"))
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    config = load_config(args.config)
    render(out_dir, config, Path(args.templates),
           Path(args.report) if args.report else out_dir / REPORT_NAME,
           Path(args.extensions) if args.extensions else out_dir / "extension_analysis.json")


if __name__ == "__main__":
    main()

