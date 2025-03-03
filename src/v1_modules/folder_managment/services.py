import os

from sqlalchemy import select, and_
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import selectinload
from starlette import status

from src.config.logger import logger
from src.v1_modules.auth.model import User
from src.v1_modules.auth.utilities import get_admin_user
from src.v1_modules.folder_managment.folder_manager import get_storage_manager, S3StorageManager
from src.v1_modules.folder_managment.model import Folder, UserFolderPermission, File, UserFilePermission, SharedItem
from src.v1_modules.folder_managment.schema import FolderResponse, FileResponse
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
            # Check if parent_folder_id is provided
            if folder.parent_folder_id:
                # Fetch the parent folder
                parent_folder_query = select(Folder).where(Folder.id == folder.parent_folder_id)
                parent_folder_result = await db.execute(parent_folder_query)
                parent_folder = parent_folder_result.scalar_one_or_none()

                if not parent_folder:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Parent folder not found"
                    )

                # Check if the current user owns the parent folder or has permission to create subfolders
                permission_query = select(UserFolderPermission).where(
                    and_(
                        UserFolderPermission.folder_id == parent_folder.id,
                        UserFolderPermission.user_id == current_user.id,
                        UserFolderPermission.can_create == True
                    )
                )
                permission_result = await db.execute(permission_query)
                permission = permission_result.scalar_one_or_none()

                if not permission and parent_folder.owner_id != current_user.id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Insufficient permissions to create a subfolder in this parent folder"
                    )

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
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Storage creation failed: {str(e)}"
                )

            admin_user = await get_admin_user(db)
            if not admin_user:
                logger.error("Admin user not found")
                await storage_manager.delete_folder(new_folder.name)
                await db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Admin user not found"
                )

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
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error occurred: {str(e)}"
            )

        except HTTPException as e:
            # Re-raise HTTPException to return the error response
            raise e

        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred"
            )
        finally:
            if new_folder and 'folder_response' not in locals():
                try:
                    await storage_manager.delete_folder(new_folder.name)
                except Exception as e:
                    logger.error(f"Failed to clean up storage folder: {str(e)}")

    @staticmethod
    async def get_accessible_folders_and_files(db, user_id, is_admin=False):
        """
        Retrieve all folders and files that a user has permission to view.
        For admin users, groups items by username.
        """
        storage_manager = get_storage_manager()
        if not is_admin:
            # Original logic for regular users
            folder_permissions_query = select(UserFolderPermission).where(UserFolderPermission.user_id == user_id)
            folder_permissions_result = await db.execute(folder_permissions_query)
            folder_permissions = folder_permissions_result.scalars().all()

            file_permissions_query = select(UserFilePermission).where(UserFilePermission.user_id == user_id)
            file_permissions_result = await db.execute(file_permissions_query)
            file_permissions = file_permissions_result.scalars().all()

            accessible_folders = []
            accessible_files = []

            # Track folders that are subfolders to avoid duplication
            subfolder_ids = set()

            for permission in folder_permissions:
                if permission.can_view:
                    folder = await get_folder_with_contents(db, permission.folder_id)
                    if folder:
                        # If the folder is a subfolder, skip adding it to the main list
                        if folder["parent_folder_id"] is not None:
                            subfolder_ids.add(folder["id"])
                        else:
                            accessible_folders.append(folder)

            for permission in file_permissions:
                if permission.can_view:
                    file_query = select(File).where(File.id == permission.file_id)
                    file_result = await db.execute(file_query)
                    file = file_result.scalar_one_or_none()
                    if file:
                        # Generate pre-signed URL for the file
                        storage_manager: S3StorageManager = get_storage_manager()
                        file_url = await storage_manager.generate_presigned_url(file.file_path)
                        file_response = FileResponse.from_orm(file)
                        file_response.file_url = file_url
                        accessible_files.append(file_response)

            folder_responses = [FolderResponse.from_orm(folder) for folder in accessible_folders]
            file_responses = [FileResponse.from_orm(file) for file in accessible_files]

            return folder_responses, file_responses
        else:
            # Admin logic - group by users
            # Get all users
            users_query = select(User)
            users_result = await db.execute(users_query)
            users = users_result.scalars().all()

            user_resources = {}

            for user in users:
                # Get folders for this user
                folder_permissions_query = select(UserFolderPermission).where(
                    UserFolderPermission.user_id == user.id
                )
                folder_permissions_result = await db.execute(folder_permissions_query)
                folder_permissions = folder_permissions_result.scalars().all()

                # Get files for this user
                file_permissions_query = select(UserFilePermission).where(
                    UserFilePermission.user_id == user.id
                )
                file_permissions_result = await db.execute(file_permissions_query)
                file_permissions = file_permissions_result.scalars().all()

                user_folders = []
                user_files = []

                # Track folders that are subfolders to avoid duplication
                subfolder_ids = set()

                for permission in folder_permissions:
                    if permission.can_view:
                        folder = await get_folder_with_contents(db, permission.folder_id)
                        if folder:
                            # If the folder is a subfolder, skip adding it to the main list
                            if folder["parent_folder_id"] is not None:
                                subfolder_ids.add(folder["id"])
                            else:
                                user_folders.append(folder)

                for permission in file_permissions:
                    if permission.can_view:
                        file_query = select(File).where(File.id == permission.file_id)
                        file_result = await db.execute(file_query)
                        file = file_result.scalar_one_or_none()
                        if file:
                            # Generate pre-signed URL for the file
                            file_url = await storage_manager.generate_presigned_url(file.file_path)
                            file_response = FileResponse.from_orm(file)
                            file_response.file_url = file_url
                            user_files.append(file_response)

                if user_folders or user_files:
                    user_resources[user.username] = {
                        "folders": [FolderResponse.from_orm(folder) for folder in user_folders],
                        "files": [FileResponse.from_orm(file) for file in user_files]
                    }

            return user_resources

    @staticmethod
    async def download_folder_as_zip(
            db,
            folder_id,
            current_user
    ):
        """
        Download all files in a folder as a ZIP archive.
        Returns a BytesIO buffer containing the ZIP file.
        """
        import io
        import zipfile

        try:
            # Fetch the folder from the database
            folder_query = select(Folder).where(Folder.id == folder_id)
            folder_result = await db.execute(folder_query)
            folder = folder_result.scalar_one_or_none()

            if not folder:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Folder not found"
                )

            # Check if the user has permission to view the folder
            permission_query = select(UserFolderPermission).where(
                and_(
                    UserFolderPermission.folder_id == folder_id,
                    UserFolderPermission.user_id == current_user.id,
                    UserFolderPermission.can_view == True
                )
            )
            permission_result = await db.execute(permission_query)
            permission = permission_result.scalar_one_or_none()

            if not permission and folder.owner_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Unauthorized to access this folder"
                )

            # Get all files in the folder
            files_query = select(File).where(File.folder_id == folder_id)
            files_result = await db.execute(files_query)
            files = files_result.scalars().all()

            # Create a ZIP file in memory
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                storage_manager = get_storage_manager()
                for file in files:
                    try:
                        storage_manager: S3StorageManager = get_storage_manager()

                        # Download the file from S3 using the storage manager
                        file_data = await storage_manager.download_file(file.file_path)
                        zip_file.writestr(file.filename, file_data)
                    except Exception as e:
                        logger.error(f"Error adding file {file.filename} to ZIP: {str(e)}")
                        # Continue with other files if one fails

            # Reset buffer position for reading
            zip_buffer.seek(0)
            return {
                "zip_buffer": zip_buffer,
                "folder_name": folder.name
            }

        except HTTPException as e:
            # Re-raise HTTP exceptions
            raise e
        except Exception as e:
            logger.error(f"Error creating ZIP archive: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create ZIP archive: {str(e)}"
            )
