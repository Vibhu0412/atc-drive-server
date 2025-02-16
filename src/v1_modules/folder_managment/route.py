from typing import Optional
from uuid import UUID
from fastapi import HTTPException, APIRouter, Depends, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.dbConnections import get_async_db
from src.utills.response_v2 import ResponseBuilder, CommonResponses, ResponseStatus
from src.v1_modules.auth.crud import get_current_user_v2
from src.v1_modules.auth.model import User
from src.v1_modules.auth.utilities import get_admin_user, has_folder_permission, has_file_permission
from src.v1_modules.folder_managment.schema import FolderCreate, FolderResponse, ShareItemRequest
from src.v1_modules.folder_managment.services import FolderService, FileService, SharingService

folder_router = APIRouter()

@folder_router.post("/folders")
async def create_folder(
    folder: FolderCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_v2)
):
    """Create a new folder with the given name."""
    try:
        new_folder = await FolderService.create_folder(folder, db, current_user)
        response = ResponseBuilder.from_common_response(
            CommonResponses.success(
                data=new_folder,
                message="Folder created successfully"
            )
        )
        return response.send_success_response()
    except Exception as e:
        response = ResponseBuilder(
            status_code=ResponseStatus.INTERNAL_ERROR,
            message=str(e),
            data=None
        )
        return response.send_error_response()

@folder_router.get("/files")
async def list_accessible_files(
    current_user: User = Depends(get_current_user_v2),
    db: AsyncSession = Depends(get_async_db)
):
    """List all files and folders the user has access to."""
    try:
        folders = await FolderService.get_accessible_folders_and_files(db, current_user.id)
        response = ResponseBuilder.from_common_response(
            CommonResponses.success(
                data=folders,
                message="Folders retrieved successfully"
            )
        )
        return response.send_success_response()
    except Exception as e:
        response = ResponseBuilder(
            status_code=ResponseStatus.INTERNAL_ERROR,
            message=str(e),
            data=None
        )
        return response.send_error_response()

@folder_router.post("/file/upload")
async def upload_file(
    folder_id: Optional[UUID] = None,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user_v2),
    db: AsyncSession = Depends(get_async_db)
):
    """Upload a file to a specific folder or a default folder if no folder_id is provided."""
    try:
        # If folder_id is provided, verify folder access
        if folder_id is not None:
            if not await has_folder_permission(db, current_user.id, folder_id, "can_create"):
                response = ResponseBuilder.from_common_response(
                    CommonResponses.unauthorized()
                )
                return response.send_error_response()

        # Upload the file
        uploaded_file = await FileService.upload_file(db, folder_id, file, current_user.id)
        response = ResponseBuilder.from_common_response(
            CommonResponses.success(
                data=uploaded_file,
                message="File uploaded successfully"
            )
        )
        return response.send_success_response(
            file_name=file.filename,
            file_size=file.size
        )
    except Exception as e:
        response = ResponseBuilder(
            status_code=ResponseStatus.INTERNAL_ERROR,
            message=str(e),
            data=None
        )
        return response.send_error_response()


@folder_router.post("/folder/share")
async def share_folder(
    share_request: ShareItemRequest,
    current_user: User = Depends(get_current_user_v2),
    db: AsyncSession = Depends(get_async_db)
):
    """Share a folder with another user."""
    try:
        # Validate item type
        if share_request.item_type != "folder":
            return ResponseBuilder.from_common_response(
                CommonResponses.BAD_REQUEST("Invalid item type. Expected 'folder'.")
            ).send_error_response()

        # Convert emails to user IDs
        shared_with_user_ids = []
        for email in share_request.shared_with_user_emails:
            user = await db.execute(select(User).where(User.email == email))
            user = user.scalar_one_or_none()
            if not user:
                return ResponseBuilder.from_common_response(
                    CommonResponses.BAD_REQUEST(f"User with email {email} not found")
                ).send_error_response()
            shared_with_user_ids.append(user.id)

        # Validate permissions before sharing
        if not await has_folder_permission(db, current_user.id, share_request.item_id, "can_share"):
            return ResponseBuilder.from_common_response(
                CommonResponses.unauthorized()
            ).send_error_response()

        result = await SharingService.share_folder(
            db=db,
            folder_id=share_request.item_id,
            shared_by_id=current_user.id,
            shared_with_user_ids=shared_with_user_ids
        )
        return ResponseBuilder.from_common_response(
            CommonResponses.success(data=result, message="Folder shared successfully")
        ).send_success_response()

    except Exception as e:
        return ResponseBuilder(
            status_code=ResponseStatus.INTERNAL_ERROR,
            message=str(e),
            data=None
        ).send_error_response()


@folder_router.post("/file/share")
async def share_file(
    share_request: ShareItemRequest,
    current_user: User = Depends(get_current_user_v2),
    db: AsyncSession = Depends(get_async_db)
):
    """Share a file with another user."""
    try:
        # Validate item type
        if share_request.item_type != "file":
            return ResponseBuilder.from_common_response(
                CommonResponses.BAD_REQUEST("Invalid item type. Expected 'file'.")
            ).send_error_response()

        # Convert emails to user IDs
        shared_with_user_ids = []
        for email in share_request.shared_with_user_emails:
            user = await db.execute(select(User).where(User.email == email))
            user = user.scalar_one_or_none()
            if not user:
                return ResponseBuilder.from_common_response(
                    CommonResponses.BAD_REQUEST(f"User with email {email} not found")
                ).send_error_response()
            shared_with_user_ids.append(user.id)

        # Validate permissions before sharing
        if not await has_file_permission(db, current_user.id, share_request.item_id, "can_share"):
            return ResponseBuilder.from_common_response(
                CommonResponses.unauthorized()
            ).send_error_response()

        result = await SharingService.share_file(
            db=db,
            file_id=share_request.item_id,
            shared_by_id=current_user.id,
            shared_with_user_ids=shared_with_user_ids
        )
        return ResponseBuilder.from_common_response(
            CommonResponses.success(data=result, message="File shared successfully")
        ).send_success_response()

    except Exception as e:
        return ResponseBuilder(
            status_code=ResponseStatus.INTERNAL_ERROR,
            message=str(e),
            data=None
        ).send_error_response()