from datetime import datetime
from typing import List, Optional
from uuid import UUID
from enum import Enum

# Pydantic models for request/response
from pydantic import BaseModel, EmailStr, ConfigDict


class PermissionType(str, Enum):
    EDITOR = "editor"
    VIEWER = "viewer"

class FolderCreate(BaseModel):
    name: str
    parent_folder_id: Optional[UUID] = None

class FileResponse(BaseModel):
    id: UUID
    filename: str
    file_type: Optional[str]
    file_size: Optional[int]

    model_config = ConfigDict(from_attributes=True)

class FolderResponse(BaseModel):
    id: UUID
    name: str
    files: List['FileResponse']
    subfolders: List['FolderResponse']
    parent_folder_id: Optional[UUID] = None
    owner_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ShareItemRequest(BaseModel):
    email: EmailStr
    permission_type: PermissionType
