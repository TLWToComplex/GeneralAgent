from collections import defaultdict
from .common import dt, num

MODULE_NAME = "advance_no_service_fee"


def analyze(records, config):
    groups = defaultdict(lambda: {"count": 0, "amount": 0.0})
    for r in records:
        booked, stay = dt(r.get("预订时间")), dt(r.get("出发时间"))
        fee = num(r.get("服务费")); amount = num(r.get("amount")) or 0
        if fee != 0 or amount <= 0 or not booked or not stay:
            continue
        lead = (stay.date() - booked.date()).days
        if lead < 0:
            bucket = "日期异常"
        elif lead == 0:
            bucket = "当天预订"
        elif lead == 1:
            bucket = "提前1天"
        elif lead == 2:
            bucket = "提前2天"
        else:
            bucket = "提前3天及以上"
        groups[bucket]["count"] += 1; groups[bucket]["amount"] += amount
    order = ["当天预订", "提前1天", "提前2天", "提前3天及以上", "日期异常"]
    return {"status": "ok", "agreement_rule": "服务费大于0为协议酒店；服务费等于0为非协议酒店",
            "buckets": [{"lead_time": k, "count": groups[k]["count"], "amount": round(groups[k]["amount"], 2)} for k in order]}
