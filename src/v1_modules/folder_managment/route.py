from typing import Optional, List
from uuid import UUID
from fastapi import HTTPException, APIRouter, Depends, UploadFile, File, Query, Body
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from src.db.dbConnections import get_async_db
from src.utills.response_v2 import ResponseBuilder, CommonResponses, ResponseStatus
from src.v1_modules.auth.crud import get_current_user_v2, get_user_role_from_token
from src.v1_modules.auth.model import User
from src.v1_modules.auth.utilities import has_folder_permission, has_file_permission
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
        # Check if user is admin
        user_role = await get_user_role_from_token(db, current_user)
        is_admin = user_role and user_role.name == 'admin'

        folders = await FolderService.get_accessible_folders_and_files(db, current_user.id, is_admin=is_admin)

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


from fastapi import Form
from uuid import UUID

@folder_router.post("/file/upload")
async def upload_file(
    folder_id: Optional[str] = Form(None),  # Accept as string first
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user_v2),
    db: AsyncSession = Depends(get_async_db)
):
    """Upload a file to a specific folder or a default folder if no folder_id is provided."""
    try:
        # Parse folder_id as UUID if provided
        parsed_folder_id = UUID(folder_id) if folder_id else None

        # If folder_id is provided, verify folder access
        if parsed_folder_id is not None:
            if not await has_folder_permission(db, current_user.id, parsed_folder_id, "can_create"):
                response = ResponseBuilder.from_common_response(
                    CommonResponses.unauthorized()
                )
                return response.send_error_response()

        # Upload the file
        uploaded_file = await FileService.upload_file(db, parsed_folder_id, file, current_user.id)
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
    except ValueError as e:
        # Handle invalid UUID format
        response = ResponseBuilder(
            status_code=ResponseStatus.BAD_REQUEST,
            message="Invalid folder_id format. Must be a valid UUID.",
            data=None
        )
        return response.send_error_response()
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
                CommonResponses.validation_error("Invalid item type. Expected 'folder'.")
            ).send_error_response()

        # Convert emails to user IDs
        shared_with_user_ids = []
        for email in share_request.shared_with_user_emails:
            user = await db.execute(select(User).where(User.email == email))
            user = user.scalar_one_or_none()
            if not user:
                return ResponseBuilder.from_common_response(
                    CommonResponses.validation_error(f"User with email {email} not found")
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
            shared_with_user_emails=share_request.shared_with_user_emails,
            actions=share_request.actions
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
                CommonResponses.validation_error("Invalid item type. Expected 'file'.")
            ).send_error_response()

        # Convert emails to user IDs
        shared_with_user_ids = []
        for email in share_request.shared_with_user_emails:
            user = await db.execute(select(User).where(User.email == email))
            user = user.scalar_one_or_none()
            if not user:
                return ResponseBuilder.from_common_response(
                    CommonResponses.validation_error(f"User with email {email} not found")
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
            shared_with_user_emails=share_request.shared_with_user_emails,
            actions=share_request.actions
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


@folder_router.get("/files/{file_id}/download")
async def download_file(
    file_id: UUID,
    current_user: User = Depends(get_current_user_v2),
    db: AsyncSession = Depends(get_async_db)
):
    """Get a pre-signed URL to download a specific file."""
    try:
        file_url = await FileService.download_file(db, file_id, current_user)
        return ResponseBuilder.from_common_response(
            CommonResponses.success(
                data={"file_url": file_url},
                message="Pre-signed URL generated successfully"
            )
        ).send_success_response()
    except HTTPException as e:
        return ResponseBuilder(
            status_code=e.status_code,
            message=e.detail,
            data=None
        ).send_error_response()
    except Exception as e:
        return ResponseBuilder(
            status_code=ResponseStatus.INTERNAL_ERROR,
            message=str(e),
            data=None
        ).send_error_response()


@folder_router.post("/files/download")
async def download_files(
        request_data: dict = Body(..., example={"file_ids": ["uuid1", "uuid2"]}),
        current_user: User = Depends(get_current_user_v2),
        db: AsyncSession = Depends(get_async_db)
):
    """Get pre-signed URLs for multiple files (max 50)."""
    try:
        file_ids = request_data.get("file_ids", [])

        # Validate input
        if not file_ids:
            return ResponseBuilder.from_common_response(
                CommonResponses.validation_error("At least one file_id is required")
            ).send_error_response()

        if len(file_ids) > 50:
            return ResponseBuilder.from_common_response(
                CommonResponses.validation_error("Max 50 files per request")
            ).send_error_response()

        # Process files
        file_urls = await FileService.download_files(db, file_ids, current_user)

        return ResponseBuilder.from_common_response(
            CommonResponses.success(
                data={"file_urls": file_urls},
                message="Pre-signed URLs generated successfully"
            )
        ).send_success_response()

    except HTTPException as e:
        return ResponseBuilder(
            status_code=e.status_code,
            message=e.detail,
            data=None
        ).send_error_response()
    except Exception as e:
        return ResponseBuilder(
            status_code=ResponseStatus.INTERNAL_ERROR,
            message=str(e),
            data=None
        ).send_error_response()

@folder_router.get("/folders/{folder_id}/download-zip")
async def download_folder_as_zip(
        folder_id: UUID,
        current_user: User = Depends(get_current_user_v2),
        db: AsyncSession = Depends(get_async_db)
):
    """Download all files in a folder as a ZIP archive."""
    try:
        # Validate permissions using the utility function
        if not await has_folder_permission(db, current_user.id, folder_id, "can_view"):
            return ResponseBuilder.from_common_response(
                CommonResponses.unauthorized()
            ).send_error_response()

        # Get the ZIP file from the service
        zip_data = await FolderService.download_folder_as_zip(db, folder_id, current_user)

        # Return as a streaming response to avoid loading the entire file into memory twice
        return StreamingResponse(
            zip_data["zip_buffer"],
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={zip_data['folder_name']}.zip"}
        )

    except HTTPException as e:
        return ResponseBuilder(
            status_code=e.status_code,
            message=e.detail,
            data=None
        ).send_error_response()
    except Exception as e:
        return ResponseBuilder(
            status_code=ResponseStatus.INTERNAL_ERROR,
            message=str(e),
            data=None
        ).send_error_response()

########################################## DELETE apis #############################################

@folder_router.delete("/folders/{folder_id}")
async def delete_folder(
    folder_id: UUID,
    current_user: User = Depends(get_current_user_v2),
    db: AsyncSession = Depends(get_async_db)
):
    """Delete a folder and its contents."""
    try:
        result = await FolderService.delete_folder(db, folder_id, current_user)
        return ResponseBuilder.from_common_response(
            CommonResponses.success(
                data=result,
                message="Folder deleted successfully"
            )
        ).send_success_response()
    except HTTPException as e:
        return ResponseBuilder(
            status_code=e.status_code,
            message=e.detail,
            data=None
        ).send_error_response()
    except Exception as e:
        return ResponseBuilder(
            status_code=ResponseStatus.INTERNAL_ERROR,
            message=str(e),
            data=None
        ).send_error_response()

@folder_router.delete("/files/{file_id}")
async def delete_file(
    file_id: UUID,
    current_user: User = Depends(get_current_user_v2),
    db: AsyncSession = Depends(get_async_db)
):
    """Delete a specific file."""
    try:
        result = await FileService.delete_file(db, file_id, current_user)
        return ResponseBuilder.from_common_response(
            CommonResponses.success(
                data=result,
                message="File deleted successfully"
            )
        ).send_success_response()
    except HTTPException as e:
        return ResponseBuilder(
            status_code=e.status_code,
            message=e.detail,
            data=None
        ).send_error_response()
    except Exception as e:
        return ResponseBuilder(
            status_code=ResponseStatus.INTERNAL_ERROR,
            message=str(e),
            data=None
        ).send_error_response()