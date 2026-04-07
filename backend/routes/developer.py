"""
routes/developer.py — Shadow Developer endpoints:
  POST /debug_code
  GET  /repo_files
"""

import subprocess
import tempfile
from typing import List, Optional

from fastapi import APIRouter, HTTPException

from config import knowledge_col
from ai_providers import generate_ai_response
from models import DebugCodeRequest
from utils import (
    detect_syntax_errors, execute_code, generate_diff,
    read_git_repo_files, extract_code_block, LANGUAGE_EXTENSIONS,
)

router = APIRouter()


@router.post("/debug_code")
async def debug_code(req: DebugCodeRequest):
    """
    Enhanced Shadow Developer endpoint with:
    - Syntax error detection before Gemini
    - Optional code execution (original + fixed)
    - Diff generation between original and fixed
    - Optional git repo file context
    """
    lang = req.language.lower()
    response_payload: dict = {
        "syntax_check": {},
        "execution_original": {},
        "ai_analysis": "",
        "fixed_code": "",
        "diff": "",
        "execution_fixed": {},
        "repo_context_used": False,
        "repo_files_read": 0,
    }

    # ── 1. SYNTAX CHECK ──────────────────────────────────────────
    syntax = detect_syntax_errors(req.code, lang)
    response_payload["syntax_check"] = syntax

    # ── 2. OPTIONAL: RUN ORIGINAL CODE ───────────────────────────
    if req.run_code:
        exec_result = execute_code(req.code, lang)
        response_payload["execution_original"] = exec_result

    # ── 3. OPTIONAL: PULL REPO CONTEXT ───────────────────────────
    repo_context_block = ""
    if req.repo_path.strip():
        repo_data = read_git_repo_files(req.repo_path.strip())
        if repo_data["files"]:
            snippets = []
            for rel_path, content in list(repo_data["files"].items())[:10]:
                snippets.append(f"### {rel_path}\n```\n{content[:1500]}\n```")
            repo_context_block = (
                f"\n\nREPO CONTEXT ({repo_data['total_files_found']} files"
                f"{', truncated' if repo_data['truncated'] else ''}):\n"
                + "\n\n".join(snippets)
            )
            response_payload["repo_context_used"] = True
            response_payload["repo_files_read"] = repo_data["total_files_found"]
        if repo_data["errors"]:
            response_payload["repo_errors"] = repo_data["errors"]

    # ── 4. PULL USER CODING STYLE FROM MEMORY ───────────────────
    style_results = knowledge_col.query(
        query_texts=["coding style programming patterns habits"],
        n_results=6,
        where={"user": req.user_id},
    )
    style_context = (
        "\n".join(style_results["documents"][0])
        if style_results["documents"] and style_results["documents"][0]
        else "No personal coding style recorded."
    )

    # ── 5. BUILD SYNTAX ERROR BLOCK FOR PROMPT ──────────────────
    syntax_block = ""
    if syntax["errors"]:
        syntax_block += "\n\nPRE-ANALYSIS SYNTAX ERRORS DETECTED:\n"
        syntax_block += "\n".join(f"  ❌ {e}" for e in syntax["errors"])
    if syntax["warnings"]:
        syntax_block += "\n\nPRE-ANALYSIS WARNINGS:\n"
        syntax_block += "\n".join(f"  ⚠️  {w}" for w in syntax["warnings"])

    # ── 6. BUILD EXECUTION CONTEXT FOR PROMPT ───────────────────
    exec_block = ""
    if req.run_code and response_payload["execution_original"].get("ran"):
        eo = response_payload["execution_original"]
        exec_block = (
            f"\n\nORIGINAL CODE EXECUTION RESULT:\n"
            f"  Exit code: {eo['exit_code']}\n"
            f"  STDOUT:\n{eo['stdout'] or '(empty)'}\n"
            f"  STDERR:\n{eo['stderr'] or '(none)'}\n"
        )

    # ── 7. CALL AI (with fallback chain) ─────────────────────────
    prompt = (
        f"You are the AI Digital Twin and Shadow Developer of {req.user_id}. "
        f"Personality Mode: {req.mood}\n\n"
        f"PERSONAL CODING STYLE PROFILE:\n{style_context}\n"
        f"{syntax_block}"
        f"{exec_block}"
        f"{repo_context_block}\n\n"
        f"TASK: {req.mode}\n"
        f"LANGUAGE: {req.language}\n"
        f"EXTRA CONTEXT: {req.extra_context or 'None provided.'}\n\n"
        f"CODE TO ANALYSE:\n```{lang}\n{req.code}\n```\n\n"
        "INSTRUCTIONS:\n"
        "1. Identify the user's coding style from the style profile above.\n"
        "2. Perform the requested task.\n"
        "3. If fixing bugs or optimising, output the COMPLETE fixed code inside a single fenced "
        "   code block (``` ... ```) — no partial snippets.\n"
        "4. After the code block, provide a clear explanation of every change made.\n"
        "5. Match the user's exact style: variable naming, indentation, error-handling patterns.\n"
        "6. If syntax errors were detected above, address each one explicitly.\n"
        "7. Be specific — reference exact line numbers where relevant.\n"
    )

    try:
        ai_response = generate_ai_response(prompt)
        response_payload["ai_analysis"] = ai_response

        # ── 8. EXTRACT FIXED CODE + GENERATE DIFF ────────────────
        fixed_code = extract_code_block(ai_response)

        if fixed_code and fixed_code.strip() != req.code.strip():
            response_payload["fixed_code"] = fixed_code
            response_payload["diff"] = generate_diff(
                req.code,
                fixed_code,
                filename=f"code{LANGUAGE_EXTENSIONS.get(lang, '.txt')}",
            )
        else:
            response_payload["fixed_code"] = ""
            response_payload["diff"] = "No changes — code appears identical or AI did not produce a fix."

        # ── 9. OPTIONAL: RUN FIXED CODE ───────────────────────────
        if req.run_fixed and fixed_code and fixed_code.strip() != req.code.strip():
            exec_fixed = execute_code(fixed_code, lang)
            response_payload["execution_fixed"] = exec_fixed

        return response_payload

    except Exception as e:
        response_payload["ai_analysis"] = f"AI Error: {str(e)}"
        return response_payload


