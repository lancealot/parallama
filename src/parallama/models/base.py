"""Base model for SQLAlchemy models."""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import Column, String, DateTime
from sqlalchemy.ext.declarative import declared_attr

from ..core.database import Base

class BaseModel(Base):
    """Base model with common fields and functionality."""

    __abstract__ = True

    @declared_attr
    def __tablename__(cls) -> str:
        """Get table name from class name.
        
        Returns:
            str: Table name in plural form
        """
        # Convert CamelCase to snake_case and pluralize
        name = cls.__name__
        # Insert underscore between lower and upper case letters
        name = ''.join(['_'+c.lower() if c.isupper() else c.lower() for c in name]).lstrip('_')
        # Pluralize by adding 's'
        return name + 's'

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))

    def __init__(self, **kwargs):
        """Initialize model with optional fields.
        
        Args:
            **kwargs: Model attributes
        """
        # Set created_at if not provided
        if 'created_at' not in kwargs:
            kwargs['created_at'] = datetime.now(timezone.utc)
        
        super().__init__(**kwargs)

    def update(self, **kwargs) -> None:
        """Update model attributes.
        
        Args:
            **kwargs: Attributes to update
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        """Convert model to dictionary.
        
        Returns:
            dict: Dictionary representation of model
        """
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                value = value.isoformat()
            result[column.name] = value
        return result

    def __repr__(self) -> str:
        """Get string representation of model.
        
        Returns:
            str: String representation
        """
        values = []
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                value = value.isoformat()
            values.append(f"{column.name}={value}")
        return f"{self.__class__.__name__}({', '.join(values)})"
