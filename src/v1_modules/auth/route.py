from fastapi import Depends, HTTPException, status, APIRouter, Security

from sqlalchemy.ext.asyncio import AsyncSession

from src.v1_modules.auth.crud import  get_current_user_v2
from src.v1_modules.auth.schema import UserDetailResponse, LoginRequest, RegisterUserRequest
from src.v1_modules.auth.services import get_user_details_from_db, login_user, get_all_roles, \
    register_user
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

# @auth_router.post("/register")
# async def register(
#     registration_data: RegisterUserRequest,
#     db: AsyncSession = Depends(get_async_db),
#     token: str = Depends(oauth2_scheme),
# ):
#     return await register_user(db, registration_data, token)

@auth_router.post("/register")
async def register(
    registration_data: RegisterUserRequest,
    db: AsyncSession = Depends(get_async_db),
    user: dict = Security(get_current_user_v2)
):
    return await register_user(db, registration_data, user)
