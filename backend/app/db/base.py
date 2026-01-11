from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Declarative base class for ORM models.

    Design considerations:
    - Centralizes metadata for Alembic autogeneration and schema management.
    """
    pass
