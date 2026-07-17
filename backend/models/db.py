from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timezone
from config import Config
import uuid

_connect_args = {"check_same_thread": False} if Config.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(Config.DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    file_name = Column(String(255), nullable=True)
    file_path = Column(String(500), nullable=True)
    file_md5 = Column(String(32), nullable=True)
    text_md5 = Column(String(32), nullable=True)
    raw_text = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    progress = Column(Integer, nullable=False, default=0)
    result = Column(Text, nullable=True)
    error_msg = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "file_name": self.file_name,
            "status": self.status,
            "progress": self.progress,
            "result": self.result,
            "error_msg": self.error_msg,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "raw_text": self.raw_text,
        }


class Material(Base):
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    tags = Column(String(500), nullable=True)
    type = Column(String(20), nullable=False, default="image")
    upload_time = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "file_path": self.file_path,
            "tags": self.tags.split(",") if self.tags else [],
            "tags_str": self.tags or "",
            "type": self.type,
            "upload_time": self.upload_time.isoformat() if self.upload_time else None,
        }


def init_db():
    Base.metadata.create_all(bind=engine, checkfirst=True)
