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

from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import List, Optional

class FileResponse(BaseModel):
    id: UUID
    filename: str
    file_path: str
    folder_id: UUID
    uploaded_by_id: UUID
    uploaded_at: datetime
    file_type: Optional[str] = None
    file_size: Optional[int] = None

class FolderResponse(BaseModel):
    id: UUID
    name: str
    files: List[FileResponse]
    subfolders: List['FolderResponse']
    parent_folder_id: Optional[UUID] = None
    owner_id: UUID  # Ensure this field is required
    created_at: datetime  # Ensure this field is required

    model_config = ConfigDict(from_attributes=True)

from pydantic import BaseModel
from typing import Literal

class ShareItemRequest(BaseModel):
    item_type: Literal["file", "folder"]  # Type of item to share
    item_id: UUID  # ID of the file or folder
    shared_with_user_id: UUID  # ID of the user with whom the item is shared
    share_type: Optional[str] = None

from pydantic import BaseModel, UUID4, validator
from typing import Optional, List
from datetime import datetime


# Base Models
class UserBase(BaseModel):
    id: UUID4
    username: str
    email: str

    class Config:
        from_attributes = True




class ShareBulkRequest(BaseModel):
    shared_with_ids: List[UUID4]

    @validator('shared_with_ids')
    def validate_shared_with_ids(cls, v):
        if not v:
            raise ValueError("At least one user ID must be provided")
        return v


# Share Response Models
class ShareResponse(BaseModel):
    message: str


class ShareDetailResponse(BaseModel):
    item_id: UUID4
    item_type: str
    shared_by: UserBase
    shared_with: UserBase
    shared_at: datetime
    share_type: str

    class Config:
        from_attributes = True


class ShareListResponse(BaseModel):
    items: List[ShareDetailResponse]
    total_count: int


# Permission Models
class PermissionBase(BaseModel):
    can_view: bool = True
    can_edit: bool = False
    can_delete: bool = False
    can_share: bool = False


class UpdateSharePermissionsRequest(PermissionBase):
    pass


# Share Status Models
class SharedItemStatus(BaseModel):
    is_shared: bool
    shared_with: List[UserBase] = []
    shared_by: Optional[UserBase] = None
    permissions: Optional[PermissionBase] = None

    class Config:
        from_attributes = True


# Shared Items List Models
class SharedFolderInfo(BaseModel):
    id: UUID4
    name: str
    created_at: datetime
    parent_folder_id: Optional[UUID4] = None

    class Config:
        from_attributes = True


class SharedFileInfo(BaseModel):
    id: UUID4
    filename: str
    file_type: Optional[str]
    file_size: Optional[int]
    uploaded_at: datetime

    class Config:
        from_attributes = True


class SharedItemsResponse(BaseModel):
    folders: List[SharedFolderInfo]
    files: List[SharedFileInfo]
    total_folders: int
    total_files: int


# Error Response Models
class ShareErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None


# Example Usage Response
class ExampleShareResponse(BaseModel):
    """Example responses for API documentation"""
    success_share: ShareResponse = ShareResponse(message="Item shared successfully")
    success_revoke: ShareResponse = ShareResponse(message="Sharing revoked successfully")
    error_not_found: ShareErrorResponse = ShareErrorResponse(
        detail="Item not found",
        error_code="ITEM_NOT_FOUND"
    )
    error_no_permission: ShareErrorResponse = ShareErrorResponse(
        detail="Insufficient permissions to share this item",
        error_code="INSUFFICIENT_PERMISSIONS"
    )