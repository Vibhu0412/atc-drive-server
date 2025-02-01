
from typing import List, Optional
from uuid import UUID
from enum import Enum

# Pydantic models for request/response
from pydantic import BaseModel, EmailStr

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

class FolderResponse(BaseModel):
    id: UUID
    name: str
    files: List[FileResponse]
    subfolders: List['FolderResponse']

class ShareItemRequest(BaseModel):
    email: EmailStr
    permission_type: PermissionType
