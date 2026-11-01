#!/usr/bin/env python3
"""Stream, merge, validate and report exported travel-expense tables."""
from __future__ import annotations

import argparse
import csv
import html
import json
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from config_loader import load_config

SUPPORTED = {".xlsx", ".csv", ".tsv"}
GENERATED = {"财务分析报告.xlsx", "analysis.xlsx"}

# 报告展示字段的中文标签（HTML 表头/概览卡片与 Excel 表头共用）
LABELS = {
    "file_count": "文件数量",
    "raw_rows": "原始行数",
    "accepted_rows": "有效行数",
    "net_amount": "净额",
    "absolute_amount": "绝对金额",
    "negative_rows": "负金额行数",
    "currency": "货币",
    "amount_sources": "金额字段来源",
    "name": "名称",
    "count": "记录数",
    "status": "校验状态",
    "duplicate_keys_removed": "去重删除行数",
    "empty_unique_keys": "空唯一键行数",
    "missing_expected_fields": "缺失字段",
    "balance_differences": "金额平衡差异",
    "refund_sign_preserved": "退款符号保留",
}
STATUS_LABELS = {"pass": "通过", "warning": "警告"}
CURRENCY_LABELS = {"CNY": "人民币", "USD": "美元", "EUR": "欧元", "JPY": "日元"}


def clean_header(value: Any) -> str:
    return " ".join(str(value or "").replace("\u3000", " ").split())


def number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    text = str(value).strip().replace(",", "").replace("￥", "").replace("¥", "")
    if text.endswith("%"):
        text = text[:-1]
        try:
            return float(text) / 100
        except ValueError:
            return None
    try:
        return float(text)
    except ValueError:
        return None


def text(value: Any, default: str = "未提供") -> str:
    value = clean_header(value)
    return value or default


def month(value: Any) -> str:
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m")
    if value:
        raw = str(value).strip().replace("/", "-")
        if len(raw) >= 7 and raw[4] == "-":
            return raw[:7]
    return "日期缺失"


def files_under(path: Path) -> list[Path]:
    candidates = [path] if path.is_file() else sorted(path.rglob("*"))
    return [p for p in candidates if p.is_file() and p.suffix.lower() in SUPPORTED
            and not p.name.startswith("~$") and p.name not in GENERATED]


def rows_from_file(path: Path) -> Iterable[tuple[str, list[str], Iterable[tuple[Any, ...]]]]:
    if path.suffix.lower() == ".xlsx":
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        try:
            for ws in wb.worksheets:
                iterator = ws.iter_rows(values_only=True)
                first = next(iterator, None)
                if first:
                    yield ws.title, [clean_header(v) for v in first], iterator
        finally:
            wb.close()
    else:
        delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
        handle = path.open("r", encoding="utf-8-sig", newline="")
        reader = csv.reader(handle, delimiter=delimiter)
        first = next(reader, None)
        if first:
            yield path.stem, [clean_header(v) for v in first], reader
        handle.close()


def inspect(input_path: Path) -> dict[str, Any]:
    result = {"files": [], "file_count": 0}
    for path in files_under(input_path):
        item = {"path": str(path), "size_bytes": path.stat().st_size, "sheets": []}
        for sheet, headers, rows in rows_from_file(path):
            count = sum(1 for _ in rows)
            item["sheets"].append({"name": sheet, "rows": count, "columns": len(headers), "headers": headers})
        result["files"].append(item)
    result["file_count"] = len(result["files"])
    return result


def add(group: dict[str, dict[str, float]], key: str, amount: float) -> None:
    bucket = group.setdefault(key, {"count": 0, "net_amount": 0.0, "absolute_amount": 0.0})
    bucket["count"] += 1
    bucket["net_amount"] += amount
    bucket["absolute_amount"] += abs(amount)


def rounded_group(group: dict[str, dict[str, float]]) -> list[dict[str, Any]]:
    rows = []
    for key, value in group.items():
        rows.append({"name": key, "count": int(value["count"]),
                     "net_amount": round(value["net_amount"], 2),
                     "absolute_amount": round(value["absolute_amount"], 2)})
    return sorted(rows, key=lambda x: (-abs(x["net_amount"]), x["name"]))


def choose(row: dict[str, Any], names: list[str]) -> tuple[str | None, Any]:
    for name in names:
        if name in row and row[name] not in (None, ""):
            return name, row[name]
    return None, None


