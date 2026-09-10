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

@router.get("/health/ollama")
async def check_ollama_health():
    import httpx
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.get("http://localhost:11434/")
            r.raise_for_status()
            return {"status": "online"}
    except Exception:
        return {"status": "offline"}
