"""
Prompt accessor module.
Manages database operations for system prompts used by AI models.
"""
import uuid
from datetime import datetime
from .database import db
from typing import Dict, Any, Tuple, List, Union

class Prompt(db.Model):
    __tablename__ = 'Prompt'
    Id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Guid = db.Column(db.String(36), unique=True, nullable=False)
    GroupId = db.Column(db.Integer, db.ForeignKey('PromptGroup.Id'), nullable=False)
    Code = db.Column(db.String(255), nullable=False)
    Name = db.Column(db.String(255))
    Content = db.Column(db.Text)
    Variables = db.Column(db.JSON)
    Tags = db.Column(db.JSON)
    AdditionalData = db.Column(db.JSON)
    CreatedBy = db.Column(db.String(255))
    CreatedAt = db.Column(db.TIMESTAMP, default=datetime.now)
    UpdatedBy = db.Column(db.String(255))
    UpdatedAt = db.Column(db.TIMESTAMP, default=datetime.now, onupdate=datetime.now)

    # Relationship definition
    prompt_group = db.relationship('PromptGroup', back_populates='prompts')

    @classmethod
    def add_prompt(cls, prompt_data: dict) -> Tuple[bool, Union[Dict[str, Any], str]]:
        try:
            prompt_data['Guid'] = str(uuid.uuid4())
            new_prompt = cls(**prompt_data)
            db.session.add(new_prompt)
            db.session.commit()
            return True, new_prompt.to_dict()
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @classmethod
    def list_prompts(cls, skip: int) -> Tuple[bool, Union[List[Dict[str, Any]], str]]:
        try:
            prompts = cls.query.order_by(cls.Id).offset(skip).all()
            return True, [prompt.to_dict() for prompt in prompts] if prompts else []
        except Exception as e:
            return False, str(e)

    @classmethod
    def list_prompts_by_group_id(cls, group_id: int, skip: int) -> Tuple[bool, Union[List[Dict[str, Any]], str]]:
        try:
            prompts = cls.query.filter_by(GroupId=group_id).order_by(cls.Id).offset(skip).all()

            return True, [prompt.to_dict() for prompt in prompts] if prompts else []
        except Exception as e:
            return False, str(e)

    @classmethod
    def get_prompt(cls, prompt_id: int) -> Tuple[bool, Union[Dict[str, Any], str]]:
        try:
            prompt = cls.query.filter_by(Id=prompt_id).first()
            if prompt:
                return True, prompt.to_dict()
            else:
                return False, 'Prompt not found'
        except Exception as e:
            return False, str(e)

    @classmethod
    def update_prompt(cls, prompt_id: int, update_data: dict) -> Tuple[bool, Union[Dict[str, Any], str]]:
        try:
            prompt = cls.query.filter_by(Id=prompt_id).first()
            if prompt:
                update_data.pop('Guid', None)
                for key, value in update_data.items():
                    setattr(prompt, key, value)
                prompt.UpdatedAt = datetime.now()
                db.session.commit()
                return True, prompt.to_dict()
            else:
                return False, 'Prompt not found'
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @classmethod
    def delete_prompt(cls, prompt_id: int) -> Tuple[bool, str]:
        try:
            prompt = cls.query.filter_by(Id=prompt_id).first()
            if prompt:
                db.session.delete(prompt)
                db.session.commit()
                return True, 'Prompt deleted successfully'
            else:
                return False, 'Prompt not found'
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @classmethod
    def get_prompt_by_code(cls, code: str) -> Tuple[bool, Union[Dict[str, Any], str]]:
        try:
            prompt = cls.query.filter_by(Code=code).first()
            if prompt:
                return True, prompt.to_dict()
            else:
                return False, 'Prompt with specified code not found'
        except Exception as e:
            return False, str(e)

    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary."""
        return {
            'Id': self.Id,
            'Guid': self.Guid,
            'GroupId': self.GroupId,
            'Code': self.Code,
            'Name': self.Name,
            'Content': self.Content,
            'Variables': self.Variables,
            'Tags': self.Tags,
            'AdditionalData': self.AdditionalData,
            'CreatedBy': self.CreatedBy,
            'CreatedAt': self.CreatedAt,
            'UpdatedBy': self.UpdatedBy,
            'UpdatedAt': self.UpdatedAt
        }

