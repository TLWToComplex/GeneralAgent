"""
AI对话记录访问器模块。
一行一条消息，按 msg_time 排序即可还原对话时序。
每完成一轮对话，批量插入本轮产生的多条消息。
"""
import json
import os
import shutil
import uuid
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from src.utils.database import db
# 单条消息序列化后的字节预算，与采集器 chat_record_collector 中定义保持一致，
# 用作落库前的最终兜底（防止单条消息把整条 INSERT 报文推过 MySQL max_allowed_packet）
from src.utils.chat_record_collector import MAX_MESSAGE_BYTES

from typing import Dict, Any, Tuple, List

logger = logging.getLogger(__name__)
LOCAL_TZ = ZoneInfo("Asia/Shanghai")


def _msg_type_from_dict(item: Dict[str, Any]) -> str:
    """从消息字典推断消息类型。"""
    if 'system' in item:
        return 'system'
    if 'user' in item:
        return 'user'
    if 'reasoning' in item:
        return 'reasoning'
    if 'tool_calls' in item:
        return 'tool_calls'
    if 'response' in item:
        return 'response'
    if 'todos' in item:
        return 'todos'
    return 'unknown'


def _parse_msg_time(item: Dict[str, Any]) -> datetime:
    """从消息字典中提取 time 字段并解析为 datetime。"""
    time_str = item.get('time', '')
    if not time_str:
        return datetime.now(LOCAL_TZ)
    try:
        return datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S.%f').replace(tzinfo=LOCAL_TZ)
    except ValueError:
        try:
            return datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=LOCAL_TZ)
        except ValueError:
            return datetime.now(LOCAL_TZ)


