"""
EdgeMind NPU - Database Models
SQLAlchemy models for all database tables.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean, DateTime,
    ForeignKey, JSON
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def generate_id():
    """Generate a unique ID."""
    return str(uuid.uuid4())


class Conversation(Base):
    """Represents a chat conversation."""
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=generate_id)
    title = Column(String(500), default="New Chat")
    model_id = Column(String(100), default="")
    system_prompt = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_pinned = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    metadata_json = Column(JSON, default=dict)

    messages = relationship(
        "Message", back_populates="conversation",
        cascade="all, delete-orphan", order_by="Message.created_at"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "model_id": self.model_id,
            "system_prompt": self.system_prompt,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_pinned": self.is_pinned,
            "is_archived": self.is_archived,
            "message_count": len(self.messages) if self.messages else 0,
        }


class Message(Base):
    """Represents a single message in a conversation."""
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=generate_id)
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=False)
    role = Column(String(20), nullable=False)  # "user", "assistant", "system"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    model_id = Column(String(100), default="")
    tokens_used = Column(Integer, default=0)
    latency_ms = Column(Float, default=0.0)
    metadata_json = Column(JSON, default=dict)

    # File attachments info
    attachments = Column(JSON, default=list)

    conversation = relationship("Conversation", back_populates="messages")

    def to_dict(self):
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "model_id": self.model_id,
            "tokens_used": self.tokens_used,
            "latency_ms": self.latency_ms,
            "attachments": self.attachments or [],
        }


class Memory(Base):
    """User-approved memory entries that persist across conversations."""
    __tablename__ = "memories"

    id = Column(String(36), primary_key=True, default=generate_id)
    key = Column(String(200), nullable=False, unique=True)
    content = Column(Text, nullable=False)
    category = Column(String(100), default="general")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    def to_dict(self):
        return {
            "id": self.id,
            "key": self.key,
            "content": self.content,
            "category": self.category,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_active": self.is_active,
        }


class ModelMetadata(Base):
    """Metadata about downloaded and available models."""
    __tablename__ = "model_metadata"

    id = Column(String(100), primary_key=True)  # model_id
    name = Column(String(200), nullable=False)
    family = Column(String(50), default="")
    file_path = Column(String(1000), default="")
    file_size_bytes = Column(Integer, default=0)
    format_type = Column(String(50), default="gguf")  # gguf, openvino, onnx
    status = Column(String(50), default="available")  # available, downloading, installed, error
    download_progress = Column(Float, default=0.0)
    context_length = Column(Integer, default=4096)
    parameters = Column(String(50), default="")
    quantization = Column(String(50), default="")
    backend_used = Column(String(50), default="")
    is_downloaded = Column(Boolean, default=False)
    last_used = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "family": self.family,
            "file_path": self.file_path,
            "file_size_bytes": self.file_size_bytes,
            "file_size_human": self._human_size(self.file_size_bytes),
            "format_type": self.format_type,
            "status": self.status,
            "download_progress": self.download_progress,
            "context_length": self.context_length,
            "parameters": self.parameters,
            "quantization": self.quantization,
            "backend_used": self.backend_used,
            "is_downloaded": self.is_downloaded,
            "last_used": self.last_used.isoformat() if self.last_used else None,
        }

    @staticmethod
    def _human_size(size_bytes: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
