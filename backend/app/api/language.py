from fastapi import APIRouter, Body
from app.services.ollama import generate_ollama_response

router = APIRouter()

@router.post("/language/detect")
async def detect_lang(payload: dict = Body(...)):
    user_text = payload.get("text", "")
    prompt = f"You are a language detection service. Given the following text, return ONLY the ISO 639-1 language code (e.g., 'hi', 'en', 'ta', 'bn', 'te', 'mr', 'gu', 'kn'). Do not return any other text.\n\nText: {user_text}\n\nLanguage code:"
    try:
        lang_code = generate_ollama_response(prompt).strip()
        if not lang_code or len(lang_code) > 3:
            lang_code = "en"
    except Exception:
        lang_code = "en"
    return {"language": lang_code.lower()}

@router.post("/language/translate")
async def translate_lang(payload: dict = Body(...)):
    english_text = payload.get("text", "")
    target_language = payload.get("target_language", "en")
    
    if target_language == "en":
        return {"translation": english_text}
        
    prompt = f"You are a translator. Translate the following text from English to {target_language}. Return only the translated text, no explanations.\n\nText: {english_text}\n\nTranslation:"
    try:
        translation = generate_ollama_response(prompt).strip()
    except Exception:
        translation = english_text
    return {"translation": translation}