class AIChatRecord(db.Model):
    """AI对话记录数据模型类（一行一条消息）"""
    __tablename__ = 'ai_chat_record'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True, comment='自增ID')
    uuid = db.Column(db.String(50), unique=True, nullable=False, comment='唯一ID')
    chat_type = db.Column(db.String(20), nullable=False,
                          comment='对话类型: model / deepagent / agent / travel_planner')
    user_id = db.Column(db.String(64), nullable=False, default='', comment='用户ID，未提供为空串')
    session_thread_id = db.Column(db.String(128), nullable=False, default='', comment='会话线程ID')
    agent_id = db.Column(db.String(64), nullable=False, default='', comment='智能体UUID；model/travel_planner 为空串')
    turn_id = db.Column(db.String(128), nullable=False, default='', comment='会话轮次ID')
    msg_type = db.Column(db.String(20), nullable=False,
                         comment='消息类型: user / reasoning / tool_calls / response / todos')
    messages = db.Column(db.JSON, nullable=False, comment='单条消息内容')
    msg_time = db.Column(db.DateTime, nullable=False, comment='消息事件时间，用于排序还原对话时序')
    is_del = db.Column(db.Boolean, nullable=False, default=False, comment='是否软删除')
    create_time = db.Column(db.DateTime, nullable=False, index=True, comment='创建时间')
    create_by = db.Column(db.String(50), nullable=False, comment='创建人')

    def to_dict(self) -> Dict[str, Any]:
        """将模型实例转换为字典"""
        return {
            'id': self.id,
            'uuid': self.uuid,
            'chat_type': self.chat_type,
            'user_id': self.user_id,
            'session_thread_id': self.session_thread_id,
            'agent_id': self.agent_id,
            'turn_id': self.turn_id,
            'msg_type': self.msg_type,
            'messages': self.messages if self.messages is not None else {},
            'msg_time': self.msg_time.isoformat() if self.msg_time else None,
            'is_del': self.is_del,
            'create_time': self.create_time.isoformat() if self.create_time else None,
            'create_by': self.create_by,
        }

    @classmethod
    def insert_messages(cls, chat_type: str, user_id: str, session_thread_id: str,
                        agent_id: str, turn_id: str, message_items: List[Dict[str, Any]],
                        operator: str = 'system') -> Tuple[bool, str]:
        """
        批量插入本轮对话产生的多条消息，每条消息一行。

        参数:
            chat_type: 对话类型 model / deepagent / agent / travel_planner
            user_id: 用户ID（None 归一为空串）
            session_thread_id: 会话线程ID（None 归一为空串）
            agent_id: 智能体UUID（None 归一为空串）
            message_items: 本轮按时序排列的消息列表，每条为
                {user,time} / {reasoning,time} / {tool_calls,time} / {response,time} 之一
            operator: 操作人

        返回:
            (成功状态, 错误信息或成功条数)
        """
        chat_type = chat_type or ''
        user_id = user_id or ''
        session_thread_id = session_thread_id or ''
        agent_id = agent_id or ''
        turn_id = turn_id or ''
        operator = operator or 'system'

        if not message_items or not isinstance(message_items, list):
            return False, 'message_items 必须是非空列表'

        current_time = datetime.now(LOCAL_TZ)
        inserted = 0

        try:
            # 同一 turn_id 的新记录写入前，先软删除该 turn_id 的旧记录
            if turn_id:
                cls.query.filter_by(turn_id=turn_id, is_del=False).update(
                    {'is_del': True}, synchronize_session=False
                )

            # 如果本轮包含 system 消息，先软删除该 session 下旧的 system 消息
            has_system = any('system' in m for m in message_items if isinstance(m, dict))
            if has_system and session_thread_id:
                cls.query.filter_by(
                    session_thread_id=session_thread_id, msg_type='system', is_del=False
                ).update({'is_del': True}, synchronize_session=False)

            for item in message_items:
                if not isinstance(item, dict):
                    continue

                # 跳过过大的单条消息
                try:
                    item_bytes = len(json.dumps(item, ensure_ascii=False).encode('utf-8'))
                    if item_bytes > MAX_MESSAGE_BYTES:
                        logger.warning(f"单条消息过大（{item_bytes} bytes），跳过")
                        continue
                except Exception:
                    pass

                record = cls(
                    uuid=str(uuid.uuid4()),
                    chat_type=chat_type,
                    user_id=user_id,
                    session_thread_id=session_thread_id,
                    agent_id=agent_id,
                    turn_id=turn_id,
                    msg_type=_msg_type_from_dict(item),
                    messages=item,
                    msg_time=_parse_msg_time(item),
                    create_time=current_time,
                    create_by=operator,
                )
                db.session.add(record)
                inserted += 1

            if inserted > 0:
                db.session.commit()
                logger.info(
                    f"对话记录已保存: chat_type={chat_type}, user_id={user_id}, "
                    f"session={session_thread_id}, agent_id={agent_id or '(无)'}, "
                    f"本轮消息数={inserted}")
            return True, f'成功插入 {inserted} 条消息'
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error inserting chat messages: {str(e)}")
            return False, str(e)

    @classmethod
    def get_records(cls, session_thread_id: str = None, chat_type: str = None,
                    user_name: str = None, agent_id: str = None) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        查询对话记录，按 msg_time 升序排列（还原对话时序）。

        参数:
            session_thread_id: 可选，按会话线程ID过滤
            chat_type: 可选，按对话类型过滤
            user_name: 可选，按用户名过滤
            agent_id: 可选，按智能体UUID过滤

        返回:
            (True, [记录字典列表]) 或 (False, 错误信息)
        """
        try:
            query = cls.query.filter_by(is_del=False)
            if session_thread_id:
                query = query.filter_by(session_thread_id=session_thread_id)
            if user_name:
                query = query.filter_by(create_by=user_name)
            if chat_type:
                query = query.filter_by(chat_type=chat_type)
            if agent_id:
                query = query.filter_by(agent_id=agent_id)

            records = query.order_by(cls.msg_time.asc()).all()
            return True, [record.to_dict() for record in records] if records else []
        except Exception as e:
            logger.error(f"Error getting chat records: {str(e)}")
            return False, str(e)

    @classmethod
    def get_distinct_sessions(cls, user_name: str = None) -> Tuple[bool, List[Dict[str, str]]]:
        """
        查询指定用户下所有去重后的 (session_thread_id, agent_id) 组合。

        参数:
            user_name: 可选，按创建人（操作人）过滤

        返回:
            (True, [{'session_thread_id': ..., 'agent_id': ...}, ...])
        """
        try:
            query = db.session.query(cls.session_thread_id, cls.agent_id).filter(
                cls.is_del == False,
                cls.session_thread_id != '',
            )
            if user_name:
                query = query.filter(cls.create_by == user_name)
            rows = query.distinct().all()
            return True, [
                {'session_thread_id': r[0], 'agent_id': r[1] or ''}
                for r in rows
            ]
        except Exception as e:
            logger.error(f"Error getting distinct sessions: {str(e)}")
            return False, str(e)

    @classmethod
    def soft_delete_records(cls, session_thread_id: str = None, chat_type: str = None,
                            user_name: str = None, agent_id: str = None) -> Tuple[bool, str]:
        """
        软删除对话记录：将匹配记录的 is_del 置为 True。

        参数:
            session_thread_id: 可选，按会话线程ID过滤
            chat_type: 可选，按对话类型过滤
            user_name: 可选，按用户名过滤
            agent_id: 可选，按智能体UUID过滤

        返回:
            (成功状态, 影响行数描述)
        """
        try:
            query = cls.query.filter_by(is_del=False)
            if session_thread_id:
                query = query.filter_by(session_thread_id=session_thread_id)
            if user_name:
                query = query.filter_by(create_by=user_name)
            if chat_type:
                query = query.filter_by(chat_type=chat_type)
            if agent_id:
                query = query.filter_by(agent_id=agent_id)

            affected = query.update({'is_del': True}, synchronize_session=False)
            db.session.commit()
            logger.info(f"软删除对话记录: {affected} 条")
            return True, f'软删除 {affected} 条记录'
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error soft-deleting chat records: {str(e)}")
            return False, str(e)

    @classmethod
    def cleanup_old_records(cls, retention_days: int = 90, batch_size: int = 5000) -> Tuple[bool, str]:
        """
        清理超过保留期的会话：删除其所有对话记录及对应的文件目录。

        找出最近一条记录 create_time 早于 retention_days 前的 session_thread_id，
        删除这些会话的全部记录，并删除 CONTAINER_PATH 下对应 session_thread_id 的目录。

        参数:
            retention_days: 保留天数，默认 90 天
            batch_size: 单次最多处理的会话数（避免单次运行过久）

        返回:
            (成功状态, 统计信息)
        """
        from sqlalchemy import func
        from src.config import ChatRecordConfig
        from src.accessors.ai_chat_session_summary_accessor import AIChatSessionSummary

        cutoff = datetime.now(LOCAL_TZ) - timedelta(days=retention_days)
        total_deleted = 0
        total_summary_deleted = 0
        deleted_dirs = 0
        container_path = ChatRecordConfig.FileConfig.CONTAINER_PATH
        try:
            # 先查出所有过期 session（最近一条记录 create_time 早于 cutoff）
            rows = db.session.query(cls.session_thread_id).filter(
                cls.session_thread_id != ''
            ).group_by(cls.session_thread_id).having(
                func.max(cls.create_time) < cutoff
            ).all()
            expired_sessions = [r[0] for r in rows]

            # 按 batch_size 分批删除
            for i in range(0, len(expired_sessions), batch_size):
                batch = expired_sessions[i:i + batch_size]

                # 批量删除该批会话的所有记录（一条 DELETE ... WHERE session_thread_id IN (...)）
                result = db.session.execute(
                    cls.__table__.delete().where(cls.session_thread_id.in_(batch))
                )
                total_deleted += result.rowcount
                db.session.commit()

                # 批量删除该批会话的摘要记录
                summary_result = db.session.execute(
                    AIChatSessionSummary.__table__.delete().where(
                        AIChatSessionSummary.session_thread_id.in_(batch)
                    )
                )
                total_summary_deleted += summary_result.rowcount
                db.session.commit()

                # 删除 CONTAINER_PATH 下对应会话目录（逐个删除）
                for sid in batch:
                    session_dir = os.path.join(container_path, str(sid))
                    try:
                        if os.path.isdir(session_dir):
                            shutil.rmtree(session_dir, ignore_errors=True)
                            deleted_dirs += 1
                    except Exception as e:
                        logger.warning(f"删除会话目录失败 {session_dir}: {e}")

            if total_deleted > 0 or total_summary_deleted > 0 or deleted_dirs > 0:
                logger.info(
                    f"清理过期对话记录完成: 删除 {total_deleted} 条记录 / "
                    f"{total_summary_deleted} 条摘要 / {deleted_dirs} 个目录 "
                    f"(保留 {retention_days} 天，过期会话 {len(expired_sessions)} 个)"
                )
            return True, f'删除 {total_deleted} 条记录 / {total_summary_deleted} 条摘要 / {deleted_dirs} 个目录'
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error cleaning up old chat records: {str(e)}")
            return False, str(e)

    @classmethod
    def cleanup_orphan_dirs(cls, skip_sids: set = None) -> Tuple[bool, str]:
        """
        清理 chat_record_files 下不存在对应对话记录的孤儿 session 目录。

        扫描 CONTAINER_PATH 下所有 {session_thread_id} 子目录，
        若该 sid 在 ai_chat_record 表中没有任何记录，则删除该目录。
        用于回收「沙盒已创建、但对话记录从未落库」的失败会话遗留目录。

        参数:
            skip_sids: 需要跳过的 session_thread_id 集合（如仍在活跃的沙盒），可选

        返回:
            (成功状态, 统计信息)
        """
        from src.config import ChatRecordConfig

        container_path = ChatRecordConfig.FileConfig.CONTAINER_PATH
        skip_sids = skip_sids or set()
        deleted = 0
        failed = 0
        try:
            if not container_path or not os.path.isdir(container_path):
                return True, f'目录不存在或未配置: {container_path}'

            # 候选 sid = 磁盘上实际存在的子目录名（排除活跃沙盒）
            candidates = []
            for name in os.listdir(container_path):
                if name in skip_sids:
                    continue
                if not os.path.isdir(os.path.join(container_path, name)):
                    continue
                candidates.append(name)
            if not candidates:
                return True, '无候选会话目录'

            # 只查询「磁盘上存在」的 sid 是否有摘要记录。
            # 摘要表每个会话一行、数据量远小于对话记录表，且 session_thread_id 与记录表一一对应。
            from src.accessors.ai_chat_session_summary_accessor import AIChatSessionSummary
            existing_sids = set()
            for i in range(0, len(candidates), 500):
                batch = candidates[i:i + 500]
                rows = db.session.query(AIChatSessionSummary.session_thread_id).filter(
                    AIChatSessionSummary.session_thread_id.in_(batch)
                ).all()
                existing_sids.update(r[0] for r in rows)

            for name in candidates:
                if name in existing_sids:
                    continue
                sid_dir = os.path.join(container_path, name)
                try:
                    shutil.rmtree(sid_dir, ignore_errors=True)
                    deleted += 1
                    logger.info(f"删除孤儿会话目录: {name}")
                except Exception as e:
                    failed += 1
                    logger.warning(f"删除孤儿会话目录失败 {name}: {e}")

            logger.info(f"清理孤儿会话目录完成: 删除 {deleted} 个，失败 {failed} 个")
            return True, f'删除 {deleted} 个孤儿目录，失败 {failed} 个'
        except Exception as e:
            logger.error(f"Error cleaning up orphan chat record dirs: {str(e)}")
            return False, str(e)


# 创建全局实例
ai_chat_record_accessor = AIChatRecord()