from fastapi import APIRouter
from src.routes.v1 import router as main_routes

router = APIRouter()

router.include_router(main_routes)

