"""
Configuration accessor module.
Manages database operations for system configuration settings.
"""
from sqlalchemy.dialects.mysql import JSON
from .database import db
from datetime import datetime
from typing import Dict, Any, Tuple, Union

class Configuration(db.Model):
    __tablename__ = 'Configurations'
    ID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Name = db.Column(db.String(255), nullable=False, unique=True)
    Value = db.Column(JSON, nullable=True)
    Description = db.Column(db.Text)
    CreatedAt = db.Column(db.TIMESTAMP, default=datetime.now)
    UpdatedAt = db.Column(db.TIMESTAMP, default=datetime.now, onupdate=datetime.now)

    @classmethod
    def get_all_configurations(cls) -> Tuple[bool, Union[Dict[str, Dict[str, Any]], str]]:
        try:
            configurations = cls.query.all()
            return True, {config.Name: {"value": config.Value, "description": config.Description} for config in
                          configurations}
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @classmethod
    def update_configuration(cls, name: str, value: dict, description: str = None) -> Tuple[bool, Union[Dict[str, Any], str]]:
        try:
            config = cls.query.filter_by(Name=name).first()
            if config:
                config.Value = value
                if description is not None:
                    config.Description = description
                db.session.commit()
                return True, config.to_dict()
            else:
                return False, "Configuration not found."
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @classmethod
    def add_configuration(cls, name: str, value: dict, description: str = None) -> Tuple[bool, Union[Dict[str, Any], str]]:
        try:
            new_config = cls(Name=name, Value=value, Description=description)
            db.session.add(new_config)
            db.session.commit()
            return True, new_config.to_dict()
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @classmethod
    def delete_configuration(cls, name: str) -> Tuple[bool, str]:
        try:
            config = cls.query.filter_by(Name=name).first()
            if config:
                db.session.delete(config)
                db.session.commit()
                return True, f'Configuration {name} deleted successfully.'
            else:
                return False, "Configuration not found."
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'Name': self.Name,
            'Value': self.Value,
            'Description': self.Description,
            'CreatedAt': self.CreatedAt.isoformat(),
            'UpdatedAt': self.UpdatedAt.isoformat()
        }
