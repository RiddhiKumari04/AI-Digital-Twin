"""
routes/newsroom.py — Twin Newsroom (Morning Briefing) endpoint:
  POST /morning_briefing
"""

from datetime import datetime
from typing import List

from fastapi import APIRouter

from config import knowledge_col, chat_histories
from ai_providers import generate_ai_response, llm
from models import NewsroomRequest

router = APIRouter()


def _build_news_search_queries(
    tech_stack: List[str],
    locations: List[str],
    extra_topics: List[str],
) -> List[str]:
    """Build a diverse set of search queries from user context."""
    queries = []

    if extra_topics:
        for topic in extra_topics:
            queries.append(f"{topic} news today")
        for loc in locations:
            queries.append(f"{loc} latest news today")
        return queries

    for tech in tech_stack[:4]:
        queries.append(f"{tech} latest news 2025")

    for loc in locations[:2]:
        queries.append(f"{loc} technology news today")
        queries.append(f"{loc} latest news today")

    for topic in extra_topics[:3]:
        queries.append(f"{topic} news today")

    queries.append("AI developer tools news today")

    return queries


def _fetch_multi_search(queries: List[str], results_per_query: int = 4) -> List[dict]:
    """Run multiple DuckDuckGo searches and deduplicate by URL."""
    try:
        try:
            from ddgs import DDGS  # type: ignore  # new package name (pip install ddgs)
        except ImportError:
            from duckduckgo_search import DDGS  # type: ignore  # old package name fallback
    except Exception:
        return []

    seen_urls: set = set()
    all_results: List[dict] = []

    try:
        with DDGS() as ddgs:
            for query in queries:
                try:
                    for r in ddgs.text(query, max_results=results_per_query):
                        href = (r.get("href") or r.get("link") or "").strip()
                        if href and href not in seen_urls:
                            seen_urls.add(href)
                            all_results.append({
                                "title": (r.get("title") or "").strip(),
                                "url": href,
                                "body": (r.get("body") or "").strip()[:300],
                                "query": query,
                            })
                except Exception:
                    continue
    except Exception:
        return []

    return all_results


