"""
Admin account accessor module.
Provides database model and authentication methods for admin user accounts.
"""
from werkzeug.security import check_password_hash
from .database import db
from typing import Optional

class AdminAccount(db.Model):
    __tablename__ = 'AdminAccounts'
    ID = db.Column(db.Integer, primary_key=True)
    Username = db.Column(db.String(255), unique=True, nullable=False)
    PasswordHash = db.Column(db.String(255), nullable=False)

    @classmethod
    def authenticate(cls, username: str, password: str) -> Optional['AdminAccount']:
        user = cls.query.filter_by(Username=username).first()
        if user and check_password_hash(user.PasswordHash, password):
            return user
        else:
            return None
