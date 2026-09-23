"""Clase base declarativa de SQLAlchemy 2.0."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Clase base de la que heredan todos los modelos ORM del microservicio ms-segip."""

    pass
