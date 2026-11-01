from collections import defaultdict
from .common import nightly, txt

MODULE_NAME = "price_deviation"


def analyze(records, config):
    dept_col = config.get("department_column", "报账部门")
    valid = [(r, nightly(r)) for r in records]; valid = [(r, p) for r, p in valid if p is not None]
    overall = sum(p for _, p in valid) / len(valid) if valid else 0
    depts, people = defaultdict(list), defaultdict(list)
    person_hotels = defaultdict(set)
    for r, p in valid:
        depts[txt(r.get(dept_col))].append(p); people[(txt(r.get("乘机人")), txt(r.get(dept_col)))].append(p)
        person_hotels[txt(r.get("乘机人"))].add(txt(r.get("服务商")))
    def row(name, vals):
        avg = sum(vals) / len(vals)
        return {"name": name, "count": len(vals), "average_nightly": round(avg, 2),
                "deviation_amount": round(avg - overall, 2), "deviation_rate": round((avg / overall - 1), 6) if overall else None}
    dept_rows = sorted((row(k, v) for k, v in depts.items()), key=lambda x: (-x["deviation_rate"], x["name"]))
    person_rows = []
    for (p, d), vals in people.items():
        item = row(p, vals); item["department"] = d; person_rows.append(item)
    person_rows.sort(key=lambda x: (-x["deviation_rate"], x["name"]))
    watch_pairs = sorted({(t["name"], h) for t in person_rows[:50] for h in person_hotels.get(t["name"], set())})
    return {"overall_average_nightly": round(overall, 2), "departments": dept_rows, "top_50_people": person_rows[:50],
            "watch_pairs": [list(x) for x in watch_pairs]}
