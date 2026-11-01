"""10. 退订后重定价差：同一(人,酒店,入住日)内，先退订(已退票)后又新订(已出票)的单晚价差。

匹配规则（固定）：
- 范围：住宿记录且退改签类型 ∈ {已出票, 已退票}，乘机人/服务商/出发时间非空；
- 分组：同一 人+酒店+入住日（出发时间日期）；
- 匹配：组内 已出票.预订时间 >= 已退票.预订时间（重订发生在退订之后或同日）；
- 价差：新订单晚价 - 被退订单晚价（单晚价=|实收实付|/住宿天数）；
- 输出间隔天数与是否同日（预订日期相同）。预订时间只有天级精度，无法复现“分钟级”间隔。
"""
from __future__ import annotations

from collections import defaultdict

from .common import dt, hotel, num, person, txt

MODULE_NAME = "cancel_rebook_gap"
DEPT_COL_DEFAULT = "报账部门"


def _nightly(r):
    a, n = num(r.get("实收实付")), num(r.get("住宿天数"))
    if a is None or n in (None, 0):
        return None
    return abs(a) / n


def analyze(records, config):
    dept_col = config.get("department_column") or DEPT_COL_DEFAULT
    max_details = int(config.get("comparison_max_details") or 500)
    groups = defaultdict(list)
    for r in records:
        if str(r.get("消费类型") or "").strip() != "住宿":
            continue
        t = str(r.get("退改签类型") or "").strip()
        if t not in ("已出票", "已退票"):
            continue
        sd = dt(r.get("出发时间"))
        p = person(r)
        h = hotel(r)
        if not sd or p == "人员缺失" or h == "酒店缺失":
            continue
        groups[(p, h, sd.date())].append((t, r))
    details = []
    excluded = 0
    for (p, h, stay), items in groups.items():
        refs = [(t, r) for t, r in items if t == "已退票"]
        iss = [(t, r) for t, r in items if t == "已出票"]
        for _t, ref in refs:
            rb = dt(ref.get("预订时间"))
            rn = _nightly(ref)
            if rb is None or rn is None:
                excluded += 1
                continue
            for _t2, it in iss:
                ib = dt(it.get("预订时间"))
                inn = _nightly(it)
                if ib is None or inn is None:
                    excluded += 1
                    continue
                if ib < rb:
                    continue
                diff = inn - rn
                gap_days = (ib - rb).days
                details.append({
                    "person": p,
                    "department": txt(it.get(dept_col)),
                    "city": txt(it.get("到达地")),
                    "stay_date": str(stay),
                    "cancelled": {"hotel": h, "booking_date": str(rb.date()),
                                  "nights": num(ref.get("住宿天数")),
                                  "total": round(abs(num(ref.get("实收实付")) or 0), 2),
                                  "nightly": round(rn, 2),
                                  "order": txt(ref.get("订单号")),
                                  "record": txt(ref.get("消费记录唯一值"))},
                    "new": {"hotel": h, "booking_date": str(ib.date()),
                            "nights": num(it.get("住宿天数")),
                            "total": round(num(it.get("实收实付")) or 0, 2),
                            "nightly": round(inn, 2),
                            "order": txt(it.get("订单号")),
                            "record": txt(it.get("消费记录唯一值"))},
                    "diff": round(diff, 2),
                    "gap_days": gap_days,
                    "same_day": gap_days == 0,
                    "direction": "加价" if diff > 0 else ("降价" if diff < 0 else "持平"),
                })
    details.sort(key=lambda x: (-abs(x["diff"]), x["person"], x["stay_date"]))
    return {"matched_count": len(details),
            "same_day_count": sum(1 for d in details if d["same_day"]),
            "up_count": sum(1 for d in details if d["diff"] > 0),
            "down_count": sum(1 for d in details if d["diff"] < 0),
            "excluded_no_nights": excluded,
            "details": details[:max_details],
            "definition": "同一人+同一酒店+同一入住日：已出票.预订时间>=已退票.预订时间即视为退订后重订；"
                          "价差=新订单晚价-被退订单晚价；间隔=两单预订日期差（天）"}
