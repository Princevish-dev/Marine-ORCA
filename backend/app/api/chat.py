from fastapi import APIRouter, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.models import ChatRequest, ChatResponse
from app.agents.orchestrator import run_orca

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post("/chat", response_model=ChatResponse)
@limiter.limit("20/minute")
async def chat(request: Request, body: ChatRequest):
    response = await run_orca(body)
    return response
