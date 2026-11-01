"""7. 部门发生费用统计：按报账部门汇总住宿/机票/火车票实收实付。

金额取“实收实付”（含退改负数冲销后的净额）；机票=消费类型为机票，火车=消费类型为火车票。
"""
from __future__ import annotations

from collections import defaultdict

from .common import num, txt

MODULE_NAME = "department_expenses"
RECORD_TYPES = ("flight",)
TYPE_MAP = {"住宿": "hotel", "机票": "flight", "火车票": "train"}


def analyze(records, config):
    dept_col = config.get("department_column") or "报账部门"
    per = defaultdict(lambda: {"hotel": 0.0, "flight": 0.0, "train": 0.0, "count": 0})
    total = {"hotel": 0.0, "flight": 0.0, "train": 0.0, "count": 0}
    source = records if isinstance(records, dict) else {"hotel": records}
    all_rows = list(source.get("hotel", [])) + list(source.get("flight", []))
    skipped = 0
    for r in all_rows:
        key = TYPE_MAP.get(str(r.get("消费类型") or "").strip())
        a = num(r.get("实收实付"))
        if key is None or a is None:
            skipped += 1
            continue
        d = txt(r.get(dept_col))
        per[d][key] += a
        per[d]["count"] += 1
        total[key] += a
        total["count"] += 1
    grand = total["hotel"] + total["flight"] + total["train"]
    rows = []
    for d, v in per.items():
        g = v["hotel"] + v["flight"] + v["train"]
        rows.append({"department": d, "hotel": round(v["hotel"], 2), "flight": round(v["flight"], 2),
                     "train": round(v["train"], 2), "total": round(g, 2),
                     "share": (g / grand) if grand else None, "count": v["count"]})
    rows.sort(key=lambda x: (-x["total"], x["department"]))
    return {"rows": rows,
            "total": {"hotel": round(total["hotel"], 2), "flight": round(total["flight"], 2),
                      "train": round(total["train"], 2), "grand": round(grand, 2),
                      "count": total["count"]},
            "skipped_untyped": skipped,
            "note": "金额为实收实付净额（含退改负数冲销）；住宿/机票/火车按消费类型分列"}
