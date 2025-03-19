from fastapi import HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.future import select
from starlette import status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.dbConnections import get_async_db
from src.utills.toekn_utills import Token
from src.v1_modules.auth.model import Role, User


async def get_role_by_user_id(db, user_role_id):
    result = await db.execute(select(Role).filter(Role.id == user_role_id))
    role = result.scalars().first()
    if not role:
        raise HTTPException(status_code=404, detail="User role not found")
    return role

async def get_user(db, email):
    result = await db.execute(select(User).filter(User.email == email))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(
    db,
    token: str
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials ss",
        headers={"WWW-Authenticate": "Bearer"}
    )
    try:
        payload = Token().decode_token(token)

        user_name: str = payload.get("sub")
        print("hello",user_name)
        if user_name is None:
            raise credentials_exception
        result = await db.execute(select(User).filter(User.username == user_name))
        user = result.scalars().first()
        if user is None:
            raise credentials_exception
        return user
    except JWTError:
        raise credentials_exception


async def get_user_role_from_token(db, current_user: User):
    try:
        print("hello",current_user.username)
        role_result = await db.execute(
            select(Role).filter(Role.id == current_user.role_id)
        )
        user_role = role_result.scalars().first()
        print("hey tehere",user_role.id)
        admin_role_result = await db.execute(
            select(Role).filter(Role.name == 'admin')
        )
        admin_role = admin_role_result.scalars().first()
        print("hey ", admin_role.id)
        if not user_role or user_role.id != admin_role.id:
            print("user_role",user_role)
            return user_role

        print("user_role",user_role)
        return user_role

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Role verification failed: {str(e)}"
        )


async def get_current_user_v2(db: AsyncSession = Depends(get_async_db),
                              token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    expired_token_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token has expired",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = Token().decode_token(token)
        payload["token"] = token
        user_name: str = payload.get("sub")

        if user_name is None:
            raise credentials_exception
    except JWTError as e:
        # Check if the error is specifically about expiration
        if "expired" in str(e).lower():
            raise expired_token_exception
        raise credentials_exception

    result = await db.execute(select(User).filter(User.username == user_name))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    return user