from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from uuid import UUID
from typing import Optional, List

from src.v1_modules.folder_managment.model import Folder, File
from src.v1_modules.folder_managment.schema import FolderResponse, FileResponse


async def get_folder_with_contents(db: AsyncSession, folder_id: UUID) -> Optional[Folder]:
    """
    Recursively fetch a folder and all its contents (files and subfolders).
    """
    query = (
        select(Folder)
        .where(Folder.id == folder_id)
        .options(
            selectinload(Folder.files),
            selectinload(Folder.permissions),
            selectinload(Folder.subfolders), 
        )
    )

    result = await db.execute(query)
    folder = result.scalar_one_or_none()

    if not folder:
        return None

    # Recursively fetch subfolder contents
    subfolders_query = select(Folder).where(Folder.parent_folder_id == folder_id)
    subfolders_result = await db.execute(subfolders_query)
    subfolders = subfolders_result.scalars().all()

    # Recursively get contents of each subfolder
    folder.subfolders = [
        await get_folder_with_contents(db, subfolder.id) for subfolder in subfolders
    ]

    return folder

async def get_root_folders(db: AsyncSession, user_id: UUID) -> List[Folder]:
    """
    Get all root folders (folders with no parent) that the user has access to.

    Args:
        db: AsyncSession - The database session
        user_id: UUID - The ID of the user

    Returns:
        List of root folders
    """
    query = (
        select(Folder)
        .where(
            Folder.parent_folder_id.is_(None),
            Folder.owner_id == user_id
        )
        .options(
            selectinload(Folder.files),
            selectinload(Folder.subfolders)
        )
    )

    result = await db.execute(query)
    return result.scalars().all()