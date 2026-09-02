import os
import sys
import importlib.util
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Load project root's database.models module directly to avoid shadowing by backend.database module
_models_path = os.path.join(PROJECT_ROOT, "database", "models.py")
_spec = importlib.util.spec_from_file_location("database.models", _models_path)
_db_models = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_db_models)
Base = _db_models.Base

# Use project root database
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_URL = f"sqlite:///{os.path.join(PROJECT_ROOT, 'trustbridge.db')}"

engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_db_session() -> Session:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db_session_direct() -> Session:
    return SessionLocal()