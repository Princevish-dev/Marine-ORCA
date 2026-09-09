from fastapi import APIRouter, Request, Depends
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.models import ChatRequest, ChatResponse
from app.agents.orchestrator import run_orca
from app.api.auth import require_api_user

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post("/chat", response_model=ChatResponse)
@limiter.limit("20/minute")
async def chat(
    request: Request,
    body: ChatRequest,
    _user: dict = Depends(require_api_user),
):
    response = await run_orca(body)
    return response
