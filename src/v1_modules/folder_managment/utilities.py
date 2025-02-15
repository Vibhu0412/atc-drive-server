from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from uuid import UUID
from typing import Optional, List

from src.v1_modules.folder_managment.model import Folder, File


async def get_folder_with_contents(db: AsyncSession, folder_id: UUID) -> Optional[dict]:
    """
    Recursively fetch a folder and all its contents (files and subfolders).
    """
    query = (
        select(Folder)
        .where(Folder.id == folder_id)
        .options(
            selectinload(Folder.files),
            selectinload(Folder.owner),
            selectinload(Folder.subfolders),
        )
    )
    result = await db.execute(query)
    folder = result.scalar_one_or_none()
    if not folder:
        return None

    # Recursively fetch subfolder contents
    subfolders = []
    for subfolder in folder.subfolders:
        subfolder_data = await get_folder_with_contents(db, subfolder.id)
        if subfolder_data:
            subfolders.append(subfolder_data)

    # Organize folder data with additional required fields
    folder_data = {
        "id": folder.id,
        "name": folder.name,
        "files": [{"id": file.id, "filename": file.filename} for file in folder.files],
        "subfolders": subfolders,
        "owner_id": folder.owner.id,  # Add owner_id
        "created_at": folder.created_at  # Add created_at
    }
    return folder_data

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