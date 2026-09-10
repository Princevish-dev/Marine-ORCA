from __future__ import annotations
import base64
import logging
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger("orca.bhashini")

router = APIRouter(prefix="/api/bhashini", tags=["bhashini"])


class ASRRequest(BaseModel):
    audio_base64: str
    language: str = "hi"
    sample_rate: int = 16000


class ASRResponse(BaseModel):
    transcript: str
    confidence: float


class TTSRequest(BaseModel):
    text: str
    language: str = "hi"
    speaker: Optional[str] = None


class TTSResponse(BaseModel):
    audio_base64: str
    mime_type: str


def _get_auth_headers() -> dict[str, str]:
    if not settings.bhashini_api_key:
        raise HTTPException(status_code=503, detail="Bhashini API key not configured")
    return {
        "Authorization": f"Bearer {settings.bhashini_api_key}",
        "Content-Type": "application/json",
    }


def _lang_code(lang: str) -> tuple[str, str]:
    """Map language code to Bhashini source/target language codes."""
    lang_map = {
        "hi": ("hi", "hi"),
        "bn": ("bn", "bn"),
        "ta": ("ta", "ta"),
        "te": ("te", "te"),
        "mr": ("mr", "mr"),
        "gu": ("gu", "gu"),
        "kn": ("kn", "kn"),
        "en": ("en", "en"),
    }
    return lang_map.get(lang, ("en", "en"))


@router.post("/asr", response_model=ASRResponse)
async def asr_transcribe(req: ASRRequest):
    """
    Proxy to Bhashini ASR (Automatic Speech Recognition).
    Accepts base64-encoded audio and returns transcript.
    """
    source_lang, _ = _lang_code(req.language)

    payload = {
        "pipelineTasks": [
            {
                "taskType": "asr",
                "config": {
                    "language": {"sourceLanguage": source_lang},
                    "audioFormat": "wav",
                    "sampleRate": req.sample_rate,
                },
            }
        ],
        "inputData": {
            "audio": [
                {
                    "audioContent": req.audio_base64,
                }
            ]
        },
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.bhashini_base_url}/model/compute",
                headers=_get_auth_headers(),
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        transcript = ""
        confidence = 0.0
        if data.get("pipelineResponse"):
            for task in data["pipelineResponse"]:
                if task.get("taskType") == "asr":
                    output = task.get("output", [])
                    if output:
                        transcript = output[0].get("source", "")
                        confidence = output[0].get("confidence", 0.0)

        return ASRResponse(transcript=transcript, confidence=confidence)

    except httpx.HTTPStatusError as e:
        logger.error(f"Bhashini ASR error: {e.response.status_code} - {e.response.text}")
        raise HTTPException(status_code=502, detail=f"Bhashini ASR failed: {e.response.text}")
    except Exception as e:
        logger.error(f"Bhashini ASR exception: {e}")
        raise HTTPException(status_code=500, detail=f"Bhashini ASR error: {str(e)}")


@router.post("/tts", response_model=TTSResponse)
async def tts_synthesize(req: TTSRequest):
    """
    Proxy to Bhashini TTS (Text-to-Speech).
    Accepts text and returns base64-encoded audio.
    """
    _, target_lang = _lang_code(req.language)

    payload = {
        "pipelineTasks": [
            {
                "taskType": "tts",
                "config": {
                    "language": {"targetLanguage": target_lang},
                    "gender": "female",
                },
            }
        ],
        "inputData": {
            "input": [
                {
                    "source": req.text,
                }
            ]
        },
    }

    if req.speaker:
        payload["pipelineTasks"][0]["config"]["speaker"] = req.speaker

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.bhashini_base_url}/model/compute",
                headers=_get_auth_headers(),
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        audio_base64 = ""
        mime_type = "audio/wav"
        if data.get("pipelineResponse"):
            for task in data["pipelineResponse"]:
                if task.get("taskType") == "tts":
                    output = task.get("output", [])
                    if output:
                        audio_base64 = output[0].get("audioContent", "")
                        mime_type = output[0].get("mimeType", "audio/wav")

        return TTSResponse(audio_base64=audio_base64, mime_type=mime_type)

    except httpx.HTTPStatusError as e:
        logger.error(f"Bhashini TTS error: {e.response.status_code} - {e.response.text}")
        raise HTTPException(status_code=502, detail=f"Bhashini TTS failed: {e.response.text}")
    except Exception as e:
        logger.error(f"Bhashini TTS exception: {e}")
        raise HTTPException(status_code=500, detail=f"Bhashini TTS error: {str(e)}")


@router.get("/health")
async def health_check():
    """Check if Bhashini API is configured."""
    return {
        "configured": bool(settings.bhashini_api_key),
        "base_url": settings.bhashini_base_url,
    }