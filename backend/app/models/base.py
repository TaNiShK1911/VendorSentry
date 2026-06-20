"""
Base declarative class shared across all models.
Keeps the import chain simple — every model imports Base from here.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
