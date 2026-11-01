"""4. 前二十大城市及其他：按到达地统计间夜数、金额、占比、平均房价。

城市归一：去掉结尾“市”（大连市→大连）。按间夜数降序取前20，其余合并为“其他”。
"""
from __future__ import annotations

from collections import defaultdict

from .common import amount, city_norm, is_valid, nights

MODULE_NAME = "top_cities"
TOP = 20


def analyze(records, config):
    agg = defaultdict(lambda: [0.0, 0.0, 0])  # [间夜, 金额, 订单数]
    for r in records:
        if not is_valid(r):
            continue
        c = city_norm(r)
        agg[c][0] += nights(r)
        agg[c][1] += amount(r)
        agg[c][2] += 1
    total_nights = sum(v[0] for v in agg.values())
    total_amount = sum(v[1] for v in agg.values())
    rows = sorted(
        ({"city": c, "nights": v[0], "amount": round(v[1], 2), "count": v[2],
          "nights_share": (v[0] / total_nights) if total_nights else None,
          "amount_share": (v[1] / total_amount) if total_amount else None,
          "avg_rate": (v[1] / v[0]) if v[0] else None}
         for c, v in agg.items()),
        key=lambda x: (-x["nights"], x["city"]))
    result = list(rows[:TOP])
    rest = rows[TOP:]
    if rest:
        rn = sum(x["nights"] for x in rest)
        ra = sum(x["amount"] for x in rest)
        rc = sum(x["count"] for x in rest)
        result.append({"city": f"其他({len(rest)}个城市)", "nights": rn, "amount": round(ra, 2),
                       "count": rc,
                       "nights_share": (rn / total_nights) if total_nights else None,
                       "amount_share": (ra / total_amount) if total_amount else None,
                       "avg_rate": (ra / rn) if rn else None, "is_other": True})
    return {"rows": result, "top_n": TOP, "city_count": len(agg),
            "total": {"nights": total_nights, "amount": round(total_amount, 2)},
            "note": "城市按到达地统计，结尾“市”已归一（大连市→大连）；按间夜数降序，第21名起合并为其他"}