@router.get("/repo_files")
async def get_repo_files(
    repo_path: str,
    extensions: Optional[str] = None,
    max_files: int = 25,
):
    """
    Browse a local git repo or clone a GitHub URL and return file contents.
    Query params:
      - repo_path: local path OR a https://github.com/... URL
      - extensions: comma-separated list e.g. '.py,.js,.ts'  (optional)
      - max_files: max number of files to return (default 25)
    """
    ext_list: Optional[List[str]] = None
    if extensions:
        ext_list = [e.strip() for e in extensions.split(",") if e.strip()]

    tmp_dir = None
    actual_path = repo_path.strip()
    is_github_url = actual_path.startswith("https://github.com/") or actual_path.startswith("http://github.com/")

    if is_github_url:
        clone_url = actual_path.rstrip("/")
        if not clone_url.endswith(".git"):
            clone_url = clone_url + ".git"

        tmp_dir = tempfile.mkdtemp(prefix="adt_repo_")
        try:
            result = subprocess.run(
                ["git", "clone", "--depth=1", clone_url, tmp_dir],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                import shutil
                shutil.rmtree(tmp_dir, ignore_errors=True)
                err_msg = result.stderr.strip() or "git clone failed"
                raise HTTPException(
                    status_code=400,
                    detail=f"Could not clone GitHub repo: {err_msg}",
                )
            actual_path = tmp_dir
        except subprocess.TimeoutExpired:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)
            raise HTTPException(status_code=408, detail="git clone timed out (60s). Try a smaller repo.")
        except FileNotFoundError:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)
            raise HTTPException(
                status_code=500,
                detail="'git' command not found on server. Please install git or provide a local path.",
            )

    try:
        data = read_git_repo_files(actual_path, extensions=ext_list, max_files=max_files)
    finally:
        if tmp_dir:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)

    if data["errors"] and not data["files"]:
        raise HTTPException(status_code=404, detail="; ".join(data["errors"]))

    return {
        "files": data["files"],
        "errors": data["errors"],
        "truncated": data["truncated"],
        "is_git_repo": data.get("is_git_repo", False),
        "total_files": data.get("total_files_found", len(data["files"])),
        "source": "github" if is_github_url else "local",
    }
