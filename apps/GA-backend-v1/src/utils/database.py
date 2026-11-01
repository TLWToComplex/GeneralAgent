"""
Database connection module.
Initializes SQLAlchemy DB instance for application-wide database access.
"""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
