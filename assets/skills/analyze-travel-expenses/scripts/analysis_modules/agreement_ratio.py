"""2. 协议酒店占比分析：按部门与按人 Top50 统计间夜及协议酒店占比。

口径（业务规则）：协议酒店=服务费>0；非协议=服务费=0；服务费缺失不参与统计。
占比按间夜（住宿天数）计算。
"""
from __future__ import annotations

from collections import defaultdict

from .common import amount, fee, nights, person, txt

MODULE_NAME = "agreement_ratio"
DEPT_COL_DEFAULT = "报账部门"


def _share(part, total):
    return (part / total) if total else None


def analyze(records, config):
    dept_col = config.get("department_column") or DEPT_COL_DEFAULT
    by_dept = defaultdict(lambda: [0.0, 0.0, 0.0])   # [总间夜, 协议间夜, 金额]
    by_person = defaultdict(lambda: [0.0, 0.0, 0.0])  # [总间夜, 协议间夜, 金额]
    grand = [0.0, 0.0, 0.0]
    excluded_missing_fee = 0
    for r in records:
        f = fee(r)
        n = nights(r)
        a = amount(r)
        if f is None:
            excluded_missing_fee += 1
            continue
        if n is None or n <= 0 or a is None or a <= 0:
            continue
        agr = n if f > 0 else 0.0
        d = txt(r.get(dept_col))
        p = person(r)
        for acc in (by_dept[d], by_person[p], grand):
            acc[0] += n
            acc[1] += agr
        by_dept[d][2] += a
        grand[2] += a
        by_person[p][2] = d
    departments = sorted(
        ({"department": d, "total_nights": v[0], "agreement_nights": v[1],
          "agreement_share": _share(v[1], v[0]), "amount": round(v[2], 2)}
         for d, v in by_dept.items()),
        key=lambda x: (-x["amount"], x["department"]))
    people = sorted(
        ({"person": p, "department": v[2], "total_nights": v[0],
          "agreement_nights": v[1], "agreement_share": _share(v[1], v[0])}
         for p, v in by_person.items()),
        key=lambda x: (-x["agreement_nights"], -x["total_nights"], x["person"]))[:50]
    return {"departments": departments,
            "top_50_people": people,
            "total": {"total_nights": grand[0], "agreement_nights": grand[1],
                      "agreement_share": _share(grand[1], grand[0]),
                      "amount": round(grand[2], 2)},
            "excluded_missing_fee": excluded_missing_fee,
            "definition": "协议酒店=服务费>0；非协议酒店=服务费=0；服务费缺失不参与统计；占比按间夜（住宿天数）计算"}
