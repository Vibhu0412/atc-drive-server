from sqlalchemy.future import select

from src.config.logger import logger
from src.v1_modules.auth.model import User, Role
from src.v1_modules.folder_managment.model import UserFolderPermission


async def get_admin_user(db) -> User:
    stmt = select(Role).where(Role.name == "admin")
    result = await db.execute(stmt)
    admin_role = result.scalars().first()

    if not admin_role:
        raise ValueError("Admin role not found")

    stmt = select(User).where(User.role_id == admin_role.id)
    result = await db.execute(stmt)
    admin_user = result.scalars().first()

    if not admin_user:
        raise ValueError("Admin user not found")

    return admin_user

async def has_folder_permission(
        db,
        user_id,
        folder_id,
        permission: str
    ) -> bool:
        """
        Check if a user has the specified permission for a folder.

        Args:
            db: AsyncSession - The database session.
            user_id: UUID - The ID of the user.
            folder_id: UUID - The ID of the folder.
            permission: str - The permission to check (e.g., "can_create").

        Returns:
            bool - True if the user has the permission, False otherwise.
        """
        try:
            query = select(UserFolderPermission).where(
                UserFolderPermission.user_id == user_id,
                UserFolderPermission.folder_id == folder_id
            )
            result = await db.execute(query)
            permission_record = result.scalar_one_or_none()

            if not permission_record:
                logger.warning(f"User '{user_id}' has no permissions for folder '{folder_id}'")
                return False

            # Check if the user has the required permission
            if not getattr(permission_record, permission, False):
                logger.warning(f"User '{user_id}' does not have '{permission}' permission for folder '{folder_id}'")
                return False

            logger.info(f"User '{user_id}' has '{permission}' permission for folder '{folder_id}'")
            return True
        except Exception as e:
            logger.error(f"Error checking folder permission: {str(e)}")
            return False