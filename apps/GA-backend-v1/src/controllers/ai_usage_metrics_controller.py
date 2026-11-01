"""
使用追踪指标控制器。
通过 Langfuse 公共 HTTP API 拉取 traces 后做聚合，返回平台使用统计。
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Any, Dict, List, Optional, Tuple

import httpx
from flask import jsonify, request
from src.accessors.ai_user_accessor import AIUser
from src.config import LangfuseConfig

logger = logging.getLogger(__name__)

LOCAL_TZ = ZoneInfo("Asia/Shanghai")

def _parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    s = value.strip()
    if not s:
        return None
    # 纯日期（YYYY-MM-DD）：补齐为当前 UTC 时分秒，而非 00:00:00
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        try:
            date_part = datetime.strptime(s, "%Y-%m-%d")
            now_utc = datetime.now(timezone.utc)
            return date_part.replace(
                hour=now_utc.hour, minute=now_utc.minute,
                second=now_utc.second, tzinfo=timezone.utc,
            )
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        try:
            return datetime.strptime(s, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    raise ValueError(f"无效日期时间格式: {value}")


def _to_iso(dt: datetime) -> str:
    """转换成 UTC ISO（带 Z），仅用于给 Langfuse 的查询参数。"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _to_local(value) -> Optional[str]:
    """对外输出统一用本地时区的 'YYYY-MM-DD HH:MM:SS'。
    入参可以是 datetime 或 ISO 字符串；None / 空串返回 None。
    """
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        try:
            dt = _parse_iso_datetime(value)
        except ValueError:
            return value  # 解析失败就原样回退
        if dt is None:
            return None
    else:
        return str(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S")


def _to_local_date(value) -> Optional[str]:
    """同 _to_local 但只取本地日期 'YYYY-MM-DD'，用于跨天聚合。"""
    s = _to_local(value)
    return s[:10] if s else None


def _mask_id(value: Optional[str], keep: int = 4) -> Optional[str]:
    """脱敏 UUID/会话 ID：只保留末尾 keep 位，前面打码。
    输出形如 '…5ee'。None 或空串原样返回。
    目的：减少响应里"姓名 + 完整 UUID + 行为追踪"组合，避免模型回复触发内容安全过滤。
    """
    if (not value) or value == "<None>":
        return value
    s = str(value)
    if len(s) <= keep:
        return s
    return "…" + s[-keep:]


class _LangfuseClient:
    """轻量 Langfuse REST 客户端：只用 traces 列表接口。"""

    # 单页请求并发上限，避免瞬间打爆 Langfuse
    _CONCURRENCY = 8

    def __init__(self, host: str, public_key: str, secret_key: str, timeout: float = 60.0):
        self.base = host.rstrip("/")
        self.auth = (public_key, secret_key)
        self.timeout = timeout

    async def _fetch_page(self, client: httpx.AsyncClient, url: str,
                          params: Dict[str, Any], page: int,
                          semaphore: asyncio.Semaphore) -> Tuple[int, List[Dict[str, Any]], int]:
        """请求单页 traces，返回 (page, data, total_pages)。"""
        async with semaphore:
            params_with_page = {**params, "page": page}
            resp = await client.get(url, params=params_with_page, auth=self.auth)
            resp.raise_for_status()
            payload = resp.json() or {}
            items = payload.get("data") or []
            meta = payload.get("meta") or {}
            total_pages = meta.get("totalPages") or 0
            return page, items, total_pages

    async def fetch_traces(self,
                           from_ts: Optional[datetime] = None,
                           to_ts: Optional[datetime] = None,
                           user_id: Optional[str] = None,
                           page_size: int = 100,
                           fields: Optional[str] = None) -> List[Dict[str, Any]]:
        """分页拉取 traces，先取首页确定总页数，再并发拉取所有剩余页。

        Args:
            fields: Langfuse fields 参数，逗号分隔字段组（core/io/scores/observations/metrics）。
                    默认不传（返回全部字段）。仅查 core 字段可大幅减少传输体积。
        """
        url = f"{self.base}/api/public/traces"
        params: Dict[str, Any] = {"limit": page_size}
        if fields:
            params["fields"] = fields
        if from_ts:
            params["fromTimestamp"] = _to_iso(from_ts)
        if to_ts:
            params["toTimestamp"] = _to_iso(to_ts)
        if user_id:
            params["userId"] = user_id

        semaphore = asyncio.Semaphore(self._CONCURRENCY)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # 第一步：先拉首页，获取总页数
            _, first_page_items, total_pages = await self._fetch_page(
                client, url, params, 1, semaphore
            )
            if not first_page_items:
                return []

            traces: List[Dict[str, Any]] = list(first_page_items)

            if total_pages <= 1:
                return traces

            # 第二步：并发拉取剩余页
            remaining_pages = list(range(2, total_pages + 1))
            tasks = [
                self._fetch_page(client, url, params, page, semaphore)
                for page in remaining_pages
            ]
            results = await asyncio.gather(*tasks)

            # 按页码顺序合并（保证与串行结果一致）
            results_sorted = sorted(results, key=lambda r: r[0])
            for _, items, _ in results_sorted:
                traces.extend(items)
        traces = [t for t in traces if t.get("userId", "") != "eval_rag"]

        return traces


def _resolve_window(from_param: Optional[str], to_param: Optional[str],
                    days_default: int = 30, use_days_default: bool = False) -> Tuple[datetime, datetime]:
    to_dt = _parse_iso_datetime(to_param) or datetime.now(timezone.utc)
    if use_days_default:
        from_dt = _parse_iso_datetime(from_param) or (to_dt - timedelta(days=days_default))
    else:
        from_dt = _parse_iso_datetime(from_param) if from_param else None
    if from_dt and from_dt > to_dt:
        from_dt, to_dt = to_dt, from_dt
    return from_dt, to_dt


def _build_client() -> Optional[_LangfuseClient]:
    if not LangfuseConfig.HOST or not LangfuseConfig.PUBLIC_KEY or not LangfuseConfig.SECRET_KEY:
        return None
    return _LangfuseClient(LangfuseConfig.HOST, LangfuseConfig.PUBLIC_KEY, LangfuseConfig.SECRET_KEY)


def _resolve_user_uuid(realname: str) -> Tuple[Optional[List[str]], Optional[str]]:
    """从 realname 查询 user.uuid。
    Returns:
        (user_uuid, error_message)。error_message 为 None 表示成功。
    """
    if not realname:
        return None, '未识别到当前用户'
    users = AIUser.query.filter_by(realname=realname, is_del=0).all()
    if not users:
        return None, f'用户不存在: {realname}'
    return [user.uuid for user in users], None


def _resolve_user_name(user_uuid: str) -> Tuple[Optional[str], Optional[str]]:
    """从 user_uuid 查询 realname。
    Returns:
        (realname, error_message)。error_message 为 None 表示成功。
    """
    if not user_uuid:
        return None, '未识别到当前用户'
    user = AIUser.query.filter_by(uuid=user_uuid, is_del=0).first()
    if not user:
        return None, f'用户不存在: {user_uuid}'
    return user.realname, None


def _batch_resolve_user_names(user_ids: set) -> Dict[str, str]:
    """批量解析用户 UUID → realname，一次 DB 查询完成。"""
    if not user_ids:
        return {}
    users = AIUser.query.filter(AIUser.uuid.in_(user_ids), AIUser.is_del == 0).all()
    return {u.uuid: u.realname for u in users}


class AIUsageMetricsController:
    """平台使用追踪相关接口。"""

    @staticmethod
    async def summary(current_user: str = "admin") -> Tuple[Dict, int]:
        """
        汇总指标：总 trace 数、去重用户数、时间范围内的活跃天数。

        查询参数：
            - fromDate (str, 可选): ISO8601 起始时间，默认 30 天前
            - toDate   (str, 可选): ISO8601 结束时间，默认现在
        """
        if not LangfuseConfig.ENABLED:
            return jsonify({"code": 503, "message": "Langfuse 追踪未启用"}), 503
        client = _build_client()
        if client is None:
            return jsonify({"code": 503, "message": "Langfuse 配置缺失"}), 503

        try:
            from_dt, to_dt = _resolve_window(request.args.get("fromDate"), request.args.get("toDate"))
        except ValueError as ve:
            return jsonify({"code": 400, "message": str(ve)}), 400

        try:
            traces = await client.fetch_traces(from_ts=from_dt, to_ts=to_dt, fields="core")
        except httpx.HTTPError as e:
            logger.error("调用 Langfuse 失败: %s", e)
            return jsonify({"code": 502, "message": f"Langfuse 调用失败: {e}"}), 502

        users: set = set()
        active_days: set = set()
        for t in traces:
            uid = t.get("userId")
            if uid:
                users.add(uid)
            ts = t.get("timestamp") or t.get("createdAt")
            local_day = _to_local_date(ts)
            if local_day:
                active_days.add(local_day)

        return jsonify({
            "code": 200,
            "message": "success",
            "data": {
                "fromDate": _to_local(from_dt),
                "toDate": _to_local(to_dt),
                "totalTraces": len(traces),
                "uniqueUsers": len(users),
                "activeDays": len(active_days),
            }
        }), 200

    @staticmethod
    async def top_users(current_user: str = "admin") -> Tuple[Dict, int]:
        """
        按使用次数排序的用户榜单。

        查询参数：
            - fromDate / toDate: 同 summary
            - limit (int, 默认 20)
        """
        if not LangfuseConfig.ENABLED:
            return jsonify({"code": 503, "message": "Langfuse 追踪未启用"}), 503
        client = _build_client()
        if client is None:
            return jsonify({"code": 503, "message": "Langfuse 配置缺失"}), 503

        try:
            from_dt, to_dt = _resolve_window(request.args.get("fromDate"), request.args.get("toDate"))
        except ValueError as ve:
            return jsonify({"code": 400, "message": str(ve)}), 400

        limit = max(1, min(request.args.get("limit", default=20, type=int), 100))

        try:
            traces = await client.fetch_traces(from_ts=from_dt, to_ts=to_dt, fields="core")
        except httpx.HTTPError as e:
            logger.error("调用 Langfuse 失败: %s", e)
            return jsonify({"code": 502, "message": f"Langfuse 调用失败: {e}"}), 502

        counts: Dict[str, int] = {}
        last_seen: Dict[str, str] = {}
        for t in traces:
            uid = t.get("userId") or "<None>"
            counts[uid] = counts.get(uid, 0) + 1
            ts = t.get("timestamp") or t.get("createdAt") or ""
            if ts and ts > last_seen.get(uid, ""):
                last_seen[uid] = ts

        # 批量解析用户名称，只对去重后的 userId 做一次 DB 查询
        unique_ids = {uid for uid in counts.keys() if uid != "<None>"}
        resolved_names = _batch_resolve_user_names(unique_ids)

        ranking = sorted(
            ({
                "userId": _mask_id(uid),
                "userName": resolved_names.get(uid) or "<anonymous>",
                "traceCount": cnt,
                "lastSeen": _to_local(last_seen.get(uid)),
            } for uid, cnt in counts.items()),
            key=lambda x: x["traceCount"],
            reverse=True,
        )[:limit]
        ranking = [x for x in ranking if x.get("userName") != "<anonymous>"] + [x for x in ranking if x.get("userName") == "<anonymous>"]

        return jsonify({
            "code": 200,
            "message": "success",
            "data": {
                "fromDate": _to_local(from_dt),
                "toDate": _to_local(to_dt),
                "totalUsers": len(counts),
                "ranking": ranking,
            }
        }), 200

    @staticmethod
    async def user_activity(current_user: str = "admin") -> Tuple[Dict, int]:
        """
        指定用户的活动概况。

        查询参数：
            - userName (str, 必填)
            - fromDate / toDate: 同 summary
            - sample (int, 默认 5): 返回最近 N 条 trace 摘要
        """
        if not LangfuseConfig.ENABLED:
            return jsonify({"code": 503, "message": "Langfuse 追踪未启用"}), 503
        client = _build_client()
        if client is None:
            return jsonify({"code": 503, "message": "Langfuse 配置缺失"}), 503

        user_name = request.args.get("userName", type=str)
        user_ids, error_message = _resolve_user_uuid(user_name)
        if not user_ids:
            return jsonify({"code": 400, "message": error_message or "userId 为必填字段"}), 400

        try:
            from_dt, to_dt = _resolve_window(request.args.get("fromDate"), request.args.get("toDate"))
        except ValueError as ve:
            return jsonify({"code": 400, "message": str(ve)}), 400

        sample_n = max(0, min(request.args.get("sample", default=5, type=int), 50))

        async def _build_user_data(user_id: str) -> Optional[Dict[str, Any]]:
            try:
                traces = await client.fetch_traces(from_ts=from_dt, to_ts=to_dt, user_id=user_id, fields="core")
            except httpx.HTTPError as e:
                logger.error("调用 Langfuse 失败，跳过: %s", e)
                return None

            traces_sorted = sorted(traces, key=lambda x: x.get("timestamp", ""), reverse=True)
            first_seen = traces_sorted[-1].get("timestamp") if traces_sorted else None
            last_seen = traces_sorted[0].get("timestamp") if traces_sorted else None
            if first_seen:
                first_seen = datetime.fromisoformat(first_seen.replace("Z", "+00:00"))
            if last_seen:
                last_seen = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
            sample = [
                {
                    "id": _mask_id(t.get("id"), keep=4),
                    "name": t.get("name"),
                    # "timestamp": _to_local(t.get("timestamp")),
                    "timestamp": _to_local(datetime.fromisoformat(t.get("timestamp").replace("Z", "+00:00"))) if t.get("timestamp") else None,
                    "sessionId": _mask_id(t.get("sessionId")),
                }
                for t in traces_sorted[:sample_n]
            ]
            return {
                "userId": _mask_id(user_id),
                "userName": user_name,
                "fromDate": _to_local(from_dt),
                "toDate": _to_local(to_dt),
                "traceCount": len(traces),
                "firstSeen": _to_local(first_seen),
                "lastSeen": _to_local(last_seen),
                "sample": sample,
            }

        results = await asyncio.gather(*[_build_user_data(uid) for uid in user_ids])
        data = [r for r in results if r is not None]

        return jsonify({
            "code": 200,
            "message": "success",
            "data": data
        }), 200

    @staticmethod
    async def deep_agent_latency(current_user: str = "admin") -> Tuple[Dict, int]:
        """
        DeepAgent 平均耗时统计：筛选 name 以 'DeepAgent' 开头的 trace，
        统计最近 30 天的平均、最小、最大耗时（秒）。

        查询参数：
            - fromDate / toDate: 可选，覆盖默认 30 天窗口
        """
        if not LangfuseConfig.ENABLED:
            return jsonify({"code": 503, "message": "Langfuse 追踪未启用"}), 503
        client = _build_client()
        if client is None:
            return jsonify({"code": 503, "message": "Langfuse 配置缺失"}), 503

        try:
            from_dt, to_dt = _resolve_window(request.args.get("fromDate"), request.args.get("toDate"), use_days_default=True)
        except ValueError as ve:
            return jsonify({"code": 400, "message": str(ve)}), 400

        try:
            traces = await client.fetch_traces(from_ts=from_dt, to_ts=to_dt, fields="core,metrics")
        except httpx.HTTPError as e:
            logger.error("调用 Langfuse 失败: %s", e)
            return jsonify({"code": 502, "message": f"Langfuse 调用失败: {e}"}), 502

        latencies: List[float] = []
        daily_sums: Dict[str, List[float]] = {}
        for t in traces:
            name = t.get("name") or ""
            if not name.startswith("DeepAgent"):
                continue
            latency = t.get("latency")
            if latency is None:
                continue
            try:
                latency = float(latency)
            except (TypeError, ValueError):
                continue
            latencies.append(latency)
            day = _to_local_date(t.get("timestamp") or t.get("createdAt"))
            if day:
                daily_sums.setdefault(day, []).append(latency)

        if not latencies:
            return jsonify({
                "code": 200,
                "message": "success",
                "data": {
                    "fromDate": _to_local(from_dt),
                    "toDate": _to_local(to_dt),
                    "traceCount": 0,
                    "avgLatencyMs": None,
                    "minLatencyMs": None,
                    "maxLatencyMs": None,
                    "p50LatencyMs": None,
                }
            }), 200

        latencies_sorted = sorted(latencies)

        def _percentile(p: float) -> float:
            idx = int(len(latencies_sorted) * p / 100)
            idx = min(idx, len(latencies_sorted) - 1)
            return round(latencies_sorted[idx], 2)


        return jsonify({
            "code": 200,
            "message": "success",
            "data": {
                "fromDate": _to_local(from_dt),
                "toDate": _to_local(to_dt),
                "traceCount": len(latencies),
                "avgLatencyMs": round(sum(latencies) / len(latencies), 2),
                "minLatencyMs": round(min(latencies), 2),
                "maxLatencyMs": round(max(latencies), 2),
                "p50LatencyMs": _percentile(50),
            }
        }), 200
