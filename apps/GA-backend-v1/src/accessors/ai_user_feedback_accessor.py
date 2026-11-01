"""
AI用户反馈访问器模块。
负责 ai_user_feedback 表（用户反馈与功能改进追溯表）的数据库操作。
"""
import uuid
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple, Union
from zoneinfo import ZoneInfo

from src.utils.database import db

logger = logging.getLogger(__name__)

LOCAL_TZ = ZoneInfo("Asia/Shanghai")


class AIUserFeedback(db.Model):
    __tablename__ = 'ai_user_feedback'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True, comment='自增ID')
    uuid = db.Column(db.String(50), unique=True, nullable=False, comment='唯一ID')
    feedback_content = db.Column(db.Text, nullable=False, comment='用户反馈内容')
    priority = db.Column(db.String(10), nullable=True, comment='需求优先级（高/中/低）')
    improvement_plan = db.Column(db.Text, nullable=True, comment='改进措施/解决方案')
    source = db.Column(db.String(100), nullable=True, comment='需求来源')
    status = db.Column(db.String(20), nullable=True, comment='当前进度状态')
    progress = db.Column(db.Numeric(3, 2), nullable=True, default=Decimal('0.00'), comment='完成进度（0~1）')
    start_time = db.Column(db.DateTime, nullable=True, comment='需求提出时间')
    finish_time = db.Column(db.DateTime, nullable=True, comment='完成时间')
    verify_result = db.Column(db.Text, nullable=True, comment='验证结果/用户反馈')
    remark = db.Column(db.Text, nullable=True, comment='备注')
    create_time = db.Column(db.DateTime, nullable=True, comment='创建时间')
    create_by = db.Column(db.String(50), nullable=True, comment='创建人')
    update_time = db.Column(db.DateTime, nullable=True, comment='更新时间')
    update_by = db.Column(db.String(50), nullable=True, comment='更新人')
    is_del = db.Column(db.Integer, nullable=False, default=0, comment='是否删除（0：未删除 1：已删除）')

    # 允许写入的字段白名单（其他字段一律忽略）
    _WRITABLE_FIELDS = {
        'feedback_content', 'priority', 'improvement_plan', 'source',
        'status', 'progress', 'start_time', 'finish_time', 'verify_result',
        'remark', 'create_by', 'update_by'
    }
    _ALLOWED_PRIORITIES = {'高', '中', '低'}

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'uuid': self.uuid,
            'feedback_content': self.feedback_content,
            'priority': self.priority,
            'improvement_plan': self.improvement_plan,
            'source': self.source,
            'status': self.status,
            'progress': float(self.progress) if self.progress is not None else None,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'finish_time': self.finish_time.isoformat() if self.finish_time else None,
            'verify_result': self.verify_result,
            'remark': self.remark,
            'create_time': self.create_time.isoformat() if self.create_time else None,
            'create_by': self.create_by,
            'update_time': self.update_time.isoformat() if self.update_time else None,
            'update_by': self.update_by,
            'is_del': self.is_del,
        }

    # ---------- 内部工具方法 ----------

    @staticmethod
    def _parse_datetime(value) -> Optional[datetime]:
        if value is None or value == '':
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            # 兼容 ISO8601 与常用格式
            for fmt in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
            try:
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                raise ValueError(f'无效的日期时间格式: {value}')
        raise ValueError(f'无效的日期时间值: {value}')

    @staticmethod
    def _parse_progress(value) -> Optional[Decimal]:
        if value is None or value == '':
            return None
        try:
            p = Decimal(str(value))
        except (InvalidOperation, ValueError):
            raise ValueError(f'progress 必须为 0~1 之间的数字: {value}')
        if p < 0 or p > 1:
            raise ValueError('progress 必须在 0 与 1 之间')
        return p.quantize(Decimal('0.01'))

    @classmethod
    def _sanitize(cls, data: dict, *, is_update: bool = False) -> Dict[str, Any]:
        """过滤、校验、转换字段。"""
        cleaned: Dict[str, Any] = {}
        for key, value in data.items():
            if key not in cls._WRITABLE_FIELDS:
                continue
            if key == 'priority' and value is not None and value != '':
                if value not in cls._ALLOWED_PRIORITIES:
                    raise ValueError(f"priority 仅允许取值 {sorted(cls._ALLOWED_PRIORITIES)}")
            if key == 'progress':
                value = cls._parse_progress(value)
            if key in ['start_time', 'finish_time']:
                value = cls._parse_datetime(value)
            cleaned[key] = value

        if not is_update:
            if not cleaned.get('feedback_content'):
                raise ValueError('feedback_content 为必填字段')
        return cleaned

    # ---------- CRUD ----------

    @classmethod
    def add_feedback(cls, data: dict) -> Tuple[bool, Union[Dict[str, Any], str]]:
        """新增一条反馈记录。"""
        try:
            cleaned = cls._sanitize(data, is_update=False)
            now = datetime.now(LOCAL_TZ)
            cleaned.setdefault('create_time', now)
            cleaned.setdefault('update_time', now)
            cleaned['uuid'] = data.get('uuid') or str(uuid.uuid4())
            cleaned.setdefault('is_del', 0)

            record = cls(**cleaned)
            db.session.add(record)
            db.session.commit()
            return True, record.to_dict()
        except ValueError as ve:
            db.session.rollback()
            return False, str(ve)
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding feedback: {e}")
            return False, str(e)

    @classmethod
    def get_feedback(cls, feedback_id: Optional[int] = None,
                     feedback_uuid: Optional[str] = None) -> Tuple[bool, Union[Dict[str, Any], str]]:
        """根据 id 或 uuid 查询单条记录。"""
        try:
            query = cls.query.filter_by(is_del=0)
            if feedback_id is not None:
                query = query.filter_by(id=feedback_id)
            elif feedback_uuid:
                query = query.filter_by(uuid=feedback_uuid)
            else:
                return False, '必须提供 id 或 uuid'

            record = query.first()
            if record:
                return True, record.to_dict()
            return False, '反馈记录不存在'
        except Exception as e:
            logger.error(f"Error getting feedback: {e}")
            return False, str(e)

    @classmethod
    def list_feedback(cls, skip: int = 0, take: int = 100) -> Tuple[bool, Union[Dict[str, Any], str]]:
        """列出反馈记录，内部循环分页获取全部数据。skip 为起始偏移，take 作为每页批次大小。
        返回 {'total': N, 'items': [...]}"""
        try:
            base = cls.query.filter_by(is_del=0)
            total = base.count()
            all_items: List[Dict[str, Any]] = []
            offset = skip
            while True:
                batch = base.order_by(cls.id).offset(offset).limit(take).all()
                all_items.extend(r.to_dict() for r in batch)
                if len(batch) < take:
                    break
                offset += take
            return True, {'total': total, 'items': all_items}
        except Exception as e:
            logger.error(f"Error listing feedback: {e}")
            return False, str(e)

    @classmethod
    def query_feedback(cls, *,
                       keyword: Optional[str] = None,
                       priority: Optional[str] = None,
                       status: Optional[str] = None,
                       source: Optional[str] = None,
                       create_by: Optional[str] = None,
                       skip: int = 0, take: int = 100) -> Tuple[bool, Union[Dict[str, Any], str]]:
        """按条件查询反馈，关键字会同时匹配反馈内容、改进措施、验证结果、备注。
        内部循环分页获取全部匹配数据。skip 为起始偏移，take 作为每页批次大小。"""
        try:
            query = cls.query.filter_by(is_del=0)
            if priority:
                query = query.filter_by(priority=priority)
            if status:
                query = query.filter_by(status=status)
            if source:
                query = query.filter(cls.source.like(f'%{source}%'))
            if create_by:
                query = query.filter_by(create_by=create_by)
            if keyword:
                like = f'%{keyword}%'
                query = query.filter(db.or_(
                    cls.feedback_content.like(like),
                    cls.improvement_plan.like(like),
                    cls.verify_result.like(like),
                    cls.remark.like(like),
                ))
            total = query.count()
            all_items: List[Dict[str, Any]] = []
            offset = skip
            while True:
                batch = query.order_by(cls.id).offset(offset).limit(take).all()
                all_items.extend(r.to_dict() for r in batch)
                if len(batch) < take:
                    break
                offset += take
            return True, {'total': total, 'items': all_items}
        except Exception as e:
            logger.error(f"Error querying feedback: {e}")
            return False, str(e)

    @classmethod
    def update_feedback(cls, feedback_uuid: str,
                        update_data: dict) -> Tuple[bool, Union[Dict[str, Any], str]]:
        """根据 uuid 更新反馈记录。"""
        try:
            if not feedback_uuid:
                return False, 'uuid 不能为空'

            record = cls.query.filter_by(uuid=feedback_uuid, is_del=0).first()
            if not record:
                return False, '反馈记录不存在'

            cleaned = cls._sanitize(update_data, is_update=True)
            for k, v in cleaned.items():
                setattr(record, k, v)
            record.update_time = datetime.now(LOCAL_TZ)
            db.session.commit()
            return True, record.to_dict()
        except ValueError as ve:
            db.session.rollback()
            return False, str(ve)
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating feedback: {e}")
            return False, str(e)

    @classmethod
    def delete_feedback(cls, feedback_uuid: str,
                        delete_by: Optional[str] = None) -> Tuple[bool, Union[Dict[str, Any], str]]:
        """删除一条反馈记录。"""
        try:
            if not feedback_uuid:
                return False, 'uuid 不能为空'

            record = cls.query.filter_by(uuid=feedback_uuid).first()
            if not record:
                return False, '反馈记录不存在'

            db.session.delete(record)
            db.session.commit()
            return True, {'message': '反馈删除成功'}
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting feedback: {e}")
            return False, str(e)
