"""
AI对话记录控制器模块。
提供对话记录（ai_chat_record 表）的历史查询、软删除、过期清理功能。
"""
import threading
import time
import os
import urllib.parse
from datetime import datetime, timedelta
from flask import request, jsonify
from typing import Dict, Tuple, List
from collections import OrderedDict
from zoneinfo import ZoneInfo
import logging

from src.accessors.ai_chat_record_accessor import ai_chat_record_accessor
from src.accessors.ai_agent_accessor import AIAgent
from src.utils.config_manager import config_manager
from src.config import ChatRecordConfig

logger = logging.getLogger(__name__)
LOCAL_TZ = ZoneInfo("Asia/Shanghai")

# 合法的对话类型
VALID_CHAT_TYPES = {'model', 'kb_chat', 'deepagent', 'agent', 'travel_planner'}


def _group_records(flat_records: List[Dict]) -> List[Dict]:
    """将扁平记录按 session 分组，每组内按 msg_time 排序并分配 seq。"""
    groups = OrderedDict()
    for rec in flat_records:
        key = (rec.get('session_thread_id', ''),
               rec.get('user_id', ''),
               rec.get('agent_id', ''),
               rec.get('chat_type', ''))
        if key not in groups:
            groups[key] = {
                'session_thread_id': key[0],
                'user_id': key[1],
                'agent_id': key[2],
                'chat_type': key[3],
                'records': [],
            }
        groups[key]['records'].append({
            'seq': 0,  # 临时占位，后续统一赋值
            'msg_type': rec.get('msg_type', ''),
            'msg_time': rec.get('msg_time', ''),
            'messages': rec.get('messages', {}),
        })

    result = []
    for group in groups.values():
        # system 消息排最前（seq=0），其余按 msg_time 排序
        group['records'].sort(key=lambda r: (0 if r['msg_type'] == 'system' else 1, r['msg_time'] or ''))
        non_system_seq = 1
        for rec in group['records']:
            if rec['msg_type'] == 'system':
                rec['seq'] = 0
            else:
                rec['seq'] = non_system_seq
                non_system_seq += 1
        result.append(group)
    return result


