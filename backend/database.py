import os
import shutil
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

load_dotenv()


def _database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if url:
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql://", 1)
        return url

    if os.getenv("VERCEL"):
        tmp_db = "/tmp/signal.db"
        bundled = os.path.join(os.path.dirname(__file__), "signal.db")
        if not os.path.exists(tmp_db) and os.path.exists(bundled):
            shutil.copy(bundled, tmp_db)
        return f"sqlite:///{tmp_db}"

    return "sqlite:///./signal.db"


SQLALCHEMY_DATABASE_URL = _database_url()

_connect_args = {"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
