"""Base model configuration for SQLAlchemy models."""
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy import Column, DateTime, String, event
import uuid

Base = declarative_base()

class BaseModel(Base):
    """Abstract base model with common fields."""
    __abstract__ = True
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

@event.listens_for(BaseModel, 'before_insert', propagate=True)
def convert_uuid_before_insert(mapper, connection, target):
    """Convert UUID fields to strings before insert."""
    for column in mapper.columns:
        value = getattr(target, column.key)
        if isinstance(value, uuid.UUID):
            setattr(target, column.key, str(value))

@event.listens_for(BaseModel, 'before_update', propagate=True)
def convert_uuid_before_update(mapper, connection, target):
    """Convert UUID fields to strings before update."""
    for column in mapper.columns:
        value = getattr(target, column.key)
        if isinstance(value, uuid.UUID):
            setattr(target, column.key, str(value))