class AIChatRecordController:

    _cleanup_thread = None
    _langfuse_cleanup_thread = None

    @staticmethod
    def _next_cleanup_time(hour: int) -> datetime:
        """计算下一个清理时间点（今天或明天的指定小时）。"""
        now = datetime.now(LOCAL_TZ)
        target = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        return target

    @classmethod
    def start_cleanup_scheduler(cls, flask_app):
        """启动对话记录过期清理后台线程，每天指定时间执行一次。

        参数:
            flask_app: Flask 应用实例，用于提供 app context
        """
        if cls._cleanup_thread is not None:
            return

        retention_days = ChatRecordConfig.RETENTION_DAYS
        cleanup_hour = ChatRecordConfig.CLEANUP_HOUR

        def cleanup_loop():
            while True:
                next_run = cls._next_cleanup_time(cleanup_hour)
                wait_seconds = (next_run - datetime.now(LOCAL_TZ)).total_seconds()
                logger.info(
                    "对话记录清理调度: 保留 %d 天，下次执行 %s（%.0f 秒后）",
                    retention_days, next_run.strftime('%Y-%m-%d %H:%M:%S'), wait_seconds
                )
                time.sleep(wait_seconds)

                try:
                    from src.accessors.ai_chat_record_accessor import AIChatRecord
                    with flask_app.app_context():
                        ok, msg = AIChatRecord.cleanup_old_records(retention_days=retention_days)
                        if ok:
                            logger.info("对话记录清理完成: %s", msg)
                        else:
                            logger.warning("对话记录清理失败: %s", msg)

                        # 清理孤儿会话目录（沙盒已创建但对话记录从未落库的失败会话遗留）
                        ok2, msg2 = AIChatRecord.cleanup_orphan_dirs()
                        if ok2:
                            logger.info("孤儿会话目录清理完成: %s", msg2)
                        else:
                            logger.warning("孤儿会话目录清理失败: %s", msg2)
                except Exception as e:
                    logger.warning(f"对话记录清理失败: {e}")

        cls._cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        cls._cleanup_thread.start()
        logger.info("对话记录清理调度器已启动（保留 %d 天，每天 %d:00 执行）", retention_days, cleanup_hour)

    @staticmethod
    def _cleanup_langfuse_old_traces(retention_days: int):
        """清理超过保留天数的 Langfuse traces。返回 (ok, message)。"""
        from src.config import LangfuseConfig

        if not LangfuseConfig.ENABLED:
            return True, "Langfuse 未启用，跳过"
        if not (LangfuseConfig.HOST and LangfuseConfig.PUBLIC_KEY and LangfuseConfig.SECRET_KEY):
            return True, "Langfuse 未配置 host/key，跳过"

        import httpx
        from datetime import timezone

        base = LangfuseConfig.HOST.rstrip("/")
        auth = (LangfuseConfig.PUBLIC_KEY, LangfuseConfig.SECRET_KEY)
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        to_ts = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

        list_url = f"{base}/api/public/traces"
        deleted = 0
        failed = 0

        with httpx.Client(timeout=120.0) as client:
            # 1. 先分页收集所有符合条件的 trace id。
            #    列表阶段不做删除，分页偏移不会因删除而错位，也能拿到完整快照。
            trace_ids = []
            page = 1
            while True:
                resp = client.get(
                    list_url,
                    params={"limit": 100, "page": page, "toTimestamp": to_ts, "fields": "core"},
                    auth=auth,
                )
                resp.raise_for_status()
                payload = resp.json() or {}
                items = payload.get("data") or []
                for trace in items:
                    tid = trace.get("id")
                    if tid:
                        trace_ids.append(tid)
                total_pages = (payload.get("meta") or {}).get("totalPages") or 0
                if not items or total_pages <= page:
                    break
                page += 1

            # 2. 批量删除。Langfuse 官方建议单批不超过 30~50 个 trace id。
            for i in range(0, len(trace_ids), 50):
                batch = trace_ids[i:i + 50]
                try:
                    del_resp = client.request(
                        "DELETE",
                        f"{base}/api/public/traces",
                        json={"traceIds": batch},
                        auth=auth,
                    )
                    del_resp.raise_for_status()
                    del_resp_json = del_resp.json() or {}
                    deleted += len(batch)
                    logger.info("批量删除 Langfuse traces: %s", del_resp_json.get("message", ""))
                except Exception as e:
                    logger.warning("批量删除 Langfuse traces 失败: %s", e)
                    failed += len(batch)

        return True, f"已删除 {deleted} 条 trace，失败 {failed} 条"

    @classmethod
    def start_langfuse_cleanup_scheduler(cls):
        """启动 Langfuse 数据过期清理后台线程，每天指定时间执行一次。"""
        if cls._langfuse_cleanup_thread is not None:
            return

        retention_days = ChatRecordConfig.RETENTION_DAYS
        cleanup_hour = ChatRecordConfig.CLEANUP_HOUR

        def cleanup_loop():
            while True:
                next_run = cls._next_cleanup_time(cleanup_hour)
                wait_seconds = (next_run - datetime.now(LOCAL_TZ)).total_seconds()
                logger.info(
                    "Langfuse 数据清理调度: 保留 %d 天，下次执行 %s（%.0f 秒后）",
                    retention_days, next_run.strftime('%Y-%m-%d %H:%M:%S'), wait_seconds
                )
                time.sleep(wait_seconds)

                try:
                    ok, msg = cls._cleanup_langfuse_old_traces(retention_days=retention_days)
                    if ok:
                        logger.info("Langfuse 数据清理完成: %s", msg)
                    else:
                        logger.warning("Langfuse 数据清理失败: %s", msg)
                except Exception as e:
                    logger.warning(f"Langfuse 数据清理失败: {e}")

        cls._langfuse_cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        cls._langfuse_cleanup_thread.start()
        logger.info("Langfuse 数据清理调度器已启动（保留 %d 天，每天 %d:00 执行）", retention_days, cleanup_hour)

    @staticmethod
    async def list_records(current_user: str = None) -> Tuple[Dict, int]:
        """查询对话记录列表

        Query 参数:
            session_thread_id: 会话线程ID过滤（可选）
            chat_type: 对话类型过滤（可选，model / deepagent / agent / travel_planner）
            agent_id: 智能体UUID过滤（可选）

        Returns:
            ({'code': 200, 'message': 'success', 'data': [...]}, status_code)
        """
        session_thread_id = request.args.get('session_thread_id', type=str)
        chat_type = request.args.get('chat_type', type=str)
        agent_id = request.args.get('agent_id', type=str)

        if chat_type and chat_type not in VALID_CHAT_TYPES:
            return jsonify({
                'code': 1,
                'message': f'非法的 chat_type: {chat_type}，可选值: {"/".join(sorted(VALID_CHAT_TYPES))}'
            }), 400

        try:
            success, result = ai_chat_record_accessor.get_records(
                session_thread_id=session_thread_id,
                chat_type=chat_type,
                user_name=current_user,
                agent_id=agent_id
            )
            if success:
                grouped = _group_records(result)
                return jsonify({
                    'code': 200,
                    'message': 'success',
                    'data': grouped
                }), 200
            else:
                logger.error(f"查询对话记录失败: {result}")
                return jsonify({
                    'code': 1,
                    'message': result
                }), 500
        except Exception as e:
            logger.error(f"查询对话记录异常: {str(e)}", exc_info=True)
            return jsonify({
                'code': 1,
                'message': f'查询对话记录失败: {str(e)}'
            }), 500

    @staticmethod
    async def list_files(current_user: str = None) -> Tuple[Dict, int]:
        """查询当前用户所有会话的 output 文件

        Returns:
            ({'code': 200, 'message': 'success', 'data': [...]}, status_code)
        """
        try:
            success, sessions = ai_chat_record_accessor.get_distinct_sessions(user_name=current_user)
            if not success:
                logger.error(f"查询会话列表失败: {sessions}")
                return jsonify({'code': 1, 'message': sessions}), 500

            container_path = config_manager.get_file_container_path()
            server_host = config_manager.get_public_host()
            server_port = config_manager.get_public_port()

            # 缓存 agent_name，避免重复查询同一智能体
            agent_name_cache = {}

            def _get_agent_name(agent_id: str) -> str:
                if not agent_id:
                    return ''
                if agent_id in agent_name_cache:
                    return agent_name_cache[agent_id]
                name = ''
                try:
                    ok, agent_data = AIAgent.get_agent(uuid=agent_id)
                    if ok and agent_data:
                        info = agent_data.get('additional_info') or {}
                        if isinstance(info, dict):
                            name = info.get('name') or ''
                except Exception as e:
                    logger.warning(f"查询智能体名称失败 {agent_id}: {e}")
                agent_name_cache[agent_id] = name
                return name

            data = []
            for s in sessions:
                sid = s.get('session_thread_id') or ''
                aid = s.get('agent_id') or ''
                if not sid:
                    continue

                output_dir = os.path.join(container_path, str(sid), 'output')
                if not os.path.isdir(output_dir):
                    continue
                try:
                    filenames = [
                        f for f in os.listdir(output_dir)
                        if os.path.isfile(os.path.join(output_dir, f))
                    ]
                except Exception as e:
                    logger.warning(f"读取 output 目录失败 {output_dir}: {e}")
                    continue
                if not filenames:
                    continue

                files = []
                for fn in filenames:
                    file_path = f"{container_path}/{sid}/output/{fn}"
                    download_url = (
                        f"http://{server_host}:{server_port}"
                        f"/aiFileProcessor/download"
                        f"?file_path={urllib.parse.quote(file_path)}"
                    )
                    files.append({'name': fn, 'path': download_url})

                data.append({
                    'session_thread_id': sid,
                    'agent_id': aid,
                    'agent_name': _get_agent_name(aid),
                    'files': files,
                })

            return jsonify({'code': 200, 'message': 'success', 'data': data}), 200
        except Exception as e:
            logger.error(f"查询 output 文件异常: {str(e)}", exc_info=True)
            return jsonify({'code': 1, 'message': f'查询 output 文件失败: {str(e)}'}), 500

    @staticmethod
    async def delete_records(current_user: str = None) -> Tuple[Dict, int]:
        """软删除对话记录

        Query 参数:
            session_thread_id: 会话线程ID过滤（可选）
            chat_type: 对话类型过滤（可选，model / deepagent / agent / travel_planner）
            agent_id: 智能体UUID过滤（可选）

        Returns:
            ({'code': 200, 'message': ...}, status_code)
        """
        data = request.json or {}
        session_thread_id = data.get('session_thread_id') or request.args.get('session_thread_id', type=str)
        chat_type = data.get('chat_type') or request.args.get('chat_type', type=str)
        agent_id =  data.get('agent_id') or  request.args.get('agent_id', type=str)

        if chat_type and chat_type not in VALID_CHAT_TYPES:
            return jsonify({
                'code': 1,
                'message': f'非法的 chat_type: {chat_type}，可选值: {"/".join(sorted(VALID_CHAT_TYPES))}'
            }), 400

        try:
            success, result = ai_chat_record_accessor.soft_delete_records(
                session_thread_id=session_thread_id,
                chat_type=chat_type,
                user_name=current_user,
                agent_id=agent_id
            )
            if not success:
                logger.error(f"软删除对话记录失败: {result}")
                return jsonify({
                    'code': 1,
                    'message': result
                }), 500

            # 同时软删除对应的会话摘要
            from src.accessors.ai_chat_session_summary_accessor import ai_chat_session_summary_accessor
            summary_success, summary_result = ai_chat_session_summary_accessor.soft_delete_summary(
                session_thread_id=session_thread_id,
                user_name=current_user,
            )
            if not summary_success:
                logger.error(f"软删除会话摘要失败: {summary_result}")

            return jsonify({
                'code': 200,
                'message': result
            }), 200
        except Exception as e:
            logger.error(f"软删除对话记录异常: {str(e)}", exc_info=True)
            return jsonify({
                'code': 1,
                'message': f'软删除对话记录失败: {str(e)}'
            }), 500
