"""Database models and configuration for chat history."""

import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import create_engine, Column, String, DateTime, Text, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.pool import QueuePool

logger = logging.getLogger(__name__)

# Database URL from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://user:password@localhost:5432/odpc_chatdb"
)

def create_optimized_engine():
    """Create database engine with proper connection pooling"""
    return create_engine(
        DATABASE_URL,
        poolclass=QueuePool,
        pool_size=5,              # Number of connections to keep open
        max_overflow=10,          # Max connections beyond pool_size
        pool_timeout=30,          # Seconds to wait for connection
        pool_recycle=3600,        # Recycle connections after 1 hour
        pool_pre_ping=True,       # Verify connections before using
        echo=False                # Set to True for SQL query logging
    )

# Create engine and session
engine = create_optimized_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class ChatMessage(Base):
    """Model for storing chat messages in PostgreSQL"""
    __tablename__ = "chat_messages"
    
    message_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    user_message = Column(Text, nullable=True)
    system_message = Column(Text, nullable=True)
    response = Column(Text, nullable=True)
    sources = Column(Text, nullable=True)  # JSON string of sources
    tokens_used = Column(Integer, nullable=True)
    timestamp = Column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    
    def __repr__(self):
        return f"<ChatMessage(message_id={self.message_id}, session_id={self.session_id}, role={self.role})>"


def init_db():
    """Initialize database tables"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise


def get_db():
    """Dependency for getting database sessions"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Test database connection
def test_connection():
    """Test database connection"""
    try:
        with engine.connect() as conn:
            logger.info("Successfully connected to PostgreSQL database")
            return True
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return False