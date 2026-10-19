from sqlalchemy.orm import declarative_base

Base = declarative_base()
Base.__table_args__ = {"extend_existing": True}
