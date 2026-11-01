"""12. 关注人员交叉分析：同一(人,酒店)组合同时出现在 1/5/9/11 四个表中 ≥3 个。

交叉模块（CROSS）：在 run_extensions 主流程完成后运行，读取已有结果中各表输出的
watch_pairs（人,酒店 组合全集，未截断），做集合交集统计，输出关注人员及统计表。

四张表口径：
- 1 顶格报销：单晚价/住宿标准 >= 95% 的记录对应 (人,酒店)
- 5 价格偏离：Top50 偏离人员的全部住宿 (人,酒店)
- 9 酒店自身偏离：Top20 酒店内全部住宿 (人,酒店)
- 11 同城10天高价：被判定高价订单的 (人,酒店)
"""
from __future__ import annotations

from collections import defaultdict

MODULE_NAME = "watch_persons"
CROSS = True
THRESHOLD = 3
TABLES = (
    ("ceiling_reimbursement", "1顶格报销"),
    ("price_deviation", "5价格偏离Top50"),
    ("hotel_price_spread", "9酒店自身偏离Top20"),
    ("city_ten_day_high_price", "11同城10天高价"),
)


def analyze(records, config, results):
    sets = {}
    for key, _label in TABLES:
        res = (results or {}).get(key) or {}
        sets[key] = {tuple(p) for p in res.get("watch_pairs", [])}
    all_pairs = set()
    for s in sets.values():
        all_pairs |= s
    rows = []
    for p, h in sorted(all_pairs):
        hit = [label for key, label in TABLES if (p, h) in sets[key]]
        if len(hit) >= THRESHOLD:
            rows.append({"person": p, "hotel": h, "tables": hit, "table_count": len(hit)})
    rows.sort(key=lambda x: (-x["table_count"], x["person"], x["hotel"]))
    by_person = defaultdict(list)
    for r in rows:
        by_person[r["person"]].append(r)
    persons = [{"person": p,
                "hotel_count": len(v),
                "hotels": [x["hotel"] for x in v],
                "tables": sorted({t for x in v for t in x["tables"]})}
               for p, v in sorted(by_person.items(), key=lambda kv: (-len(kv[1]), kv[0]))]
    return {"pairs": rows, "persons": persons,
            "pair_count": len(rows), "person_count": len(persons),
            "threshold": THRESHOLD,
            "set_sizes": {key: len(s) for key, _label in TABLES for s in [sets[key]]},
            "tables": {key: label for key, label in TABLES},
            "definition": f"关注人员=(人,酒店)组合同时出现在 {len(TABLES)} 张表中至少 {THRESHOLD} 张；"
                          "各表组合来源见各模块 watch_pairs（未截断全集）"}
