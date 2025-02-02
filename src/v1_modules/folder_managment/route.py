from typing import List
from uuid import UUID

from fastapi import HTTPException, APIRouter, Depends, UploadFile, File


from sqlalchemy.ext.asyncio import AsyncSession

from src.db.dbConnections import get_async_db
from src.v1_modules.auth.crud import get_current_user_v2
from src.v1_modules.auth.model import User
from src.v1_modules.auth.utilities import get_admin_user, has_folder_permission
from src.v1_modules.folder_managment.schema import FolderCreate, FolderResponse
from src.v1_modules.folder_managment.services import FolderService, FileService

folder_router = APIRouter()

@folder_router.post("/folders", response_model=FolderResponse)
async def create_folder(
    folder: FolderCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_v2)
):
    """Create a new folder with the given name."""
    return await FolderService.create_folder(folder, db, current_user)

@folder_router.get("/files", response_model=List[FolderResponse])
async def list_accessible_files(
    current_user: User = Depends(get_current_user_v2),
    db: AsyncSession = Depends(get_async_db)
):
    """List all files and folders the user has access to."""
    return await FolderService.get_accessible_folders(db, current_user.id)


@folder_router.post("/{folder_id}/upload")
async def upload_file(
    folder_id: UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user_v2),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Upload a file to a specific folder.
    """
    # Verify folder access
    if not await has_folder_permission(db, current_user.id, folder_id, "can_create"):
        raise HTTPException(status_code=403, detail="Permission denied")

    # Upload the file
    return await FileService.upload_file(db, folder_id, file, current_user.id)