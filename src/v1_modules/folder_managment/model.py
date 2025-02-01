from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from sqlalchemy.dialects.postgresql import UUID

from src.db.base import Base


class Folder(Base):
    __tablename__ = 'folders'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    parent_folder_id = Column(UUID(as_uuid=True), ForeignKey('folders.id'), nullable=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="folders")
    files = relationship("File", back_populates="folder")
    permissions = relationship("UserFolderPermission", back_populates="folder")

class File(Base):
    __tablename__ = 'files'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    folder_id = Column(UUID(as_uuid=True), ForeignKey('folders.id'), nullable=False)
    uploaded_by_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    file_type = Column(String(50), nullable=True)
    file_size = Column(BigInteger, nullable=True)

    folder = relationship("Folder", back_populates="files")

    uploaded_by = relationship("User", back_populates="files")


class UserFolderPermission(Base):
    __tablename__ = 'user_folder_permissions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    folder_id = Column(UUID(as_uuid=True), ForeignKey('folders.id'), nullable=False)
    can_view = Column(Boolean, default=False)
    can_edit = Column(Boolean, default=False)
    can_delete = Column(Boolean, default=False)
    can_create = Column(Boolean, default=False)
    can_share = Column(Boolean, default=False)

    user = relationship("User", back_populates="folder_permissions")
    folder = relationship("Folder", back_populates="permissions")


class SharedItem(Base):
    __tablename__ = 'shared_items'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_type = Column(String(10), nullable=False)
    item_id = Column(Integer, nullable=False)
    shared_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    shared_with = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    shared_at = Column(DateTime(timezone=True), server_default=func.now())
    share_type = Column(String(20), nullable=True)