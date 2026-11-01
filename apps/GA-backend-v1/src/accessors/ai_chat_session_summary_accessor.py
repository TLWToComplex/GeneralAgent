"""
AI会话摘要访问器模块。
一个 session_thread_id 一条摘要，总结会话第一个用户问题。
"""
import uuid
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from src.utils.database import db

from typing import Dict, Any, Tuple, Union, List

logger = logging.getLogger(__name__)
LOCAL_TZ = ZoneInfo("Asia/Shanghai")


class AIChatSessionSummary(db.Model):
    """AI会话摘要数据模型类"""
    __tablename__ = 'ai_chat_session_summary'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True, comment='自增ID')
    uuid = db.Column(db.String(50), unique=True, nullable=False, comment='唯一ID')
    session_thread_id = db.Column(db.String(128), unique=True, nullable=False, comment='会话线程ID')
    summary = db.Column(db.Text, nullable=False, comment='会话首个问题的摘要')
    is_del = db.Column(db.Boolean, nullable=False, default=False, comment='是否软删除')
    create_time = db.Column(db.DateTime, nullable=False, comment='创建时间')
    create_by = db.Column(db.String(50), nullable=False, comment='创建人')
    update_time = db.Column(db.DateTime, nullable=True, comment='更新时间')
    update_by = db.Column(db.String(50), nullable=True, comment='更新人')

    def to_dict(self) -> Dict[str, Any]:
        """将模型实例转换为字典"""
        return {
            'id': self.id,
            'uuid': self.uuid,
            'session_thread_id': self.session_thread_id,
            'summary': self.summary,
            'is_del': self.is_del,
            'create_time': self.create_time.isoformat() if self.create_time else None,
            'create_by': self.create_by,
            'update_time': self.update_time.isoformat() if self.update_time else None,
            'update_by': self.update_by,
        }

    @classmethod
    def get_by_session_thread_id(cls, session_thread_id: str) -> Tuple[bool, Union[Dict[str, Any], str]]:
        """
        查询指定会话的摘要。

        返回:
            (True, 摘要字典) 或 (False, 错误信息)
        """
        try:
            if not session_thread_id:
                return False, 'session_thread_id 不能为空'
            record = cls.query.filter_by(session_thread_id=session_thread_id, is_del=False).first()
            if record:
                return True, record.to_dict()
            return False, '摘要不存在'
        except Exception as e:
            logger.error(f"Error getting session summary: {str(e)}")
            return False, str(e)

    @classmethod
    def list_summary(cls, create_by: str = None) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        查询会话摘要列表。

        参数:
            create_by: 可选，按创建人过滤

        返回:
            (True, [摘要字典列表]) 或 (False, 错误信息)
        """
        try:
            query = cls.query.filter_by(is_del=False)
            if create_by:
                query = query.filter_by(create_by=create_by)
            records = query.order_by(cls.create_time.desc()).all()
            return True, [record.to_dict() for record in records] if records else []
        except Exception as e:
            logger.error(f"Error listing session summaries: {str(e)}")
            return False, str(e)

    @classmethod
    def insert_summary(cls, session_thread_id: str, summary: str,
                       operator: str = 'system') -> Tuple[bool, str]:
        """
        插入会话摘要。若该 session_thread_id 已存在摘要则直接返回（幂等）。

        返回:
            (成功状态, 描述)
        """
        session_thread_id = session_thread_id or ''
        summary = (summary or '').strip()
        operator = operator or 'system'

        if not session_thread_id or not summary:
            return False, 'session_thread_id 和 summary 不能为空'

        try:
            existing = cls.query.filter_by(session_thread_id=session_thread_id).first()
            if existing and not existing.is_del:
                return True, '摘要已存在，跳过'
            if existing and existing.is_del:
                # 软删除后重新总结：原地恢复
                existing.summary = summary
                existing.is_del = False
                existing.create_time = datetime.now(LOCAL_TZ)
                existing.create_by = operator
                existing.update_time = datetime.now(LOCAL_TZ)
                existing.update_by = operator
                db.session.commit()
                logger.info(f"会话摘要已恢复: session={session_thread_id}")
                return True, '摘要已恢复'

            record = cls(
                uuid=str(uuid.uuid4()),
                session_thread_id=session_thread_id,
                summary=summary,
                is_del=False,
                create_time=datetime.now(LOCAL_TZ),
                create_by=operator,
                update_time=datetime.now(LOCAL_TZ),
                update_by=operator
            )
            db.session.add(record)
            db.session.commit()
            logger.info(f"会话摘要已保存: session={session_thread_id}")
            return True, '摘要保存成功'
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error inserting session summary: {str(e)}")
            return False, str(e)

    @classmethod
    def update_summary(cls, session_thread_id: str, summary: str,
                       operator: str = 'system') -> Tuple[bool, str]:
        """
        编辑指定会话的摘要（仅创建人本人可编辑）。

        返回:
            (成功状态, 描述)
        """
        session_thread_id = session_thread_id or ''
        summary = (summary or '').strip()
        operator = operator or 'system'

        if not session_thread_id or not summary:
            return False, 'session_thread_id 和 summary 不能为空'

        try:
            record = cls.query.filter_by(
                session_thread_id=session_thread_id, is_del=False
            ).first()
            if not record:
                return False, '摘要不存在或无权限编辑'

            record.summary = summary
            record.update_time = datetime.now(LOCAL_TZ)
            record.update_by = operator
            db.session.commit()
            logger.info(f"会话摘要已更新: session={session_thread_id}")
            return True, '摘要更新成功'
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating session summary: {str(e)}")
            return False, str(e)

    @classmethod
    def touch_summary(cls, session_thread_id: str, update_time: datetime = datetime.now(LOCAL_TZ),
                      operator: str = 'system') -> Tuple[bool, str]:
        """
        仅刷新摘要行的 update_time / update_by，不改 summary 内容。

        返回:
            (成功状态, 描述)
        """
        session_thread_id = session_thread_id or ''
        operator = operator or 'system'
        if not session_thread_id:
            return False, 'session_thread_id 不能为空'

        try:
            record = cls.query.filter_by(
                session_thread_id=session_thread_id, is_del=False
            ).first()
            if not record:
                return False, '摘要不存在'

            record.update_time = update_time
            record.update_by = operator
            db.session.commit()
            return True, '摘要更新时间已刷新'
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error touching session summary: {str(e)}")
            return False, str(e)

    @classmethod
    def soft_delete_summary(cls, session_thread_id: str = None,
                              user_name: str = None) -> Tuple[bool, str]:
        """
        软删除会话摘要：将匹配记录的 is_del 置为 True。

        参数:
            session_thread_id: 可选，按会话线程ID过滤
            user_name: 可选，按创建人过滤

        返回:
            (成功状态, 影响行数描述)
        """
        try:
            query = cls.query.filter_by(is_del=False)
            if session_thread_id:
                query = query.filter_by(session_thread_id=session_thread_id)
            if user_name:
                query = query.filter_by(create_by=user_name)

            affected = query.update({'is_del': True}, synchronize_session=False)
            db.session.commit()
            logger.info(f"软删除会话摘要: {affected} 条")
            return True, f'软删除 {affected} 条摘要'
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error soft-deleting session summaries: {str(e)}")
            return False, str(e)


# 创建全局实例
ai_chat_session_summary_accessor = AIChatSessionSummary()
