from fastapi import APIRouter
from app.config import settings
from app.guardian.guardian import get_guardian_status

router = APIRouter()


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "demo_mode": settings.demo_mode,
        "guardian": get_guardian_status(),
        "version": "1.0.0",
    }
