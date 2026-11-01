"""系统配置访问器模块"""
import logging
from datetime import datetime
from typing import Dict, Any, Tuple, List, Union
from src.utils.database import db

logger = logging.getLogger(__name__)


class AISystemConfig(db.Model):
    __tablename__ = 'ai_system_config'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True, comment='自增ID')
    config_key = db.Column(db.String(100), unique=True, nullable=False, comment='配置键')
    config_value = db.Column(db.Text, nullable=False, comment='配置值')
    update_time = db.Column(db.DateTime, nullable=False, comment='更新时间')
    update_by = db.Column(db.String(50), nullable=False, comment='更新人')

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'config_key': self.config_key,
            'config_value': self.config_value,
            'update_time': self.update_time.isoformat() if self.update_time else None,
            'update_by': self.update_by,
        }

    @classmethod
    def get_all_configs(cls) -> Tuple[bool, Union[Dict[str, str], str]]:
        """获取所有配置，返回 {config_key: config_value} 字典"""
        try:
            configs = cls.query.all()
            return True, {c.config_key: c.config_value for c in configs}
        except Exception as e:
            logger.error(f"Error getting system configs: {str(e)}")
            return False, str(e)

    @classmethod
    def get_configs_list(cls) -> Tuple[bool, Union[List[Dict], str]]:
        """获取所有配置列表"""
        try:
            configs = cls.query.order_by(cls.id).all()
            return True, [c.to_dict() for c in configs]
        except Exception as e:
            logger.error(f"Error getting system configs: {str(e)}")
            return False, str(e)

    @classmethod
    def update_configs(cls, configs: dict, current_user: str) -> Tuple[bool, Union[List[Dict], str]]:
        """批量更新配置，configs 为 {config_key: config_value}"""
        try:
            result = []
            for key, value in configs.items():
                config = cls.query.filter_by(config_key=key).first()
                if config:
                    config.config_value = str(value)
                    config.update_time = datetime.now()
                    config.update_by = current_user
                else:
                    config = cls(
                        config_key=key,
                        config_value=str(value),
                        update_time=datetime.now(),
                        update_by=current_user
                    )
                    db.session.add(config)
                result.append(config.to_dict())

            db.session.commit()
            return True, result
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating system configs: {str(e)}")
            return False, str(e)

    @classmethod
    def add_config(cls, config_key: str, config_value: str, current_user: str) -> Tuple[bool, Union[Dict, str]]:
        """新增配置，key 重复时返回错误"""
        try:
            existing = cls.query.filter_by(config_key=config_key).first()
            if existing:
                return False, f'配置键 "{config_key}" 已存在'

            config = cls(
                config_key=config_key,
                config_value=str(config_value),
                update_time=datetime.now(),
                update_by=current_user
            )
            db.session.add(config)
            db.session.commit()
            return True, config.to_dict()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding system config: {str(e)}")
            return False, str(e)

    @classmethod
    def seed_defaults(cls):
        """初始化默认配置（仅添加不存在的 key）"""
        defaults = {'score_threshold': '0.1', 'top_k': '3'}
        existing_keys = {c.config_key for c in cls.query.all()}
        missing = {k: v for k, v in defaults.items() if k not in existing_keys}
        if missing:
            cls.update_configs(missing, 'system')
            logger.info(f"System config defaults seeded: {list(missing.keys())}")