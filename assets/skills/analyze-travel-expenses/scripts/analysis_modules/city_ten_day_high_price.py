from collections import defaultdict, deque
from .common import city, dt, nightly, record_info, txt

MODULE_NAME = "city_ten_day_high_price"


def analyze(records, config):
    days = int(config.get("city_window_days", 10)); factor = float(config.get("city_high_price_ratio", 1.0))
    grouped = defaultdict(list)
    for r in records:
        stay, price = dt(r.get("出发时间")), nightly(r)
        if stay and price is not None:
            grouped[city(r)].append((stay, price, r))
    details = []
    pairs = set()
    for place, values in grouped.items():
        values.sort(key=lambda x: x[0]); window = deque(); total = 0.0
        for stay, price, record in values:
            while window and (stay.date() - window[0][0].date()).days >= days:
                total -= window.popleft()[1]
            batch_count = len(window) + 1; batch_mean = (total + price) / batch_count
            if batch_count >= 2 and price > batch_mean * factor:
                details.append({"city": place, "stay_date": str(stay.date()), "nightly": round(price, 2),
                                "batch_count": batch_count, "batch_average": round(batch_mean, 2),
                                "higher_by": round(price - batch_mean, 2), "higher_rate": round(price / batch_mean - 1, 6),
                                "order": record_info(record)})
                pairs.add((txt(record.get("乘机人")), txt(record.get("服务商"))))
            window.append((stay, price, record)); total += price
    details.sort(key=lambda x: -x["higher_rate"])
    limit = int(config.get("comparison_max_details", 500))
    return {"matched_count": len(details), "window_days": days, "threshold_ratio": factor, "details": details[:limit],
            "watch_pairs": sorted([list(x) for x in pairs])}
