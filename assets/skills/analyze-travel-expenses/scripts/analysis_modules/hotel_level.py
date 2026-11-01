from collections import defaultdict
from .common import num, txt

MODULE_NAME = "hotel_level"


def analyze(records, config):
    dept_col = config.get("department_column", "报账部门")
    out = defaultdict(lambda: {"count": 0, "amount": 0.0})
    for r in records:
        key = (txt(r.get(dept_col)), txt(r.get("等级"), "未指定"))
        out[key]["count"] += 1; out[key]["amount"] += num(r.get("amount")) or 0
    return {"rows": [{"department": k[0], "hotel_level": k[1], "count": v["count"], "amount": round(v["amount"], 2)}
                     for k, v in sorted(out.items())]}
