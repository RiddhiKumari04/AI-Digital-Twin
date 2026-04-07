"""
routes/misc.py — Miscellaneous endpoints:
  POST /translate
"""

from fastapi import APIRouter, HTTPException

from ai_providers import llm

router = APIRouter()


@router.post("/translate")
async def translate_text(data: dict):
    text        = data.get("text", "")
    target_lang = data.get("target_lang", "English")
    if not text:
        return {"translated": ""}
    prompt = f"""Translate the following text to {target_lang}. 
Return ONLY the translated text, nothing else.

Text: {text}"""
    try:
        result = llm.invoke(prompt)
        return {"translated": result.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
