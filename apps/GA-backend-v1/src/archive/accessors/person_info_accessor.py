"""
Person info accessor module.
Manages database operations for person information records.
"""
import uuid
from datetime import datetime
from sqlalchemy import cast, String
from sqlalchemy.inspection import inspect
from .database import db
import logging
logger = logging.getLogger(__name__)
class PersonInfo(db.Model):
    __tablename__ = 'PersonInfo'
    Id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    Guid = db.Column(db.String(36), unique=True, nullable=False)
    Code = db.Column(db.Integer)
    Name = db.Column(db.String(255), nullable=False)
    Sex = db.Column(db.Integer, nullable=False)
    DateOfBirth = db.Column(db.Date)
    Company = db.Column(db.String(255))
    Title = db.Column(db.String(255))
    Introduction = db.Column(db.Text)
    AdditionalInfo = db.Column(db.JSON)
    CreatedBy = db.Column(db.String(255))
    CreatedAt = db.Column(db.TIMESTAMP, default=datetime.now)
    UpdatedBy = db.Column(db.String(255))
    UpdatedAt = db.Column(db.TIMESTAMP, default=datetime.now, onupdate=datetime.now)

    @classmethod
    def add_person(cls, person_data: dict):
        try:
            if 'Sex' in person_data and person_data['Sex'] not in [0, 1]:
                raise ValueError("Sex must be either 0 or 1.")
            
            # Check if Code already exists
            if 'Code' in person_data and person_data['Code'] is not None:
                existing_person = cls.query.filter_by(Code=person_data['Code']).first()
                if existing_person:
                    return False, f"Person with Code {person_data['Code']} already exists"

            person_data['Guid'] = str(uuid.uuid4())
            new_person = cls(**person_data)
            db.session.add(new_person)
            db.session.commit()
            return True, new_person.to_dict()
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @classmethod
    def list_persons(cls, skip: int, take: int):
        try:
            persons = cls.query.order_by(cls.Id).offset(skip).limit(take).all()

            if not persons:
                return True, []

            return True, [person.to_dict() for person in persons]
        except Exception as e:
            return False, str(e)

    @classmethod
    def get_persons_by_codes(cls, codes: list):
        try:
            persons = []
            if codes:
                persons = cls.query.filter(cls.Code.in_(codes)).all()
                if not persons:
                    logger.error("No persons found matching the provided codes.")
            else:
                logger.error("No codes provided.")

            return True, [person.to_dict() for person in persons]
        except Exception as e:
            return False, str(e)

    @classmethod
    def get_person(cls, person_id: int):
        try:
            person = cls.query.filter_by(Id=person_id).first()
            if person:
                return True, person.to_dict()
            else:
                return False, 'Person not found'
        except Exception as e:
            return False, str(e)

    @classmethod
    def get_person_by_code(cls, code: int):
        try:
            person = cls.query.filter_by(Code=code).first()
            if person:
                return True, person.to_dict()
            else:
                return False, 'Person with specified code not found'
        except Exception as e:
            return False, str(e)

    @classmethod
    def query_person(cls, name: str, code_prefix: str, skip: int, take: int):
        try:
            if not name and not code_prefix:
                return False, "Query must include 'name' or 'code' parameter."

            query = cls.query

            if name:
                query = query.filter(cls.Name.like(f'%{name}%'))

            if code_prefix:
                query = query.filter(cast(cls.Code, String).like(f'{code_prefix}%'))

            persons = query.offset(skip).limit(take).all()

            if not persons:
                return False, "No matching records found."

            return True, [person.to_dict() for person in persons]
        except Exception as e:
            return False, str(e)

    @classmethod
    def update_person(cls, person_id: int, update_data: dict):
        try:
            person = cls.query.filter_by(Id=person_id).first()
            if person:
                # Ignore Guid
                update_data.pop('Guid', None)

                if 'Sex' in update_data:
                    if update_data['Sex'] not in [0, 1]:
                        raise ValueError("Sex must be either 0 or 1.")

                for key, value in update_data.items():
                    setattr(person, key, value)
                person.UpdatedAt = datetime.now()
                db.session.commit()
                return True, person.to_dict()
            else:
                return False, 'Person not found'
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @classmethod
    def delete_person(cls, person_id: int):
        try:
            person = cls.query.filter_by(Id=person_id).first()
            if person:
                db.session.delete(person)
                db.session.commit()
                return True, 'Person deleted successfully'
            else:
                return False, 'Person not found'
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    def to_dict(self):
        """Convert model instance to dictionary."""
        return {c.key: getattr(self, c.key)
                for c in inspect(self).mapper.column_attrs}
