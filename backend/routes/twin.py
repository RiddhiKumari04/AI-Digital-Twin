"""
routes/twin.py — Core Digital Twin endpoints:
  GET  /ask
  GET  /ask_stream
  POST /analyze_image
  POST /style_mirror
  POST /train
  GET  /memories
  DELETE /memories/{memory_id}
  GET  /export
  GET  /analytics
  GET  /status
  GET  /recommend_gift
"""

import csv
import random
import io
from typing import List

from fastapi import APIRouter, HTTPException, File, UploadFile
from fastapi.responses import StreamingResponse

import google.generativeai as genai  # pyright: ignore[reportMissingImports]

from config import knowledge_col, chat_histories, GEMINI_KEY, MODEL_NAME
from ai_providers import generate_ai_response, llm
from utils import _looks_like_realtime_request, web_search_snippets

router = APIRouter()


@router.get("/status")
async def get_status():
    return {"mongodb": "Connected", "chromadb": "Active", "ai": MODEL_NAME}


@router.get("/analytics")
async def get_analytics(user_id: str):
    results = knowledge_col.get(where={"user": user_id})
    categories = [meta.get("category", "General") for meta in results["metadatas"]]
    counts = {cat: categories.count(cat) for cat in set(categories)}
    return {"counts": counts}


@router.get("/memories")
async def get_memories(user_id: str):
    results = knowledge_col.get(where={"user": user_id})
    return {"memories": results["documents"], "ids": results["ids"]}


@router.delete("/memories/{memory_id}")
async def delete_memory(memory_id: str):
    knowledge_col.delete(ids=[memory_id])
    return {"status": "deleted"}