@router.post("/morning_briefing")
async def morning_briefing(req: NewsroomRequest):
    """
    Twin Newsroom: fetches live news relevant to the user's tech stack,
    location, and interests — then presents it as a personalised briefing
    written in the user's chosen personality/mood.
    """
    # ── 1. PULL USER INTERESTS FROM MEMORY ───────────────────────
    interest_results = knowledge_col.query(
        query_texts=[
            "tech stack programming languages frameworks tools",
            "interests hobbies work projects",
            "location city workplace",
        ],
        n_results=10,
        where={"user": req.user_id},
    )
    memory_context = (
        "\n".join(interest_results["documents"][0])
        if interest_results["documents"] and interest_results["documents"][0]
        else ""
    )

    # ── 2. EXTRACT TECH STACK FROM MEMORY VIA QUICK LLM CALL ─────
    tech_stack: List[str] = []
    if not req.extra_topics:
        if memory_context:
            try:
                extract_prompt = (
                    "From the following personal memory, extract a list of up to 6 specific "
                    "technologies, frameworks, or programming languages the person uses. "
                    "Return ONLY a comma-separated list, nothing else.\n\n"
                    f"MEMORY:\n{memory_context}"
                )
                raw_tech = llm.invoke(extract_prompt).strip()
                tech_stack = [t.strip() for t in raw_tech.split(",") if t.strip()][:6]
            except Exception:
                pass

    if not tech_stack and not req.extra_topics:
        tech_stack = ["Python", "FastAPI", "AI", "Machine Learning"]

    # ── 3. FETCH LIVE NEWS ────────────────────────────────────────
    queries = _build_news_search_queries(tech_stack, req.locations, req.extra_topics)
    raw_articles = _fetch_multi_search(queries, results_per_query=4)

    if not raw_articles:
        return {
            "briefing": (
                "⚠️ Could not fetch live news right now. "
                "Make sure `duckduckgo_search` is installed (`pip install duckduckgo-search`) "
                "and you have an internet connection."
            ),
            "articles_found": 0,
            "tech_stack_detected": tech_stack,
        }

    # ── 4. FORMAT RAW ARTICLES FOR PROMPT ────────────────────────
    article_lines = []
    for i, art in enumerate(raw_articles[:20], 1):
        article_lines.append(
            f"{i}. [{art['query']}] {art['title']}\n   {art['url']}\n   {art['body']}"
        )
    articles_block = "\n\n".join(article_lines)

    # ── 5. MOOD-SPECIFIC PERSONA INSTRUCTIONS ────────────────────
    mood_instructions = {
        "Professional": (
            "Write in a crisp, executive-briefing style. Use confident, direct language. "
            "Group stories by category (Tech, Local, Industry). "
            "Conclude with one sharp 'Key Takeaway for Today'."
        ),
        "Sarcastic": (
            "Write like you're a snarky, self-aware version of the user reading the news to themselves. "
            "Add dry wit, light sarcasm, and the occasional eye-roll emoji. "
            "Still cover all key stories but make it entertaining. "
            "End with a sarcastic 'Deep Thought of the Morning'."
        ),
        "Natural": (
            "Write in a warm, conversational tone — like a smart friend catching you up over coffee. "
            "Be engaging but concise. End with a friendly 'One Thing to Watch Today'."
        ),
    }
    persona = mood_instructions.get(req.mood, mood_instructions["Natural"])

    # ── 6. BUILD PROMPT ───────────────────────────────────────────
    today = datetime.now().strftime("%A, %B %d %Y")
    prompt = (
        f"You are the AI Digital Twin of {req.user_id}. Today is {today}.\n"
        f"Personality Mode: {req.mood}\n\n"
        f"USER PROFILE:\n"
        f"  Tech Stack: {', '.join(tech_stack)}\n"
        f"  Locations of interest: {', '.join(req.locations)}\n"
        f"  Additional topics: {', '.join(req.extra_topics) if req.extra_topics else 'None'}\n\n"
        f"PERSONA INSTRUCTION: {persona}\n\n"
        f"RAW NEWS ARTICLES (fetched live):\n{articles_block}\n\n"
        "TASK: Write a personalised Morning Briefing for the user based on the articles above.\n\n"
        "FORMAT YOUR RESPONSE EXACTLY LIKE THIS:\n\n"
        "## 📰 Good Morning — Your Twin Newsroom\n"
        f"*{today}*\n\n"
        "### 💻 Tech & Dev Updates\n"
        "- Cover 3–4 most relevant tech/dev stories from the articles. "
        "Include the source URL inline as a markdown link.\n\n"
        "### 🌍 Local & Regional News\n"
        "- Cover 2–3 local/regional stories relevant to their location(s).\n\n"
        "### 🔮 What's Trending in Your World\n"
        "- 2 stories that intersect their interests/stack with current events.\n\n"
        "### ☕ [Closing Section — title depends on mood]\n"
        "- Your mood-appropriate closing insight (Key Takeaway / Deep Thought / One Thing to Watch).\n\n"
        "RULES:\n"
        "- Only use stories from the provided articles — do not invent news.\n"
        "- Every story must include a clickable markdown URL link.\n"
        "- Keep the whole briefing under 600 words.\n"
        "- Write it AS the user's twin — speak directly to them in second person.\n"
        "- Make it feel personal by referencing their specific tech stack and location.\n"
    )

    try:
        briefing = generate_ai_response(prompt)

        if req.user_id not in chat_histories:
            chat_histories[req.user_id] = []
        chat_histories[req.user_id].extend(
            [
                f"User: Morning briefing requested ({req.mood} mode)",
                f"Twin (Newsroom): {briefing[:300]}...",
            ]
        )

        return {
            "briefing": briefing,
            "articles_found": len(raw_articles),
            "tech_stack_detected": tech_stack,
            "queries_used": queries,
        }

    except Exception as e:
        return {
            "briefing": f"Newsroom Error: {str(e)}",
            "articles_found": len(raw_articles),
            "tech_stack_detected": tech_stack,
        }
