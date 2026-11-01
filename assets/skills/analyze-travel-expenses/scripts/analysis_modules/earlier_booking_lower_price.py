from collections import defaultdict
from .common import city, dt, nightly, record_info

MODULE_NAME = "earlier_booking_lower_price"


def analyze(records, config):
    groups = defaultdict(list)
    for r in records:
        booked, stay, price = dt(r.get("预订时间")), dt(r.get("出发时间")), nightly(r)
        if booked and stay and price is not None:
            groups[(city(r), stay.date())].append((booked, price, r))
    details = []
    for (place, stay_day), values in groups.items():
        values.sort(key=lambda x: x[0]); best = None
        for booked, price, record in values:
            if best and booked > best[0] and price > best[1]:
                details.append({"city": place, "stay_date": str(stay_day), "earlier_booking_time": str(best[0]),
                                "earlier_nightly": round(best[1], 2), "later_booking_time": str(booked),
                                "later_nightly": round(price, 2), "difference": round(price - best[1], 2),
                                "earlier_order": record_info(best[2]), "later_order": record_info(record)})
            if best is None or price < best[1]:
                best = (booked, price, record)
    details.sort(key=lambda x: -x["difference"])
    limit = int(config.get("comparison_max_details", 500))
    return {"matched_count": len(details), "definition": "同城同入住日，较早预订的最低单晚价低于后续预订", "details": details[:limit]}
