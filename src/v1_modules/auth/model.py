from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
import uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from src.db.base import Base
from src.v1_modules.folder_managment.model import *

class Role(Base):
    __tablename__ = 'roles'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(20), unique=True, nullable=False)
    can_view = Column(Boolean, default=False)
    can_edit = Column(Boolean, default=False)
    can_delete = Column(Boolean, default=False)
    can_create = Column(Boolean, default=False)
    can_share = Column(Boolean, default=False)

    users = relationship("User", back_populates="role_details")

class User(Base):
    __tablename__ = 'users'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role_id = Column(UUID(as_uuid=True), ForeignKey('roles.id'), nullable=False)  # Changed to UUID
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)

    role_details = relationship("Role", back_populates="users")

    folders = relationship("Folder", back_populates="owner")
    files = relationship("File", back_populates="uploaded_by")
    folder_permissions = relationship("UserFolderPermission", back_populates="user")

    @classmethod
    def get_by_id(cls, db_session, user_id: int):
        """
        Fetch a user by ID.

        :param db_session: SQLAlchemy session instance
        :param user_id: ID of the user to fetch
        :return: User object if found, else None
        """
        return db_session.query(cls).filter(cls.id == user_id).first()