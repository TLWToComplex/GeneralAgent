"""9. 酒店自身偏离度 Top20：同一酒店内最高/最低单晚价之差。

有效记录：住宿、金额>0、天数>0。按酒店(服务商)分组，取组内单晚价最高与最低两单，
偏离度=最高-最低，按偏离度降序取前20；同时输出关注人员交叉分析所需的 (人,酒店) 对。
"""
from __future__ import annotations

from collections import defaultdict

from .common import amount, city_norm, hotel, is_valid, nightly, nights, person, record_info

MODULE_NAME = "hotel_price_spread"
TOP = 20


def _as_int_if_whole(v):
    return int(v) if v == int(v) else v


def analyze(records, config):
    per = defaultdict(list)
    for r in records:
        if not is_valid(r):
            continue
        per[hotel(r)].append(r)
    rows = []
    for h, rs in per.items():
        priced = []
        for r in rs:
            p = nightly(r)
            if p is not None:
                priced.append((p, r))
        if len(priced) < 2:
            continue
        priced.sort(key=lambda x: (x[0], str(x[1].get("消费记录唯一值") or "")))
        lo_p, lo_r = priced[0]
        hi_p, hi_r = priced[-1]
        tot_a = sum(amount(r) for r in rs)
        tot_n = sum(nights(r) for r in rs if nights(r))
        avg = (tot_a / tot_n) if tot_n else None
        rows.append({"hotel": h,
                     "city": city_norm(hi_r),
                     "record_count": len(rs),
                     "total_nights": _as_int_if_whole(tot_n),
                     "avg_rate": round(avg, 2) if avg is not None else None,
                     "max": {"nightly": round(hi_p, 2), **record_info(hi_r)},
                     "min": {"nightly": round(lo_p, 2), **record_info(lo_r)},
                     "spread": round(hi_p - lo_p, 2),
                     "spread_ratio": round((hi_p - lo_p) / lo_p, 6) if lo_p else None})
    rows.sort(key=lambda x: (-x["spread"], x["hotel"]))
    top_rows = rows[:TOP]
    top_set = {x["hotel"] for x in top_rows}
    pairs = sorted({(person(r), h) for h, rs in per.items() if h in top_set for r in rs})
    return {"rows": top_rows, "top_n": TOP,
            "hotel_total": len(rows),
            "watch_pairs": [[p, h] for p, h in pairs],
            "note": "有效记录=住宿且金额>0且天数>0；单晚价=实收实付/住宿天数；平均房价=总金额/总间夜；偏离度=组内最高单晚价-最低单晚价"}
