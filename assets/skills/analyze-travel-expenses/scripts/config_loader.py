"""将用户友好的中文配置转换为脚本内部参数。"""
from __future__ import annotations

import json
from pathlib import Path


KEYS = {
    "配置版本": "version",
    "货币单位": "currency",
    "是否去除重复记录": "deduplicate",
    "唯一键候选字段": "unique_key_candidates",
    "金额字段优先顺序": "amount_precedence",
    "日期字段优先顺序": "date_precedence",
    "排名保留数量": "top_n",
    "折扣率分段界限": "discount_bands",
    "住宿标准比例分段界限": "hotel_ratio_bands",
    "部门统计字段": "department_column",
    "启用分析模块": "enabled_modules",
    "比较明细最大数量": "comparison_max_details",
    "同城比较窗口天数": "city_window_days",
    "同城高价判定倍数": "city_high_price_ratio",
    "输出语言": "output_language",
}

MODULES = {
    "住宿顶格报销分析": "ceiling_reimbursement",
    "酒店等级分析": "hotel_level",
    "住宿价格偏离分析": "price_deviation",
    "早预订低价比较": "earlier_booking_lower_price",
    "同城十天高价订单": "city_ten_day_high_price",
    "非协议酒店提前预订": "advance_no_service_fee",
    "机票住宿深度分析": "flight_analysis",
    "协议酒店占比分析": "agreement_ratio",
    "前二十大城市及其他": "top_cities",
    "酒店数量统计": "hotel_ranking",
    "部门发生费用统计": "department_expenses",
    "每月出差费用曲线": "monthly_trend",
    "酒店自身偏离度Top20": "hotel_price_spread",
    "退订后重定价差": "cancel_rebook_gap",
    "关注人员交叉分析": "watch_persons",
}

CURRENCY = {"人民币": "CNY", "美元": "USD", "欧元": "EUR", "日元": "JPY"}
LANGUAGE = {"简体中文": "zh-CN", "繁体中文": "zh-TW", "英文": "en"}


def normalize_config(raw: dict) -> dict:
    config = {}
    for key, value in raw.items():
        config[KEYS.get(key, key)] = value
    config["enabled_modules"] = [MODULES.get(v, v) for v in config.get("enabled_modules", [])]
    config["currency"] = CURRENCY.get(config.get("currency"), config.get("currency", "CNY"))
    config["output_language"] = LANGUAGE.get(config.get("output_language"), config.get("output_language", "zh-CN"))
    return config


def load_config(path: str | Path) -> dict:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return normalize_config(raw)
