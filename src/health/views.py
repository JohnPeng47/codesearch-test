from fastapi import APIRouter, Depends
from src.models import HTTPSuccess
from src.auth.service import get_current_user
from src.auth.models import User


health_router = APIRouter()


@health_router.get("/health")
async def health():
    return HTTPSuccess()
