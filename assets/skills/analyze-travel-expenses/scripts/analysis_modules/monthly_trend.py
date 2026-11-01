"""8. 每月出差费用曲线：按月汇总住宿/机票/火车票实收实付净额。

月份取数优先级：出发时间 > 预订时间 > 报销完成日期（与 config.date_precedence 一致）。
金额含退改负数冲销；输出供渲染层生成纯 SVG 曲线图。
"""
from __future__ import annotations

from collections import defaultdict

from .common import dt, num

MODULE_NAME = "monthly_trend"
RECORD_TYPES = ("flight",)
TYPE_MAP = {"住宿": "hotel", "机票": "flight", "火车票": "train"}


def _month_key(value):
    d = dt(value)
    return f"{d.year:04d}-{d.month:02d}" if d else None


def analyze(records, config):
    date_fields = config.get("date_precedence") or ["出发时间", "预订时间", "报销完成日期"]
    per = defaultdict(lambda: {"hotel": 0.0, "flight": 0.0, "train": 0.0})
    source = records if isinstance(records, dict) else {"hotel": records}
    all_rows = list(source.get("hotel", [])) + list(source.get("flight", []))
    missing = 0
    for r in all_rows:
        key = TYPE_MAP.get(str(r.get("消费类型") or "").strip())
        a = num(r.get("实收实付"))
        if key is None or a is None:
            continue
        mk = None
        for f in date_fields:
            mk = _month_key(r.get(f))
            if mk:
                break
        if mk is None:
            missing += 1
            continue
        per[mk][key] += a
    months = []
    for mk in sorted(per):
        v = per[mk]
        g = v["hotel"] + v["flight"] + v["train"]
        months.append({"month": mk, "hotel": round(v["hotel"], 2), "flight": round(v["flight"], 2),
                       "train": round(v["train"], 2), "total": round(g, 2)})
    total = {"hotel": 0.0, "flight": 0.0, "train": 0.0}
    for m in months:
        total["hotel"] += m["hotel"]
        total["flight"] += m["flight"]
        total["train"] += m["train"]
    total = {k: round(v, 2) for k, v in total.items()}
    total["grand"] = round(total["hotel"] + total["flight"] + total["train"], 2)
    return {"months": months, "total": total, "missing_date_records": missing,
            "date_precedence": date_fields,
            "note": "月份按 出发时间>预订时间>报销完成日期 取数；金额含退改负数冲销的净额"}
