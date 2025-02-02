import os

from sqlalchemy import select, and_
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException, UploadFile

from src.config.logger import logger
from src.utills.response import Response
from src.v1_modules.auth.utilities import get_admin_user
from src.v1_modules.folder_managment.folder_manager import get_storage_manager
from src.v1_modules.folder_managment.model import Folder, UserFolderPermission, File
from src.v1_modules.folder_managment.schema import  FolderResponse
from src.v1_modules.folder_managment.utilities import get_folder_with_contents


class FolderService:
    @staticmethod
    async def create_folder(
        folder,
        db,
        current_user
    ):
        """Create a new folder with the given name."""
        new_folder = None
        storage_manager = get_storage_manager()

        try:
            # Check for duplicate folder name logic remains the same
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

            try:
                folder_path = await storage_manager.create_folder(new_folder.name)
                logger.info(f"Created storage folder at: {folder_path}")
            except Exception as e:
                logger.error(f"Storage creation failed: {str(e)}")
                await db.rollback()
                raise

            admin_user = await get_admin_user(db)
            if not admin_user:
                logger.error("Admin user not found")
                await storage_manager.delete_folder(new_folder.name)
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

            folder_response = FolderResponse(
                id=new_folder.id,
                name=new_folder.name,
                parent_folder_id=new_folder.parent_folder_id,
                owner_id=new_folder.owner_id,
                created_at=new_folder.created_at,
                files=[],
                subfolders=[]
            )

            return folder_response

        except SQLAlchemyError as e:
            logger.error(f"Database error: {str(e)}")
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Database error occurred: {str(e)}"
            )

        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="An unexpected error occurred"
            )
        finally:
            if new_folder and 'folder_response' not in locals():
                try:
                    await storage_manager.delete_folder(new_folder.name)
                except Exception as e:
                    logger.error(f"Failed to clean up storage folder: {str(e)}")

    @staticmethod
    async def get_accessible_folders(db, user_id):
        """
        Retrieve all folders that a user has permission to view.
        """
        query = select(UserFolderPermission).where(UserFolderPermission.user_id == user_id)
        result = await db.execute(query)
        permissions = result.scalars().all()

        accessible_folders = []
        for permission in permissions:
            if permission.can_view:
                folder = await get_folder_with_contents(db, permission.folder_id)
                if folder:
                    accessible_folders.append(folder)

        return [FolderResponse.from_orm(folder) for folder in accessible_folders]

class FileService:
    @staticmethod
    async def upload_file(
        db,
        folder_id,
        file: UploadFile,
        user_id
    ) -> dict:
        """
        Upload a file to a specific folder.

        Args:
            db: AsyncSession - The database session.
            folder_id: UUID - The ID of the folder where the file will be uploaded.
            file: UploadFile - The file to upload.
            user_id: UUID - The ID of the user uploading the file.

        Returns:
            dict - A success message.
        """
        try:
            # Save file to storage
            file_path = f"storage/{folder_id}/{file.filename}"
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)

            # Create file record
            new_file = File(
                filename=file.filename,
                file_path=file_path,
                folder_id=folder_id,
                uploaded_by_id=user_id,
                file_type=file.content_type,
                file_size=len(content)
            )
            db.add(new_file)
            await db.commit()

            logger.info(f"File '{file.filename}' uploaded successfully to folder '{folder_id}' by user '{user_id}'")
            return {"message": "File uploaded successfully"}
        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to upload file")