from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, validator
from uuid import UUID
from typing import Optional


class RoleBase(BaseModel):
    id: UUID
    name: str
    can_view: bool
    can_edit: bool
    can_delete: bool
    can_create: bool
    can_share: bool

    class Config:
        orm_mode = True

class FolderBase(BaseModel):
    id: int
    name: str

    class Config:
        orm_mode = True

class FileBase(BaseModel):
    id: int
    name: str
    created_at: str

    class Config:
        orm_mode = True

class UserFolderPermissionBase(BaseModel):
    id: int
    permission: str

    class Config:
        orm_mode = True


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=4, max_length=128)

    @validator('email')
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError('Invalid email format')
        return v

class RolePermissionsResponse(BaseModel):
    can_view: bool = False
    can_edit: bool = False
    can_delete: bool = False
    can_create: bool = False
    can_share: bool = False

class UserDetailResponse(BaseModel):
    id: UUID
    username: str
    email: str
    role_name: str
    last_login: Optional[datetime] = None
    role_permissions: RolePermissionsResponse
    meta: dict  # Add other necessary metadata if required

    class Config:
        orm_mode = True

class RoleResponse(BaseModel):
    id: UUID
    name: str
    can_view: bool
    can_edit: bool
    can_delete: bool
    can_create: bool
    can_share: bool

class UserResponse(BaseModel):
    id: UUID
    username: str
    email: str
    role_id: UUID
    created_at: datetime
    last_login: Optional[datetime]

class LoginResponse(BaseModel):
    user: UserResponse
    role: RoleResponse
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RegisterUserRequest(BaseModel):
    username: str
    password_hash: str
    email: EmailStr
    role_id: UUID

class UserRegistrationResponse(BaseModel):
    username: str
    email: str
    role_id: str

class SuccessResponse(BaseModel):
    detail: UserRegistrationResponse
    meta: dict


class UserResponseForGet(BaseModel):
    id: UUID
    username: str
    email: str
    role: RoleResponse
    created_at: datetime
    last_login: Optional[datetime] = None