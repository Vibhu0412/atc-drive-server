
from fastapi import Depends, HTTPException, status, APIRouter, Security
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from src.v1_modules.auth.crud import  get_current_user_v2
from src.v1_modules.auth.schema import UserDetailResponse, LoginRequest, RegisterUserRequest, RefreshTokenRequest, \
    ChangePasswordRequest
from src.v1_modules.auth.services import get_user_details_from_db, login_user, get_all_roles, \
    register_user, get_all_users, create_refresh_token, change_user_password
from src.db.dbConnections import get_async_db
from uuid import UUID

auth_router = APIRouter()

@auth_router.get("/{user_id}", response_model=UserDetailResponse)
async def get_user_details(user_id: UUID, db: AsyncSession = Depends(get_async_db)):

    try:
        user = await get_user_details_from_db(user_id, db)
        return user
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error: {str(e)}")


@auth_router.post("/login", response_model=dict)
async def login(
        login_data: LoginRequest,
        db: AsyncSession = Depends(get_async_db)
):
    login_response = await login_user(db, login_data)
    return login_response

@auth_router.get("/roles/fetch_roles")
async def fetch_roles(
        db: AsyncSession = Depends(get_async_db)
):
    role_response = await get_all_roles(db)
    return role_response

@auth_router.post("/register")
async def register(
    registration_data: RegisterUserRequest,
    db: AsyncSession = Depends(get_async_db),
    user: dict = Security(get_current_user_v2)
):
    return await register_user(db, registration_data, user)

@auth_router.get("/all/users")
async def list_all_users(
    db: AsyncSession = Depends(get_async_db),
    user: dict = Security(get_current_user_v2)  # Authentication required
):
    """
    Get a list of all users along with their role details.
    Only authenticated users can access this route.
    """
    return await get_all_users(db)

@auth_router.post("/refresh-token")
async def refresh_token(
    refresh_token_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_async_db)
):
    try:
        login_response = await create_refresh_token(db, refresh_token_data=refresh_token_data)
        return login_response

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
@auth_router.post("/change-password")
async def change_password(
    change_password_data: ChangePasswordRequest,
    db: AsyncSession = Depends(get_async_db),
    user: dict = Security(get_current_user_v2)
):
    try:
        response = await change_user_password(db, change_password_data,user)
        return response
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error changing password: {str(e)}"
        )