def analyze(input_path: Path, config: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    by_type, by_dept, by_month = {}, {}, {}
    people, routes = {}, {}
    discounts: dict[str, int] = defaultdict(int)
    hotel: dict[str, dict[str, float]] = defaultdict(lambda: {"count": 0, "net_amount": 0.0})
    statuses: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    seen: set[str] = set()
    raw_rows = accepted = duplicate = empty_key = negative = 0
    amount_sources: dict[str, int] = defaultdict(int)
    field_sets: list[set[str]] = []
    files = files_under(input_path)

    for path in files:
        for _sheet, headers, rows in rows_from_file(path):
            field_sets.append(set(headers))
            for values in rows:
                if not any(v not in (None, "") for v in values):
                    continue
                raw_rows += 1
                row = {headers[i]: values[i] if i < len(values) else None for i in range(len(headers)) if headers[i]}
                _, key_value = choose(row, config["unique_key_candidates"])
                key = text(key_value, "")
                if key:
                    if config.get("deduplicate", True) and key in seen:
                        duplicate += 1
                        continue
                    seen.add(key)
                else:
                    empty_key += 1
                amount_field, amount_value = choose(row, config["amount_precedence"])
                amount = number(amount_value)
                if amount is None:
                    amount = 0.0
                    amount_field = "金额缺失"
                amount_sources[amount_field or "金额缺失"] += 1
                if amount < 0:
                    negative += 1
                accepted += 1

                kind = text(row.get("消费类型"))
                dept = text(row.get("报账部门"))
                person = text(row.get("乘机人"))
                _, date_value = choose(row, config["date_precedence"])
                add(by_type, kind, amount)
                add(by_dept, dept, amount)
                add(by_month, month(date_value), amount)
                add(people, f"{person}｜{dept}", amount)

                if kind in {"机票", "火车票"}:
                    route = f"{text(row.get('出发地'))} → {text(row.get('到达地'))}"
                    add(routes, route, amount)
                    rate = number(row.get("折扣率(%)"))
                    if rate is None or rate == 0:
                        discounts["未提供"] += 1
                    elif rate < config["discount_bands"][0]:
                        discounts["4折以下"] += 1
                    elif rate < config["discount_bands"][1]:
                        discounts["4-8折"] += 1
                    else:
                        discounts["8折以上"] += 1

                if kind == "住宿":
                    nights, standard = number(row.get("住宿天数")), number(row.get("住宿标准"))
                    if amount > 0 and nights and nights > 0 and standard and standard > 0:
                        ratio = amount / nights / standard
                        bounds = config["hotel_ratio_bands"]
                        label = ("70%以下" if ratio < bounds[0] else "70%-80%" if ratio < bounds[1]
                                 else "80%-90%" if ratio < bounds[2] else "90%-95%" if ratio < bounds[3]
                                 else "95%以上")
                    else:
                        label = "不可计算"
                    hotel[label]["count"] += 1
                    hotel[label]["net_amount"] += amount

                for status in ("报销状态", "对账状态", "是否清账", "明细状态"):
                    statuses[status][text(row.get(status))] += 1

    overall = sum(v["net_amount"] for v in by_type.values())
    def balance(group: dict[str, dict[str, float]]) -> float:
        return round(sum(v["net_amount"] for v in group.values()) - overall, 2)
    all_fields = set().union(*field_sets) if field_sets else set()
    missing = [f for f in ["消费类型", "报账部门", *config["amount_precedence"]]
               if f not in all_fields]
    analysis = {
        "overview": {"file_count": len(files), "raw_rows": raw_rows, "accepted_rows": accepted,
                     "net_amount": round(overall, 2),
                     "absolute_amount": round(sum(v["absolute_amount"] for v in by_type.values()), 2),
                     "negative_rows": negative, "currency": config.get("currency", "CNY"),
                     "amount_sources": dict(amount_sources)},
        "by_type": rounded_group(by_type), "by_department": rounded_group(by_dept),
        "by_month": rounded_group(by_month),
        "top_people": rounded_group(people)[: int(config.get("top_n", 50))],
        "top_routes": rounded_group(routes)[: int(config.get("top_n", 50))],
        "hotel_compliance": [{"name": k, "count": int(v["count"]), "net_amount": round(v["net_amount"], 2)}
                             for k, v in sorted(hotel.items())],
        "discount_distribution": dict(sorted(discounts.items())),
        "status_distribution": {k: dict(sorted(v.items())) for k, v in statuses.items()},
    }
    validation = {
        "status": "pass" if not missing and all(abs(balance(g)) <= 0.01 for g in (by_type, by_dept, by_month)) else "warning",
        "file_count": len(files), "raw_rows": raw_rows, "accepted_rows": accepted,
        "duplicate_keys_removed": duplicate, "empty_unique_keys": empty_key,
        "missing_expected_fields": missing,
        "balance_differences": {"by_type": balance(by_type), "by_department": balance(by_dept), "by_month": balance(by_month)},
        "refund_sign_preserved": True,
    }
    return analysis, validation


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def write_html(path: Path, analysis: dict[str, Any], validation: dict[str, Any]) -> None:
    def table(title: str, rows: list[dict[str, Any]], name_label: str = "名称") -> str:
        if not rows:
            return f"<h2>{html.escape(title)}</h2><p>无数据</p>"
        cols = list(rows[0])
        def header(c: str) -> str:
            return name_label if c == "name" else LABELS.get(c, c)
        head = "".join(f"<th>{html.escape(header(c))}</th>" for c in cols)
        body = "".join("<tr>" + "".join(f"<td>{html.escape(str(r.get(c, '')))}</td>" for c in cols) + "</tr>" for r in rows)
        return f"<h2>{html.escape(title)}</h2><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"
    ov = analysis["overview"]
    cards = "".join(f"<div><b>{html.escape(LABELS.get(k, k))}</b><span>{html.escape(str(CURRENCY_LABELS.get(v, v) if k == 'currency' else v))}</span></div>" for k, v in ov.items() if not isinstance(v, dict))
    sections = "".join([table("按消费类型", analysis["by_type"], "消费类型"), table("按部门", analysis["by_department"], "部门"),
                        table("按月份", analysis["by_month"], "月份"), table("人员 Top", analysis["top_people"], "人员"),
                        table("路线 Top", analysis["top_routes"], "路线"), table("住宿标准使用率", analysis["hotel_compliance"], "住宿标准")])
    doc = f"""<!doctype html><meta charset='utf-8'><title>财务分析报告</title><style>body{{font:14px system-ui;margin:32px;color:#172033}}h1{{color:#17365d}}.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}}.cards div{{background:#edf3f8;padding:14px;border-radius:8px}}.cards span{{display:block;font-size:20px;margin-top:6px}}table{{border-collapse:collapse;width:100%;margin-bottom:28px}}th,td{{border:1px solid #ccd5df;padding:7px;text-align:right}}th:first-child,td:first-child{{text-align:left}}th{{background:#17365d;color:white}}</style><h1>差旅消费综合分析</h1><p>校验状态：{STATUS_LABELS.get(validation['status'], validation['status'])}</p><div class='cards'>{cards}</div>{sections}"""
    path.write_text(doc, encoding="utf-8")


def write_xlsx(path: Path, analysis: dict[str, Any], validation: dict[str, Any]) -> None:
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    datasets = [("概览", [analysis["overview"]]), ("消费类型", analysis["by_type"]),
                ("部门", analysis["by_department"]), ("月份", analysis["by_month"]),
                ("人员Top", analysis["top_people"]), ("路线Top", analysis["top_routes"]),
                ("住宿合规", analysis["hotel_compliance"]), ("校验", [validation])]
    for name, rows in datasets:
        ws = wb.create_sheet(name[:31])
        if not rows:
            ws.append(["无数据"]); continue
        flat_rows = [{k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v for k, v in r.items()} for r in rows]
        for r in flat_rows:
            if isinstance(r.get("status"), str) and r["status"] in STATUS_LABELS:
                r["status"] = STATUS_LABELS[r["status"]]
            if isinstance(r.get("currency"), str) and r["currency"] in CURRENCY_LABELS:
                r["currency"] = CURRENCY_LABELS[r["currency"]]
        raw_headers = list(flat_rows[0])
        headers = [LABELS.get(h, h) for h in raw_headers]
        ws.append(headers)
        for cell in ws[1]:
            cell.fill = PatternFill("solid", fgColor="17365D"); cell.font = Font(color="FFFFFF", bold=True)
            cell.alignment = Alignment(horizontal="center")
        for row in flat_rows:
            ws.append([row.get(h, "") for h in raw_headers])
        ws.freeze_panes = "A2"; ws.auto_filter.ref = ws.dimensions
        for col in ws.columns:
            letter = col[0].column_letter
            ws.column_dimensions[letter].width = min(45, max(12, max(len(str(c.value or "")) for c in col) + 2))
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    pi = sub.add_parser("inspect"); pi.add_argument("--input", required=True); pi.add_argument("--output", required=True)
    pa = sub.add_parser("analyze"); pa.add_argument("--input", required=True); pa.add_argument("--output-dir", required=True)
    pa.add_argument("--config", default=str(Path(__file__).parents[1] / "config" / "config.json"))
    args = parser.parse_args()
    if args.command == "inspect":
        write_json(Path(args.output), inspect(Path(args.input)))
        return
    config = load_config(args.config)
    analysis, validation = analyze(Path(args.input), config)
    out = Path(args.output_dir); out.mkdir(parents=True, exist_ok=True)
    write_json(out / "analysis.json", analysis); write_json(out / "validation.json", validation)
    write_html(out / "财务分析报告.html", analysis, validation)
    write_xlsx(out / "财务分析报告.xlsx", analysis, validation)
    print(json.dumps({"output_dir": str(out), "validation": validation["status"], **analysis["overview"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
