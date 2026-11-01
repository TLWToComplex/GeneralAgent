"""
Prompt group accessor module.
Manages database operations for grouping and organizing system prompts.
"""
import uuid
from datetime import datetime
from sqlalchemy.inspection import inspect
from .database import db
from .prompt_accessor import Prompt
from typing import Dict, Any, Tuple, List, Union
class PromptGroup(db.Model):
    __tablename__ = 'PromptGroup'
    Id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Guid = db.Column(db.String(36), unique=True, nullable=False)
    Name = db.Column(db.String(255))
    Description = db.Column(db.Text)
    IconPath = db.Column(db.String(255))
    AdditionalData = db.Column(db.JSON)
    CreatedBy = db.Column(db.String(255))
    CreatedAt = db.Column(db.TIMESTAMP, default=datetime.now)
    UpdatedBy = db.Column(db.String(255))
    UpdatedAt = db.Column(db.TIMESTAMP, default=datetime.now, onupdate=datetime.now)
    
     # Relationship definition
    prompts = db.relationship('Prompt', back_populates='prompt_group')

    @classmethod
    def add_prompt_group(cls, group_data: dict) -> Tuple[bool, Union[Dict[str, Any], str]]:
        try:
            group_data['Guid'] = str(uuid.uuid4())
            new_group = cls(**group_data)
            db.session.add(new_group)
            db.session.commit()
            return True, new_group.to_dict()
        except Exception as e:
            db.session.rollback()
            return False, str(e)
        
    @classmethod
    def list_prompt_groups_with_count(cls) -> Tuple[bool, Union[List[Dict[str, Any]], str]]:
        try:
            groups = cls.query.all()
            if not groups:
                return True, []
            
            # 计算每个group下的prompts数量
            group_counts = {group.Id: len(group.prompts) for group in groups}
            
            return True, [{**group.to_dict(), 'prompt_count': group_counts[group.Id]} for group in groups]
        except Exception as e:
            return False, str(e)
      
    @classmethod
    def get_group_id_by_name(cls, group_name: str) -> Tuple[bool, Union[int, str]]:
        try:
            group = cls.query.filter_by(Name=group_name).first()
            if group:
                return True, group.Id
            else:
                return False, "No prompt group found with the specified name."
        except Exception as e:
            return False, str(e)

    @classmethod
    def get_prompt_group(cls, group_id: int) -> Tuple[bool, Union[Dict[str, Any], str]]:
        try:
            group = cls.query.filter_by(Id=group_id).first()
            if group:
                return True, group.to_dict()
            else:
                return False, 'Prompt group not found'
        except Exception as e:
            return False, str(e)

    @classmethod
    def update_prompt_group(cls, group_id: int, update_data: dict) -> Tuple[bool, Union[Dict[str, Any], str]]:
        try:
            group = cls.query.filter_by(Id=group_id).first()
            if group:
                update_data.pop('Guid', None)
                for key, value in update_data.items():
                    setattr(group, key, value)
                group.UpdatedAt = datetime.now()
                db.session.commit()
                return True, group.to_dict()
            else:
                return False, 'Prompt group not found'
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @classmethod
    def delete_prompt_group(cls, group_id: int) -> Tuple[bool, str]:
        try:
            group = cls.query.filter_by(Id=group_id).first()
            if group:
                # 删除所有与该group关联的prompts
                db.session.query(Prompt).filter_by(GroupId=group_id).delete()
                db.session.delete(group)
                db.session.commit()
                return True, 'Prompt group and its prompts deleted successfully'
            else:
                return False, 'Prompt group not found'
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary."""
        return {c.key: getattr(self, c.key)
                for c in inspect(self).mapper.column_attrs}
