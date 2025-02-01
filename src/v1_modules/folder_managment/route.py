from fastapi import HTTPException, APIRouter, Depends
from sqlalchemy import select, and_
from sqlalchemy.exc import SQLAlchemyError
import os

from sqlalchemy.ext.asyncio import AsyncSession

from src.config.logger import logger
from src.db.dbConnections import get_async_db
from src.v1_modules.auth.crud import get_current_user_v2
from src.v1_modules.auth.model import User
from src.v1_modules.auth.utilities import get_admin_user
from src.v1_modules.folder_managment.folder_manager import get_storage_manager
from src.v1_modules.folder_managment.model import Folder, UserFolderPermission
from src.v1_modules.folder_managment.schema import FolderCreate, FolderResponse

folder_router = APIRouter()

@folder_router.post("/folders", response_model=FolderResponse)
async def create_folder(
        folder: FolderCreate,
        db: AsyncSession = Depends(get_async_db),
        current_user: User = Depends(get_current_user_v2)
):
    """Create a new folder with the given name"""
    try:
        # Check for duplicate folder name in the same parent directory
        base_name = folder.name
        suffix = 1
        new_folder_name = base_name

        while True:
            query = select(Folder).where(
                and_(
                    Folder.name == new_folder_name,
                    Folder.parent_folder_id == folder.parent_folder_id,
                    Folder.owner_id == current_user.id
                )
            )
            result = await db.execute(query)
            existing_folder = result.scalar_one_or_none()

            if not existing_folder:
                break

            new_folder_name = f"{base_name} ({suffix})"
            suffix += 1

        # Create folder in database
        new_folder = Folder(
            name=new_folder_name,
            parent_folder_id=folder.parent_folder_id,
            owner_id=current_user.id
        )
        db.add(new_folder)
        await db.commit()
        await db.refresh(new_folder)

        # Create physical storage folder
        storage_manager = get_storage_manager()
        try:
            folder_path = await storage_manager.create_folder(new_folder.name)
            logger.info(f"Created storage folder at: {folder_path}")
        except Exception as e:
            logger.error(f"Storage creation failed: {str(e)}")
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Failed to create storage folder"
            )

        # Add admin permissions
        admin_user = await get_admin_user(db)
        if not admin_user:
            logger.error("Admin user not found")
            await storage_manager.delete_folder(new_folder.id)
            await db.rollback()
            raise ValueError("Admin user not found")

        admin_permission = UserFolderPermission(
            user_id=admin_user.id,
            folder_id=new_folder.id,
            can_view=True,
            can_edit=True,
            can_delete=True,
            can_create=True,
            can_share=True
        )
        db.add(admin_permission)
        await db.commit()

        # Add owner permissions if not admin
        if current_user.id != admin_user.id:
            owner_permission = UserFolderPermission(
                user_id=current_user.id,
                folder_id=new_folder.id,
                can_view=True,
                can_edit=True,
                can_delete=True,
                can_create=True,
                can_share=True
            )
            db.add(owner_permission)
            await db.commit()

        return {
            "id": new_folder.id,
            "name": new_folder.name,
            "parent_folder_id": new_folder.parent_folder_id,
            "owner_id": new_folder.owner_id,
            "created_at": new_folder.created_at,
            "files": [],
            "subfolders": []
        }

    except SQLAlchemyError as e:
        logger.error(f"Database error: {str(e)}")
        # Clean up storage if needed
        if 'new_folder' in locals():
            try:
                storage_manager = get_storage_manager()
                await storage_manager.delete_folder(new_folder.id)
            except:
                pass
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Database error occurred: {str(e)}"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        # Clean up storage if needed
        if 'new_folder' in locals():
            try:
                storage_manager = get_storage_manager()
                await storage_manager.delete_folder(new_folder.id)
            except:
                pass
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred"
        )