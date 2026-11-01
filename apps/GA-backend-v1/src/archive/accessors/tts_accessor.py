"""
Text-to-Speech accessor module.
Manages database operations for TTS configurations and services.
"""
from datetime import datetime
from .database import db
from typing import Dict, Any, Tuple, List, Union, Optional
class TTS(db.Model):
    __tablename__ = 'tts'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    prompt = db.Column(db.Text)
    descriptions = db.Column(db.Text)
    audio_url = db.Column(db.String(1000))
    virtual_human_tts_status = db.Column(db.Boolean, default=False)
    offline_synthesis_tts_status = db.Column(db.Boolean, default=False)
    is_need_training = db.Column(db.Boolean, default=False)
    virtual_human_tts_model_path = db.Column(db.String(255))
    offline_synthesis_tts_model_path = db.Column(db.String(255))
    created_at = db.Column(db.TIMESTAMP, default=datetime.now)
    updated_at = db.Column(db.TIMESTAMP, default=datetime.now, onupdate=datetime.now)

    @classmethod
    def create(cls, data: dict) -> Tuple[bool, Union['TTS', str]]:
        try:
            tts = cls(
                name=data.get('name'),
                prompt=data.get('prompt'),
                descriptions=data.get('descriptions'),
                audio_url=data.get('audio_url'),
                virtual_human_tts_status=data.get('virtual_human_tts_status', False),
                offline_synthesis_tts_status=data.get('offline_synthesis_tts_status', False),
                is_need_training=data.get('is_need_training', False),
                virtual_human_tts_model_path=data.get('virtual_human_tts_model_path'),
                offline_synthesis_tts_model_path=data.get('offline_synthesis_tts_model_path')
            )
            db.session.add(tts)
            db.session.commit()
            return True, tts
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @classmethod
    def get_by_id(cls, id: int) -> Tuple[bool, Union['TTS', str]]:
        try:
            tts = db.session.query(cls).filter_by(id=id).first()
            if tts:
                return True, tts
            return False, 'TTS not found'
        except Exception as e:
            return False, str(e)

    @classmethod
    def list_all(cls) -> Tuple[bool, Union[List['TTS'], str]]:
        try:
            tts_list = db.session.query(cls).all()
            return True, tts_list
        except Exception as e:
            return False, str(e)

    @classmethod
    def update(cls, id: int, data: dict) -> Tuple[bool, Union['TTS', str]]:
        try:
            tts = db.session.query(cls).filter_by(id=id).first()
            if not tts:
                return False, 'TTS not found'

            for key, value in data.items():
                if hasattr(tts, key):
                    setattr(tts, key, value)

            db.session.commit()
            return True, tts
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @classmethod
    def delete(cls, id: int) -> Tuple[bool, str]:
        try:
            tts = db.session.query(cls).filter_by(id=id).first()
            if not tts:
                return False, 'TTS not found'

            db.session.delete(tts)
            db.session.commit()
            return True, 'TTS deleted successfully'
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @classmethod
    def update_all(cls, data: dict) -> Tuple[bool, str]:
        """更新所有记录"""
        try:
            cls.query.update(data)
            db.session.commit()
            return True, "所有记录更新成功"
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @classmethod
    def get_by_status(cls, status_field: str) -> Tuple[bool, Union[Optional['TTS'], str]]:
        """获取指定状态字段为 True 的记录"""
        try:
            tts = db.session.query(cls).filter(getattr(cls, status_field) == True).first()
            if tts:
                return True, tts
            return True, None
        except Exception as e:
            return False, str(e)

