"""Database setup. SQLite by default for local dev; set DATABASE_URL for Postgres."""
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()  # a backend/.env file works too, not just real environment vars

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./rosterflow.db")
# Always use the psycopg2 driver (the one in requirements.txt). Render
# provides postgres:// URLs; Supabase provides postgresql:// URLs. A bare
# postgresql:// makes SQLAlchemy 2.0 default to the psycopg (v3) driver,
# which is NOT installed -- that crashed the backend on Vercel+Supabase
# with "No module named 'psycopg'". So pin the driver explicitly, unless
# the URL already names one (postgresql+...://).
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = "postgresql+psycopg2://" + DATABASE_URL[len("postgres://"):]
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = "postgresql+psycopg2://" + DATABASE_URL[len("postgresql://"):]

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True,
                       pool_pre_ping=True)  # drop stale pooled connections (serverless hosts)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


_initialized = False


def ensure_initialized():
    """Create tables and seed demo data on first use (once per process).

    Serverless hosts (Vercel) may not run FastAPI lifespan startup events,
    so get_db() calls this too: the first real API request initializes the
    database. The flag is only set after success, so a failed seed (e.g. a
    concurrent cold start racing it) is retried on the next request.
    """
    global _initialized
    if _initialized:
        return
    init_db()
    db = SessionLocal()
    try:
        from .models import User
        if db.query(User).count() == 0:
            from . import seed as _seed
            _seed.run(db)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    _initialized = True


def get_db():
    ensure_initialized()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from . import models  # noqa: F401  (register models)
    Base.metadata.create_all(bind=engine)
