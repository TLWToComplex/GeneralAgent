"""6. 酒店数量统计：前二十大城市内的酒店，按间夜数取前二十。

先按间夜数取前20个城市，再在这20个城市范围内按间夜数取前20个酒店；
同时输出每个前20城市的酒店数量。
"""
from __future__ import annotations

from collections import defaultdict

from .common import amount, city_norm, hotel, is_valid, nights

MODULE_NAME = "hotel_ranking"
TOP_CITY = 20
TOP_HOTEL = 20


def analyze(records, config):
    city_nights = defaultdict(float)
    per = defaultdict(lambda: [0.0, 0.0, 0])  # (城市,酒店) -> [间夜, 金额, 订单数]
    for r in records:
        if not is_valid(r):
            continue
        c = city_norm(r)
        h = hotel(r)
        city_nights[c] += nights(r)
        per[(c, h)][0] += nights(r)
        per[(c, h)][1] += amount(r)
        per[(c, h)][2] += 1
    top_cities = [c for c, _ in sorted(city_nights.items(), key=lambda kv: (-kv[1], kv[0]))[:TOP_CITY]]
    hc = set(top_cities)
    rows = sorted(
        ({"city": c, "hotel": h, "nights": v[0], "amount": round(v[1], 2), "count": v[2]}
         for (c, h), v in per.items() if c in hc),
        key=lambda x: (-x["nights"], x["hotel"]))[:TOP_HOTEL]
    hotels_per_city = defaultdict(int)
    for (c, _h) in per:
        if c in hc:
            hotels_per_city[c] += 1
    hotel_count_by_city = [{"city": c, "nights": city_nights[c], "hotel_count": hotels_per_city[c]}
                           for c in top_cities]
    return {"rows": rows, "top_city_n": TOP_CITY, "top_hotel_n": TOP_HOTEL,
            "hotel_count_by_city": hotel_count_by_city,
            "note": "统计范围为间夜数前20城市内的酒店；酒店前20按间夜数降序"}
