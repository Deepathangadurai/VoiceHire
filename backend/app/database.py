"""SQLAlchemy database setup - SQLite for local-first, swap DATABASE_URL for PostgreSQL."""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./voicehire.db")

# SQLite-compatible engine (use pool_pre_ping for PostgreSQL)
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables."""
    from app.email import models  # noqa: F401 - registers models
    Base.metadata.create_all(bind=engine)
