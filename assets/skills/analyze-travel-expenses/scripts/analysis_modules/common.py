from __future__ import annotations

from datetime import date, datetime
from typing import Any


def num(v: Any) -> float | None:
    if v in (None, ""):
        return None
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v)
    s = str(v).strip().replace(",", "").replace("￥", "").replace("¥", "")
    if s.endswith("%"):
        s = s[:-1]
        try:
            return float(s) / 100
        except ValueError:
            return None
    try:
        return float(s)
    except ValueError:
        return None


def dt(v: Any) -> datetime | None:
    if isinstance(v, datetime):
        return v
    if isinstance(v, date):
        return datetime(v.year, v.month, v.day)
    if not v:
        return None
    s = str(v).strip().replace("/", "-")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[:19], fmt)
        except ValueError:
            pass
    return None


def txt(v: Any, default: str = "未提供") -> str:
    s = str(v or "").strip()
    return s or default


def nightly(r: dict[str, Any]) -> float | None:
    amount, nights = num(r.get("amount")), num(r.get("住宿天数"))
    return amount / nights if amount is not None and amount > 0 and nights and nights > 0 else None


def city(r: dict[str, Any]) -> str:
    return txt(r.get("到达地"), "城市缺失")


def record_info(r: dict[str, Any]) -> dict[str, Any]:
    return {k: r.get(k) for k in ("订单号", "消费记录唯一值", "乘机人", "报账部门", "服务商", "到达地",
                                            "预订时间", "出发时间", "到达时间", "住宿天数", "住宿标准",
                                            "票面价", "服务费", "实收实付", "退改签类型")}



# ---- 住宿专用取数（口径与 schema/business-rules 对齐） ----

def nights(r: dict[str, Any]) -> float | None:
    return num(r.get("住宿天数"))


def amount(r: dict[str, Any]) -> float | None:
    return num(r.get("amount"))


def city_norm(r: dict[str, Any]) -> str:
    s = txt(r.get("到达地"), "城市缺失")
    return s[:-1] if s.endswith("市") else s


def hotel(r: dict[str, Any]) -> str:
    return txt(r.get("服务商"), "酒店缺失")


def person(r: dict[str, Any]) -> str:
    return txt(r.get("乘机人"), "人员缺失")


def fee(r: dict[str, Any]) -> float | None:
    return num(r.get("服务费"))


def is_valid(r: dict[str, Any]) -> bool:
    a, n = amount(r), nights(r)
    return a is not None and a > 0 and n is not None and n > 0
