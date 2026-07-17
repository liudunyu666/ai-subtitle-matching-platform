from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
import uuid

db = SQLAlchemy()


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    file_name = db.Column(db.String(255), nullable=True)
    file_path = db.Column(db.String(500), nullable=True)
    file_md5 = db.Column(db.String(32), nullable=True)
    text_md5 = db.Column(db.String(32), nullable=True)
    raw_text = db.Column(db.Text, nullable=True)
    status = db.Column(
        db.String(20),
        nullable=False,
        default="pending",
    )
    progress = db.Column(db.Integer, nullable=False, default=0)
    result = db.Column(db.Text, nullable=True)
    error_msg = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
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
        }


class Material(db.Model):
    __tablename__ = "materials"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    tags = db.Column(db.String(500), nullable=True)
    type = db.Column(db.String(20), nullable=False, default="image")
    upload_time = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

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
