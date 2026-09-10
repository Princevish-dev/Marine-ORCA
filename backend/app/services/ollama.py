from __future__ import annotations

import httpx

from app.config import settings


def generate_ollama_response(prompt: str, system: str = "") -> str | None:
    if not settings.ollama_enabled:
        return None

    try:
        response = httpx.post(
            f"{settings.ollama_url}/api/generate",
            json={
                "model": settings.ollama_model,
                "system": system,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.2, "num_predict": 700},
            },
            timeout=8.0,
        )
        response.raise_for_status()
        result = response.json().get("response", "").strip()
        return result[:2000] or None
    except (httpx.HTTPError, ValueError):
        return None


def generate_local_context(query: str, history: list[dict[str, str]]) -> str | None:
    transcript = "\n".join(
        f"{item.get('role', 'user')}: {item.get('content', '')[:500]}"
        for item in history[-8:]
    )
    return generate_ollama_response(
        f"Previous context:\n{transcript}\nCurrent query: {query}",
        "Summarize relevant previous user context only. Do not invent marine facts.",
    )