@router.get("/export")
async def export_memories(user_id: str):
    results = knowledge_col.get(where={"user": user_id})
    if not results["documents"]:
        raise HTTPException(status_code=404)
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(["Memory", "Category"])
    for doc, meta in zip(results["documents"], results["metadatas"]):
        writer.writerow([doc, meta.get("category", "General")])
    return StreamingResponse(
        io.BytesIO(stream.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={user_id}_memories.csv"},
    )


@router.post("/train")
async def train_twin(user_id: str, details: str):
    cat_prompt = f"Categorize this fact into one word (Personal, Work, Hobby, Coding): {details}"
    category = llm.invoke(cat_prompt).strip()
    count = knowledge_col.count()
    knowledge_col.add(
        documents=[details],
        metadatas=[{"user": user_id, "category": category}],
        ids=[f"{user_id}_{count}_{random.randint(100, 999)}"],
    )
    return {"status": "success"}


@router.get("/recommend_gift")
async def recommend_gift(user_id: str, person_name: str, mood: str):
    results = knowledge_col.query(
        query_texts=[f"About {person_name}"], n_results=5, where={"user": user_id}
    )
    context = (
        "\n".join(results["documents"][0])
        if results["documents"]
        else f"No specific memories of {person_name}."
    )
    search_block = web_search_snippets(
        f"best gift ideas for {person_name} price India", max_results=5
    )
    prompt = (
        f"You are the AI Digital Twin of {user_id}. Personality: {mood}\n"
        f"MEMORIES OF {person_name}: {context}\n"
        f"TASK: Recommend 3 gift ideas for {person_name} based on these memories. "
        "If web results are provided, use them to suggest real products and approximate prices.\n\n"
        f"WEB RESULTS:\n{search_block if search_block else 'No web results available.'}\n"
    )
    try:
        answer = generate_ai_response(prompt)
        return {"answer": answer}
    except Exception as e:
        return {"answer": f"Gift Agent Error: {str(e)}"}


@router.post("/analyze_image")
async def analyze_image(
    user_id: str,
    question: str,
    mood: str,
    files: List[UploadFile] = File(...),
):
    results = knowledge_col.query(
        query_texts=[question, "fashion preferences"], n_results=5, where={"user": user_id}
    )
    context = (
        "\n".join(results["documents"][0])
        if results["documents"]
        else "No specific personal preference found."
    )
    image_parts = []
    for f in files:
        image_data = await f.read()
        image_parts.append({"mime_type": f.content_type, "data": image_data})

    prompt = (
        f"You are the AI Digital Twin of {user_id}. Personality Mode: {mood}\n"
        f"USER PERSONAL CONTEXT: {context}\n"
        f"QUESTION: {question}\n\n"
        "Analyze the image and user preferences."
    )
    if _looks_like_realtime_request(question):
        search_block = web_search_snippets(f"{question} t-shirt price", max_results=6)
        prompt += f"\n\nWEB RESULTS:\n{search_block if search_block else 'No web results available.'}\n"

    try:
        try:
            genai.configure(api_key=GEMINI_KEY)
            vision_model = genai.GenerativeModel(MODEL_NAME)
            response = vision_model.generate_content([prompt] + image_parts)
            answer = response.text
        except Exception:
            answer = generate_ai_response(prompt)
        if user_id not in chat_histories:
            chat_histories[user_id] = []
        chat_histories[user_id].extend(
            [f"User (Image): {question}", f"Twin: {answer}"]
        )
        return {"answer": answer}
    except Exception as e:
        return {"answer": f"Vision AI Error: {str(e)}"}


@router.get("/ask")
async def ask_twin(user_id: str, question: str, mood: str = "Natural"):
    results = knowledge_col.query(
        query_texts=[question], n_results=3, where={"user": user_id}
    )
    context = "\n".join(results["documents"][0]) if results["documents"] else ""
    history_text = "\n".join(chat_histories.get(user_id, [])[-6:])
    try:
        prompt = (
            f"You are the AI Digital Twin of {user_id}. Personality Mode: {mood}\n"
            f"Context:\n{context}\n\n"
            f"Conversation History:\n{history_text}\n\n"
            f"User Question:\n{question}\n\n"
        )
        if _looks_like_realtime_request(question):
            search_block = web_search_snippets(question, max_results=4)
            prompt += f"WEB RESULTS:\n{search_block if search_block else 'No web results available.'}\n\n"
        prompt += "Answer:"

        answer = generate_ai_response(prompt)

        if user_id not in chat_histories:
            chat_histories[user_id] = []
        chat_histories[user_id].extend([f"User: {question}", f"Twin: {answer}"])
        return {"answer": answer}
    except Exception as e:
        return {"answer": f"AI Error: {str(e)}"}


@router.get("/ask_stream")
async def ask_twin_stream(user_id: str, question: str, mood: str = "Natural"):
    """
    Streaming version of /ask — returns Server-Sent Events (text/event-stream).
    Each chunk is sent as: data: <token>\n\n
    Final chunk is:         data: [DONE]\n\n
    """
    results = knowledge_col.query(
        query_texts=[question], n_results=3, where={"user": user_id}
    )
    context = "\n".join(results["documents"][0]) if results["documents"] else ""
    history_text = "\n".join(chat_histories.get(user_id, [])[-6:])
    prompt = (
        f"You are the AI Digital Twin of {user_id}. Personality Mode: {mood}\n"
        f"Context:\n{context}\n\n"
        f"Conversation History:\n{history_text}\n\n"
        f"User Question:\n{question}\n\n"
    )
    if _looks_like_realtime_request(question):
        search_block = web_search_snippets(question, max_results=4)
        prompt += f"WEB RESULTS:\n{search_block if search_block else 'No web results available.'}\n\n"
    prompt += "Answer:"

    import asyncio

    async def event_generator():
        full_answer = ""
        try:
            try:
                genai.configure(api_key=GEMINI_KEY)
                chat_model = genai.GenerativeModel(MODEL_NAME)
                response = chat_model.generate_content(prompt, stream=True)
                for chunk in response:
                    chunk_text = getattr(chunk, "text", "") or ""
                    if chunk_text:
                        full_answer += chunk_text
                        for word in chunk_text.split(" "):
                            if word:
                                safe = (word + " ").replace("\n", "\\n")
                                yield f"data: {safe}\n\n"
                                await asyncio.sleep(0.025)
                            else:
                                yield "data:  \n\n"
                                await asyncio.sleep(0.01)
            except Exception:
                full_answer = generate_ai_response(prompt)
                for word in full_answer.split(" "):
                    safe = (word + " ").replace("\n", "\\n")
                    yield f"data: {safe}\n\n"
                    await asyncio.sleep(0.03)
        except Exception as e:
            yield f"data: AI Error: {str(e)}\n\n"
        finally:
            if full_answer:
                if user_id not in chat_histories:
                    chat_histories[user_id] = []
                chat_histories[user_id].extend([f"User: {question}", f"Twin: {full_answer}"])
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/style_mirror")
async def style_mirror(
    user_id: str,
    mood: str = "Natural",
    occasion: str = "casual",
    files: List[UploadFile] = File(...),
):
    style_results = knowledge_col.query(
        query_texts=[
            "fashion style preference clothing outfit colour wardrobe",
            "favourite colors brands clothing style",
        ],
        n_results=8,
        where={"user": user_id},
    )
    style_context = (
        "\n".join(style_results["documents"][0])
        if style_results["documents"] and style_results["documents"][0]
        else "No personal style preferences found in memory."
    )
    image_parts = []
    for f in files:
        image_data = await f.read()
        image_parts.append({"mime_type": f.content_type, "data": image_data})

    prompt = (
        f"You are the AI Digital Twin and personal fashion stylist of {user_id}. "
        f"Personality Mode: {mood}\n\n"
        f"PERSONAL STYLE PROFILE (from memory):\n{style_context}\n\n"
        f"OCCASION: {occasion}\n\n"
        "TASK: Analyse the outfit in the uploaded photo(s) and act as a brutally honest yet "
        "encouraging personal stylist who knows the user intimately.\n\n"
        "Your response MUST follow this exact structure:\n\n"
        "## 👗 Style Mirror Report\n\n"
        "**Overall Score: X/10**  ← give a score out of 10\n\n"
        "**Verdict:** One punchy sentence (e.g. 'Classic you — clean lines, solid palette.')\n\n"
        "### ✅ What's Working\n"
        "- List 2–3 specific things done well, referencing their personal style profile where possible.\n\n"
        "### ⚠️ What Could Be Better\n"
        "- List 1–3 honest, constructive critiques tied to the occasion and their known preferences.\n\n"
        "### 💡 Stylist Tips\n"
        "- Give 2–3 actionable suggestions (accessories, swaps, colour tweaks) that align with their style.\n\n"
        "### 🔁 Style Match\n"
        "- Explain how well this outfit matches their personal style profile (high / medium / low match and why).\n\n"
        "Be specific — mention actual colours, garment types, fits you can see in the photo. "
        "If no style profile exists, base the score purely on general fashion principles for the occasion."
    )
    try:
        try:
            genai.configure(api_key=GEMINI_KEY)
            vision_model = genai.GenerativeModel(MODEL_NAME)
            response = vision_model.generate_content([prompt] + image_parts)
            answer = response.text
        except Exception:
            answer = generate_ai_response(prompt)
        if user_id not in chat_histories:
            chat_histories[user_id] = []
        chat_histories[user_id].extend(
            [f"User (Style Mirror - {occasion}): [outfit photo]", f"Twin: {answer}"]
        )
        return {"answer": answer}
    except Exception as e:
        return {"answer": f"Style Mirror Error: {str(e)}"}
