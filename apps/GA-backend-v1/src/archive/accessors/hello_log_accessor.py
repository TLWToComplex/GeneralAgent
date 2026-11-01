"""
Hello log accessor module.
Manages database operations for tracking system hello messages and interactions.
"""
from .database import db


class HelloLog(db.Model):
    __tablename__ = 'HelloLog'
    Id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    Code = db.Column(db.Integer)
    CreatedAt = db.Column(db.TIMESTAMP, default=db.func.current_timestamp())

    @classmethod
    def add_log_records(cls, codes: list):
        new_records = []
        try:
            for code in codes:
                new_record = cls(Code=code)
                db.session.add(new_record)
                new_records.append(new_record)
            db.session.commit()
            return True, new_records
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @classmethod
    def get_logs_by_code(cls, code: int):
        try:
            logs = cls.query.filter_by(Code=code).all()
            return True, logs
        except Exception as e:
            return False, str(e)

    def to_dict(self):
        return {
            'Id': self.Id,
            'Code': self.Code,
            'CreatedAt': self.CreatedAt.strftime("%Y-%m-%d %H:%M:%S") if self.CreatedAt else None
        }
