from collections import defaultdict
from .common import nightly, num, txt

MODULE_NAME = "ceiling_reimbursement"
BANDS = ["95%以上", "90%-95%", "80%-90%", "70%-80%", "70%以下"]


def band(ratio):
    return "95%以上" if ratio >= .95 else "90%-95%" if ratio >= .9 else "80%-90%" if ratio >= .8 else "70%-80%" if ratio >= .7 else "70%以下"


def analyze(records, config):
    dept_col = config.get("department_column", "报账部门")
    depts = defaultdict(lambda: defaultdict(lambda: {"count": 0, "amount": 0.0}))
    people = defaultdict(lambda: {"department": "", "count": 0, "amount": 0.0, "bands": defaultdict(int)})
    ceiling_pairs = set()
    for r in records:
        price, standard = nightly(r), num(r.get("住宿标准"))
        if price is None or not standard or standard <= 0:
            continue
        b, d, p = band(price / standard), txt(r.get(dept_col)), txt(r.get("乘机人"))
        if b == "95%以上":
            ceiling_pairs.add((p, txt(r.get("服务商"))))
        amount = num(r.get("amount")) or 0
        depts[d][b]["count"] += 1; depts[d][b]["amount"] += amount
        people[p]["department"] = d; people[p]["count"] += 1; people[p]["amount"] += amount; people[p]["bands"][b] += 1
    department_rows = []
    for d, values in depts.items():
        total_count = sum(v["count"] for v in values.values()); total_amount = sum(v["amount"] for v in values.values())
        for b in BANDS:
            v = values[b]
            department_rows.append({"department": d, "band": b, "count": v["count"], "amount": round(v["amount"], 2),
                                    "count_share": round(v["count"] / total_count, 6) if total_count else 0,
                                    "amount_share": round(v["amount"] / total_amount, 6) if total_amount else 0})
    top = sorted(({"person": p, "department": v["department"], "count": v["count"], "amount": round(v["amount"], 2),
                   **{b: v["bands"][b] for b in BANDS}} for p, v in people.items()), key=lambda x: (-x["amount"], x["person"]))
    return {"department_bands": department_rows, "top_50_people": top[:50],
            "watch_pairs": sorted([list(x) for x in ceiling_pairs])}
