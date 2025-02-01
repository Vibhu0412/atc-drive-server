from sqlalchemy.future import select

from src.v1_modules.auth.model import User, Role


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