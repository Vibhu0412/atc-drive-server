from fastapi import APIRouter

from src.v1_modules.auth.route import auth_router
from src.v1_modules.folder_managment.route import folder_router

router = APIRouter(prefix="/v1")

router.include_router(auth_router, prefix="/auth")
router.include_router(folder_router, prefix="/folder")
