"""
EdgeMind NPU - Database Manager
Handles all database operations with SQLAlchemy.
"""

import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker, Session, selectinload

from src.config import DATABASE_URL
from src.database.models import Base, Conversation, Message, Memory, ModelMetadata

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Singleton database manager for all operations."""

    _instance: Optional['DatabaseManager'] = None
    _engine = None
    _Session = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._init_db()

    def _init_db(self):
        """Initialize database connection and create tables."""
        try:
            self._engine = create_engine(
                DATABASE_URL,
                echo=False,
                connect_args={"check_same_thread": False},
                pool_pre_ping=True,
            )
            Base.metadata.create_all(self._engine)
            # expire_on_commit=False keeps returned ORM objects usable after
            # the session closes (callers read attributes on detached objects)
            self._Session = sessionmaker(bind=self._engine, expire_on_commit=False)
            logger.info(f"Database initialized at {DATABASE_URL}")
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            raise

    def _get_session(self) -> Session:
        """Get a new database session."""
        return self._Session()

    # ── Conversation Operations ──────────────────────────────────

    def create_conversation(self, title: str = "New Chat",
                           model_id: str = "",
                           system_prompt: str = "") -> Conversation:
        """Create a new conversation."""
        session = self._get_session()
        try:
            conv = Conversation(
                title=title,
                model_id=model_id,
                system_prompt=system_prompt,
            )
            session.add(conv)
            session.commit()
            session.refresh(conv)
            logger.info(f"Created conversation: {conv.id}")
            return conv
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating conversation: {e}")
            raise
        finally:
            session.close()

    def get_conversation(self, conv_id: str) -> Optional[Conversation]:
        """Get a conversation by ID (with messages eagerly loaded)."""
        session = self._get_session()
        try:
            return (
                session.query(Conversation)
                .options(selectinload(Conversation.messages))
                .filter(Conversation.id == conv_id)
                .first()
            )
        finally:
            session.close()

    def get_all_conversations(self, include_archived: bool = False) -> List[Conversation]:
        """Get all conversations, optionally including archived ones."""
        session = self._get_session()
        try:
            query = (
                session.query(Conversation)
                .options(selectinload(Conversation.messages))
            )
            if not include_archived:
                query = query.filter(Conversation.is_archived == False)
            return query.order_by(desc(Conversation.updated_at)).all()
        finally:
            session.close()

    def update_conversation(self, conv_id: str, **kwargs) -> bool:
        """Update conversation fields."""
        session = self._get_session()
        try:
            conv = session.query(Conversation).filter(Conversation.id == conv_id).first()
            if not conv:
                return False
            for key, value in kwargs.items():
                if hasattr(conv, key):
                    setattr(conv, key, value)
            conv.updated_at = datetime.utcnow()
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating conversation: {e}")
            return False
        finally:
            session.close()

    def delete_conversation(self, conv_id: str) -> bool:
        """Delete a conversation and all its messages."""
        session = self._get_session()
        try:
            conv = session.query(Conversation).filter(Conversation.id == conv_id).first()
            if not conv:
                return False
            session.delete(conv)
            session.commit()
            logger.info(f"Deleted conversation: {conv_id}")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting conversation: {e}")
            return False
        finally:
            session.close()

    def search_conversations(self, query: str) -> List[Conversation]:
        """Search conversations by title."""
        session = self._get_session()
        try:
            return session.query(Conversation).filter(
                Conversation.title.ilike(f"%{query}%"),
                Conversation.is_archived == False,
            ).order_by(desc(Conversation.updated_at)).all()
        finally:
            session.close()

    def auto_title_conversation(self, conv_id: str, first_message: str):
        """Auto-generate a title from the first user message."""
        # Simple: take first 50 chars of the message
        title = first_message[:50].strip()
        if len(first_message) > 50:
            title += "..."
        self.update_conversation(conv_id, title=title)

    # ── Message Operations ───────────────────────────────────────

    def add_message(self, conversation_id: str, role: str, content: str,
                    model_id: str = "", tokens_used: int = 0,
                    latency_ms: float = 0.0,
                    attachments: list = None) -> Message:
        """Add a message to a conversation."""
        session = self._get_session()
        try:
            msg = Message(
                conversation_id=conversation_id,
                role=role,
                content=content,
                model_id=model_id,
                tokens_used=tokens_used,
                latency_ms=latency_ms,
                attachments=attachments or [],
            )
            session.add(msg)

            # Update conversation timestamp
            conv = session.query(Conversation).filter(
                Conversation.id == conversation_id).first()
            if conv:
                conv.updated_at = datetime.utcnow()

            session.commit()
            session.refresh(msg)
            return msg
        except Exception as e:
            session.rollback()
            logger.error(f"Error adding message: {e}")
            raise
        finally:
            session.close()

    def get_messages(self, conversation_id: str) -> List[Message]:
        """Get all messages for a conversation, ordered by time."""
        session = self._get_session()
        try:
            return session.query(Message).filter(
                Message.conversation_id == conversation_id
            ).order_by(Message.created_at).all()
        finally:
            session.close()

    def delete_message(self, msg_id: str) -> bool:
        """Delete a specific message."""
        session = self._get_session()
        try:
            msg = session.query(Message).filter(Message.id == msg_id).first()
            if not msg:
                return False
            session.delete(msg)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting message: {e}")
            return False
        finally:
            session.close()

    # ── Memory Operations ────────────────────────────────────────

    def add_memory(self, key: str, content: str, category: str = "general") -> Memory:
        """Add or update a memory entry."""
        session = self._get_session()
        try:
            existing = session.query(Memory).filter(Memory.key == key).first()
            if existing:
                existing.content = content
                existing.category = category
                existing.updated_at = datetime.utcnow()
                session.commit()
                session.refresh(existing)
                return existing

            memory = Memory(key=key, content=content, category=category)
            session.add(memory)
            session.commit()
            session.refresh(memory)
            return memory
        except Exception as e:
            session.rollback()
            logger.error(f"Error adding memory: {e}")
            raise
        finally:
            session.close()

    def get_memories(self, category: Optional[str] = None) -> List[Memory]:
        """Get all active memories, optionally filtered by category."""
        session = self._get_session()
        try:
            query = session.query(Memory).filter(Memory.is_active == True)
            if category:
                query = query.filter(Memory.category == category)
            return query.all()
        finally:
            session.close()

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory entry."""
        session = self._get_session()
        try:
            mem = session.query(Memory).filter(Memory.id == memory_id).first()
            if not mem:
                return False
            session.delete(mem)
            session.commit()
            return True
        except Exception:
            session.rollback()
            return False
        finally:
            session.close()

    def get_memory_context(self) -> str:
        """Get all active memories formatted for LLM context."""
        memories = self.get_memories()
        if not memories:
            return ""
        lines = ["[User-approved memory entries:]"]
        for mem in memories:
            lines.append(f"- {mem.key}: {mem.content}")
        return "\n".join(lines)

    # ── Model Metadata Operations ────────────────────────────────

    def save_model_metadata(self, model_id: str, **kwargs) -> ModelMetadata:
        """Save or update model metadata."""
        session = self._get_session()
        try:
            existing = session.query(ModelMetadata).filter(ModelMetadata.id == model_id).first()
            if existing:
                for key, value in kwargs.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                session.commit()
                session.refresh(existing)
                return existing

            meta = ModelMetadata(id=model_id, **kwargs)
            session.add(meta)
            session.commit()
            session.refresh(meta)
            return meta
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving model metadata: {e}")
            raise
        finally:
            session.close()

    def get_model_metadata(self, model_id: str) -> Optional[ModelMetadata]:
        """Get model metadata by ID."""
        session = self._get_session()
        try:
            return session.query(ModelMetadata).filter(ModelMetadata.id == model_id).first()
        finally:
            session.close()

    def get_all_models(self) -> List[ModelMetadata]:
        """Get all model metadata entries."""
        session = self._get_session()
        try:
            return session.query(ModelMetadata).all()
        finally:
            session.close()

    def delete_model_metadata(self, model_id: str) -> bool:
        """Delete model metadata."""
        session = self._get_session()
        try:
            meta = session.query(ModelMetadata).filter(ModelMetadata.id == model_id).first()
            if not meta:
                return False
            session.delete(meta)
            session.commit()
            return True
        except Exception:
            session.rollback()
            return False
        finally:
            session.close()

    # ── Export/Import ─────────────────────────────────────────────

    def export_conversation(self, conv_id: str) -> Optional[dict]:
        """Export a conversation with all its messages as a dictionary."""
        conv = self.get_conversation(conv_id)
        if not conv:
            return None

        return {
            "conversation": conv.to_dict(),
            "messages": [m.to_dict() for m in conv.messages],
            "exported_at": datetime.utcnow().isoformat(),
            "app_version": "1.0.0",
        }

    def import_conversation(self, data: dict) -> Optional[str]:
        """Import a conversation from exported data. Returns new conversation ID."""
        conv_data = data.get("conversation", {})
        messages_data = data.get("messages", [])

        conv = self.create_conversation(
            title=conv_data.get("title", "Imported Chat"),
            model_id=conv_data.get("model_id", ""),
            system_prompt=conv_data.get("system_prompt", ""),
        )

        for msg_data in messages_data:
            self.add_message(
                conversation_id=conv.id,
                role=msg_data.get("role", "user"),
                content=msg_data.get("content", ""),
                model_id=msg_data.get("model_id", ""),
                tokens_used=msg_data.get("tokens_used", 0),
                latency_ms=msg_data.get("latency_ms", 0.0),
                attachments=msg_data.get("attachments", []),
            )

        logger.info(f"Imported conversation: {conv.id}")
        return conv.id
