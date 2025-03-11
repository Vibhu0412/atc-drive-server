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
    parent_folder_id = Column(UUID(as_uuid=True), ForeignKey('folders.id', ondelete="CASCADE"), nullable=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="folders")
    files = relationship("File", back_populates="folder", cascade="all, delete-orphan")
    permissions = relationship("UserFolderPermission", back_populates="folder", cascade="all, delete-orphan")
    parent_folder = relationship("Folder", remote_side=[id], back_populates="subfolders")
    subfolders = relationship("Folder", back_populates="parent_folder", cascade="all, delete-orphan")

class File(Base):
    __tablename__ = 'files'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    folder_id = Column(UUID(as_uuid=True), ForeignKey('folders.id', ondelete="CASCADE"), nullable=False)
    uploaded_by_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    file_type = Column(String(100), nullable=True)
    file_size = Column(BigInteger, nullable=True)

    folder = relationship("Folder", back_populates="files")
    uploaded_by = relationship("User", back_populates="files")
    permissions = relationship("UserFilePermission", back_populates="file", cascade="all, delete-orphan")

class UserFolderPermission(Base):
    __tablename__ = 'user_folder_permissions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    folder_id = Column(UUID(as_uuid=True), ForeignKey('folders.id', ondelete="CASCADE"), nullable=False)
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
    item_id = Column(UUID(as_uuid=True), nullable=False)  # Changed from Integer to UUID
    shared_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    shared_with = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    shared_at = Column(DateTime(timezone=True), server_default=func.now())
    share_type = Column(String(20), nullable=True)


class UserFilePermission(Base):
    __tablename__ = 'user_file_permissions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    file_id = Column(UUID(as_uuid=True), ForeignKey('files.id', ondelete="CASCADE"), nullable=False)
    can_view = Column(Boolean, default=False)
    can_edit = Column(Boolean, default=False)
    can_delete = Column(Boolean, default=False)
    can_share = Column(Boolean, default=False)

    user = relationship("User", back_populates="file_permissions")
    file = relationship("File", back_populates="permissions")