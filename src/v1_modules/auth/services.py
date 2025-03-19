from datetime import timedelta, datetime
from uuid import UUID

import pytz
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.future import select
from fastapi import status
from sqlalchemy.orm import selectinload

from src.v1_modules.auth.crud import get_role_by_user_id, get_user, get_user_role_from_token, get_current_user
from src.v1_modules.auth.model import User, Role
from src.v1_modules.auth.schema import LoginRequest, UserResponse, RoleResponse, LoginResponse, RegisterUserRequest, \
 UserResponseForGet
from src.config.logger import logger
from src.utills.response import Response
from src.utills.toekn_utills import Token
from src.utills.hash_utills import Hasher as hash

async def login_user(db, login_data: LoginRequest):
    try:
        logger.info("Attempting to log in user")
        user = await get_user(db, email=login_data.email)
        if not user:
            logger.warning("Invalid credentials")
            return Response(
                status_code=401,
                message="Invalid credentials"
            ).send_error_response()

        if not hash.verify_password(login_data.password, user.password_hash):
            logger.warning("Invalid credentials")
            return Response(
                status_code=401,
                message="Invalid credentials"
            ).send_error_response()
        role = await get_role_by_user_id(db, user.role_id)

        token_handler = Token()
        access_token = token_handler.create_access_token(
            data={"sub": user.username},
            expires_delta=timedelta(minutes=1)
        )
        refresh_token = token_handler.create_link_token()

        user.last_login = datetime.now(pytz.utc)
        db.add(user)
        await db.commit()
        await db.refresh(user)

        response_data = LoginResponse(
            user=UserResponse(**user.__dict__),
            role=RoleResponse(**role.__dict__),
            access_token=access_token,
            refresh_token=refresh_token
        )

        logger.info("Login successful")
        return Response(
            data=response_data,
            message="Login successful",
            status_code=200
        ).send_success_response()

    except Exception as e:
        await db.rollback()
        logger.error(f"Login failed: {str(e)}")
        return Response(
            status_code=500,
            message=f"Login failed: {str(e)}"
        ).send_error_response()

async def get_user_details_from_db(user_id: UUID, db) -> User:
    """
    This service function fetches a user and their associated role
    based on the user_id.
    """
    try:
        logger.info(f"Fetching user details for user_id: {user_id}")
        stmt = (
            select(User)
            .join(Role)
            .where(User.id == user_id)
        )
        result = await db.execute(stmt)

        user = result.scalars().first()
        print("users",user)
        if not user:
            logger.warning("User not found")
            return Response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="User not found"
            ).send_error_response()

        logger.info("User details fetched successfully")
        return Response(
            data=user,
            message="User details fetched successfully",
            status_code=200
        ).send_success_response()

    except SQLAlchemyError as e:
        logger.error(f"Database error: {str(e)}")
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Database error: {str(e)}"
        ).send_error_response()
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Unexpected error: {str(e)}"
        ).send_error_response()

async def get_all_roles(db) -> User:
    try:
        logger.info(f"Fetching all role details")
        stmt = (
            select(Role)
        )
        result = await db.execute(stmt)

        roles = result.scalars().all()

        role_responses = [RoleResponse(**role.__dict__) for role in roles]
        if not roles:
            logger.warning("roles not found")
            return Response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="roles not found"
            ).send_error_response()

        logger.info("roles details fetched successfully")
        return Response(
            data=role_responses,
            message="roles details fetched successfully",
            status_code=200
        ).send_success_response()

    except SQLAlchemyError as e:
        logger.error(f"Database error: {str(e)}")
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Database error: {str(e)}"
        ).send_error_response()
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Unexpected error: {str(e)}"
        ).send_error_response()


async def register_user(db, request: RegisterUserRequest, user) -> dict:
    try:
        user_role = await get_user_role_from_token(db, user)

        if user_role.name != "admin":
            return Response(
                status_code=status.HTTP_403_FORBIDDEN,
                message="Only admins can register users."
            ).send_error_response()

        hashed_password = hash.hash_password(request.password_hash)

        user_data = request.dict()
        user_data["password_hash"] = str(hashed_password)

        new_user = User(**user_data)

        db.add(new_user)
        await db.commit()

        response_data = {
            "username": new_user.username,
            "email": new_user.email,
            "role_id": str(new_user.role_id)
        }

        return Response(
            data=response_data,
            message="User registered successfully",
            status_code=status.HTTP_201_CREATED
        ).send_success_response()

    except Exception as e:
        await db.rollback()
        logger.error(f"User registration failed: {str(e)}")
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"User registration failed: {str(e)}"
        ).send_error_response()



async def get_all_users(db):
    """
    Fetch all users along with their role details.
    """
    try:
        logger.info("Fetching all users with role details")

        # Query to fetch all users with role details
        query = select(User).options(selectinload(User.role_details))
        result = await db.execute(query)
        users = result.scalars().all()

        # Prepare the response data using Pydantic models
        user_list = []
        for user in users:
            role_response = RoleResponse(
                id=user.role_details.id,
                name=user.role_details.name,
                can_view=user.role_details.can_view,
                can_edit=user.role_details.can_edit,
                can_delete=user.role_details.can_delete,
                can_create=user.role_details.can_create,
                can_share=user.role_details.can_share,
            )
            user_response = UserResponseForGet(
                id=user.id,
                username=user.username,
                email=user.email,
                role=role_response,
                created_at=user.created_at,
                last_login=user.last_login,
            )
            user_list.append(user_response.dict())

        logger.info("Users retrieved successfully")
        return Response(
            data=user_list,
            message="Users retrieved successfully",
            status_code=200
        ).send_success_response()

    except Exception as e:
        logger.error(f"Failed to fetch users: {str(e)}")
        return Response(
            status_code=500,
            message=f"Failed to fetch users: {str(e)}"
        ).send_error_response()