class FileService:
    @staticmethod
    async def upload_file(
            db,
            folder_id,
            file,
            user_id
    ) -> FileResponse:
        """
        Upload a file to a specific folder or a default folder if no folder_id is provided.
        Returns the uploaded file's details as a FileResponse object.
        """
        try:
            # If folder_id is None, upload to a default folder (e.g., user's root folder)
            if folder_id is None:
                default_folder_name = f"user_{user_id}_root"
                folder_query = select(Folder).where(
                    and_(
                        Folder.name == default_folder_name,
                        Folder.owner_id == user_id
                    )
                )
                folder_result = await db.execute(folder_query)
                folder = folder_result.scalar_one_or_none()

                # If the default folder doesn't exist, create it
                if not folder:
                    folder = Folder(
                        name=default_folder_name,
                        owner_id=user_id,
                        parent_folder_id=None
                    )
                    db.add(folder)
                    await db.commit()
                    await db.refresh(folder)

                folder_id = folder.id

            # Make sure folder_id is not None at this point
            if folder_id is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No valid folder_id could be determined"
                )

            # Fetch the folder from the database using folder_id
            folder_query = select(Folder).where(Folder.id == folder_id)
            folder_result = await db.execute(folder_query)
            folder = folder_result.scalar_one_or_none()

            if not folder:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Folder not found"
                )

            # Check if the user has permission to upload files to the folder
            permission_query = select(UserFolderPermission).where(
                and_(
                    UserFolderPermission.folder_id == folder_id,
                    UserFolderPermission.user_id == user_id,
                    UserFolderPermission.can_create == True
                )
            )
            permission_result = await db.execute(permission_query)
            permission = permission_result.scalar_one_or_none()

            if not permission and folder.owner_id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions to upload files to this folder"
                )

            # Use S3StorageManager to store the file in the S3 bucket
            storage_manager = get_storage_manager()

            # Ensure we're using the correct folder name
            folder_name = folder.name
            logger.info(f"Uploading file to folder: {folder_name} (ID: {folder_id})")

            # Reset file position to ensure we can read the entire file
            await file.seek(0)
            file_key = await storage_manager.store_file(folder_name, file)

            # Create file record
            new_file = File(
                filename=file.filename,
                file_path=file_key,  # Use the S3 file key as the file path
                folder_id=folder_id,
                uploaded_by_id=user_id,
                file_type=file.content_type,
                file_size=file.size  # Use file.size directly (FastAPI provides this)
            )
            db.add(new_file)
            await db.commit()
            await db.refresh(new_file)

            # Create file permissions for the owner
            owner_permission = UserFilePermission(
                user_id=user_id,
                file_id=new_file.id,
                can_view=True,
                can_edit=True,
                can_delete=True,
                can_share=True
            )
            db.add(owner_permission)

            # Create file permissions for the admin
            admin_user = await get_admin_user(db)
            if admin_user:
                admin_permission = UserFilePermission(
                    user_id=admin_user.id,
                    file_id=new_file.id,
                    can_view=True,
                    can_edit=True,
                    can_delete=True,
                    can_share=True
                )
                db.add(admin_permission)

            await db.commit()

            logger.info(f"File '{file.filename}' uploaded successfully to folder '{folder_name}' by user '{user_id}'")

            # Return the uploaded file's details as a FileResponse object
            return FileResponse(
                id=new_file.id,
                filename=new_file.filename,
                file_path=new_file.file_path,
                folder_id=new_file.folder_id,
                uploaded_by_id=new_file.uploaded_by_id,
                uploaded_at=new_file.uploaded_at,
                file_type=new_file.file_type,
                file_size=new_file.file_size
            )

        except HTTPException as e:
            raise e

        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload file"
            )

    @staticmethod
    async def download_file(
        db,
        file_id,
        current_user
    ) :
        """Generate a pre-signed URL to download a specific file."""
        # Check if the file exists
        file_query = select(File).where(File.id == file_id)
        file_result = await db.execute(file_query)
        file = file_result.scalar_one_or_none()

        if not file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )

        # Check if the user has permission to view the file
        permission_query = select(UserFilePermission).where(
            and_(
                UserFilePermission.file_id == file_id,
                UserFilePermission.user_id == current_user.id,
                UserFilePermission.can_view == True
            )
        )
        permission_result = await db.execute(permission_query)
        permission = permission_result.scalar_one_or_none()

        if not permission and file.uploaded_by_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unauthorized to access this file"
            )

        # Generate pre-signed URL
        storage_manager: S3StorageManager = get_storage_manager()
        file_url = await storage_manager.generate_presigned_url(file.file_path)

        return file_url



class SharingService:
    @staticmethod
    async def share_folder(
            db,
            folder_id,
            shared_by_id,
            shared_with_user_emails,
            actions
    ):
        """
        Share a folder with multiple users and define their permissions.
        """
        try:
            # Check if folder exists and get its details
            folder_query = (
                select(Folder)
                .where(Folder.id == folder_id)
                .options(
                    selectinload(Folder.subfolders),
                    selectinload(Folder.files)
                )
            )
            result = await db.execute(folder_query)
            folder = result.scalar_one_or_none()

            if not folder:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Folder not found"
                )

            # Check if sharer has permission to share
            permission_query = select(UserFolderPermission).where(
                and_(
                    UserFolderPermission.folder_id == folder_id,
                    UserFolderPermission.user_id == shared_by_id,
                    UserFolderPermission.can_share == True
                )
            )
            permission_result = await db.execute(permission_query)
            permission = permission_result.scalar_one_or_none()

            if not permission and folder.owner_id != shared_by_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to share this folder"
                )

            # Share with each user in the list
            for shared_with_email in shared_with_user_emails:
                # Fetch the user by email
                user_query = select(User).where(User.email == shared_with_email)
                user_result = await db.execute(user_query)
                shared_with_user = user_result.scalar_one_or_none()

                if not shared_with_user:
                    logger.warning(f"User with email {shared_with_email} not found")
                    continue

                # Check if the folder is already shared with the user
                sharing_record_query = select(SharedItem).where(
                    and_(
                        SharedItem.item_type == "folder",
                        SharedItem.item_id == folder_id,
                        SharedItem.shared_with == shared_with_user.id
                    )
                )
                sharing_record_result = await db.execute(sharing_record_query)
                sharing_record = sharing_record_result.scalar_one_or_none()

                if sharing_record:
                    continue

                # Create sharing record
                shared_item = SharedItem(
                    item_type="folder",
                    item_id=folder_id,
                    shared_by=shared_by_id,
                    shared_with=shared_with_user.id,
                    share_type="full" if folder.parent_folder_id is None else "specific"
                )
                db.add(shared_item)

                # Check if the user already has folder permissions
                folder_permission_query = select(UserFolderPermission).where(
                    and_(
                        UserFolderPermission.folder_id == folder_id,
                        UserFolderPermission.user_id == shared_with_user.id
                    )
                )
                folder_permission_result = await db.execute(folder_permission_query)
                folder_permission = folder_permission_result.scalar_one_or_none()

                if not folder_permission:
                    # Create folder permission for shared user
                    folder_permission = UserFolderPermission(
                        user_id=shared_with_user.id,
                        folder_id=folder_id,
                        can_view=True,
                        can_edit="can_edit" in actions,
                        can_delete="can_delete" in actions,
                        can_create="can_create" in actions,
                        can_share="can_share" in actions
                    )
                    db.add(folder_permission)

                # If it's a parent folder (no parent_folder_id), share all subfolders recursively
                if folder.parent_folder_id is None:
                    await SharingService._share_subfolders_recursively(
                        db,
                        folder,
                        shared_with_user.id,
                        actions
                    )

                # Share all files within the folder
                for file in folder.files:
                    # Check if the user already has file permissions
                    file_permission_query = select(UserFilePermission).where(
                        and_(
                            UserFilePermission.file_id == file.id,
                            UserFilePermission.user_id == shared_with_user.id
                        )
                    )
                    file_permission_result = await db.execute(file_permission_query)
                    file_permission = file_permission_result.scalar_one_or_none()

                    if not file_permission:
                        # Create file permission for shared user
                        file_permission = UserFilePermission(
                            user_id=shared_with_user.id,
                            file_id=file.id,
                            can_view=True,
                            can_edit="can_edit" in actions,
                            can_delete="can_delete" in actions,
                            can_share="can_share" in actions
                        )
                        db.add(file_permission)

            await db.commit()
            return {"message": "Folder shared successfully with all users"}

        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Error sharing folder: {str(e)}")
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to share folder: {str(e)}"
            )

    @staticmethod
    async def _share_subfolders_recursively(
            db,
            folder: Folder,
            shared_with_id,
            actions
    ):
        """
        Recursively share all subfolders and their contents with the specified permissions.
        """
        for subfolder in folder.subfolders:
            # Create permission for subfolder
            subfolder_permission = UserFolderPermission(
                user_id=shared_with_id,
                folder_id=subfolder.id,
                can_view=True,
                can_edit="can_edit" in actions,
                can_delete="can_delete" in actions,
                can_create="can_create" in actions,
                can_share="can_share" in actions
            )
            db.add(subfolder_permission)

            # Share files in subfolder
            for file in subfolder.files:
                file_permission = UserFilePermission(
                    user_id=shared_with_id,
                    file_id=file.id,
                    can_view=True,
                    can_edit="can_edit" in actions,
                    can_delete="can_delete" in actions,
                    can_share="can_share" in actions
                )
                db.add(file_permission)

            # Recursively process nested subfolders
            await SharingService._share_subfolders_recursively(
                db,
                subfolder,
                shared_with_id,
                actions
            )

    @staticmethod
    async def share_file(
            db,
            file_id,
            shared_by_id,
            shared_with_user_emails,
            actions
    ):
        """
        Share a specific file with multiple users and define their permissions.
        """
        try:
            # Check if file exists
            file_query = select(File).where(File.id == file_id)
            result = await db.execute(file_query)
            file = result.scalar_one_or_none()

            if not file:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="File not found"
                )

            # Check if sharer has permission to share
            permission_query = select(UserFilePermission).where(
                and_(
                    UserFilePermission.file_id == file_id,
                    UserFilePermission.user_id == shared_by_id,
                    UserFilePermission.can_share == True
                )
            )
            permission_result = await db.execute(permission_query)
            permission = permission_result.scalar_one_or_none()

            if not permission and file.uploaded_by_id != shared_by_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to share this file"
                )

            # Share with each user in the list
            for shared_with_email in shared_with_user_emails:
                # Fetch the user by email
                user_query = select(User).where(User.email == shared_with_email)
                user_result = await db.execute(user_query)
                shared_with_user = user_result.scalar_one_or_none()

                if not shared_with_user:
                    logger.warning(f"User with email {shared_with_email} not found")
                    continue

                sharing_record_query = select(SharedItem).where(
                    and_(
                        SharedItem.item_type == "file",
                        SharedItem.item_id == file_id,
                        SharedItem.shared_with == shared_with_user.id
                    )
                )
                sharing_record_result = await db.execute(sharing_record_query)
                sharing_record = sharing_record_result.scalar_one_or_none()

                if sharing_record:
                    continue

                # Create sharing record
                shared_item = SharedItem(
                    item_type="file",
                    item_id=file_id,
                    shared_by=shared_by_id,
                    shared_with=shared_with_user.id,
                    share_type="specific"
                )
                db.add(shared_item)

                # Create file permission for shared user
                file_permission = UserFilePermission(
                    user_id=shared_with_user.id,
                    file_id=file_id,
                    can_view=True,
                    can_edit="can_edit" in actions,
                    can_delete="can_delete" in actions,
                    can_share="can_share" in actions
                )
                db.add(file_permission)

            await db.commit()
            return {"message": "File shared successfully with all users"}

        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Error sharing file: {str(e)}")
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to share file: {str(e)}"
            )