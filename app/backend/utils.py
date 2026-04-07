"""
utils.py — Shared utility functions used across multiple route modules.
Includes Shadow Developer helpers, web search, syntax checking, and code execution.
"""

import os
import re
import ast
import sys
import subprocess
import tempfile
import difflib
from pathlib import Path
from typing import List, Optional


# ── Real-time request detection ───────────────────────────────────────────────

def _looks_like_realtime_request(text: str) -> bool:
    t = (text or "").lower()
    keywords = [
        "price", "prices", "best price", "cheapest", "buy",
        "where to buy", "amazon", "flipkart", "myntra",
        "ajio", "shop", "link", "available",
    ]
    return any(k in t for k in keywords)


# ── DuckDuckGo web search ─────────────────────────────────────────────────────

def web_search_snippets(query: str, max_results: int = 5) -> str:
    try:
        try:
            from ddgs import DDGS  # type: ignore  # new package name (pip install ddgs)
        except ImportError:
            from duckduckgo_search import DDGS  # type: ignore  # old package name fallback
    except Exception:
        return ""
    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                title = (r.get("title") or "").strip()
                href = (r.get("href") or r.get("link") or "").strip()
                body = (r.get("body") or "").strip()
                if title and href:
                    if body:
                        results.append(f"- {title} — {href}\n  {body}")
                    else:
                        results.append(f"- {title} — {href}")
    except Exception:
        return ""
    return "\n".join(results)


# ── Shadow Developer helpers ──────────────────────────────────────────────────

LANGUAGE_EXTENSIONS = {
    "python": ".py",
    "javascript": ".js",
    "typescript": ".ts",
    "java": ".java",
    "c++": ".cpp",
    "c": ".c",
    "go": ".go",
    "rust": ".rs",
    "bash": ".sh",
    "other": ".txt",
}

RUNNABLE_LANGUAGES = {"python", "javascript", "bash"}


def detect_syntax_errors(code: str, language: str) -> dict:
    """
    Attempt static syntax checking before sending to Gemini.
    Returns {"has_errors": bool, "errors": [str], "warnings": [str]}
    """
    lang = language.lower()
    errors = []
    warnings = []

    if lang == "python":
        try:
            ast.parse(code)
        except SyntaxError as e:
            errors.append(
                f"SyntaxError on line {e.lineno}: {e.msg}"
                + (f" — near `{e.text.strip()}`" if e.text else "")
            )
        except Exception as e:
            errors.append(f"Parse error: {str(e)}")

        lines = code.splitlines()
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("print ") and not stripped.startswith("print("):
                warnings.append(f"Line {i}: Looks like Python 2 print statement — use print()")
            if "==" in stripped and stripped.startswith("if") and "is None" not in stripped and "== None" in stripped:
                warnings.append(f"Line {i}: Use `is None` instead of `== None`")
            if stripped.startswith("except:") or stripped == "except :":
                warnings.append(f"Line {i}: Bare `except:` catches everything — consider `except Exception as e:`")

    elif lang in ("javascript", "typescript"):
        lines = code.splitlines()
        open_braces = code.count("{")
        close_braces = code.count("}")
        if open_braces != close_braces:
            errors.append(f"Mismatched braces: {open_braces} opening vs {close_braces} closing.")
        open_parens = code.count("(")
        close_parens = code.count(")")
        if open_parens != close_parens:
            errors.append(f"Mismatched parentheses: {open_parens} opening vs {close_parens} closing.")
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("var "):
                warnings.append(f"Line {i}: Consider replacing `var` with `let` or `const`.")
            if "==" in stripped and "===" not in stripped and "!==" not in stripped:
                warnings.append(f"Line {i}: Prefer `===` over `==` for strict equality.")

    elif lang in ("c", "c++"):
        open_braces = code.count("{")
        close_braces = code.count("}")
        if open_braces != close_braces:
            errors.append(f"Mismatched braces: {open_braces} opening vs {close_braces} closing.")
        for i, line in enumerate(code.splitlines(), 1):
            stripped = line.strip()
            if "gets(" in stripped:
                warnings.append(f"Line {i}: `gets()` is unsafe — use `fgets()` instead.")
            if "strcpy(" in stripped:
                warnings.append(f"Line {i}: `strcpy()` can overflow — consider `strncpy()`.")

    elif lang == "java":
        open_braces = code.count("{")
        close_braces = code.count("}")
        if open_braces != close_braces:
            errors.append(f"Mismatched braces: {open_braces} opening vs {close_braces} closing.")
        for i, line in enumerate(code.splitlines(), 1):
            stripped = line.strip()
            if "System.out.print" not in stripped and "==" in stripped:
                if ".equals(" not in stripped:
                    if '"' in stripped:
                        warnings.append(
                            f"Line {i}: String comparison with `==` may fail — use `.equals()`."
                        )

    return {
        "has_errors": len(errors) > 0,
        "errors": errors,
        "warnings": warnings,
    }


def execute_code(code: str, language: str, timeout: int = 10) -> dict:
    """
    Safely execute code in a subprocess and return stdout/stderr.
    Only runs Python, JavaScript (node), and Bash.
    """
    lang = language.lower()
    if lang not in RUNNABLE_LANGUAGES:
        return {
            "ran": False,
            "reason": f"Execution not supported for {language}. Supported: Python, JavaScript, Bash.",
            "stdout": "",
            "stderr": "",
            "exit_code": None,
        }

    ext = LANGUAGE_EXTENSIONS.get(lang, ".txt")

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=ext, delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    try:
        if lang == "python":
            cmd = [sys.executable, tmp_path]
        elif lang == "javascript":
            cmd = ["node", tmp_path]
        elif lang == "bash":
            cmd = ["bash", tmp_path]
        else:
            return {"ran": False, "reason": "Unknown language", "stdout": "", "stderr": "", "exit_code": None}

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return {
            "ran": True,
            "stdout": result.stdout[:3000],
            "stderr": result.stderr[:1500],
            "exit_code": result.returncode,
            "reason": "",
        }
    except subprocess.TimeoutExpired:
        return {
            "ran": True,
            "stdout": "",
            "stderr": f"⏰ Execution timed out after {timeout} seconds.",
            "exit_code": -1,
            "reason": "timeout",
        }
    except FileNotFoundError as e:
        return {
            "ran": False,
            "stdout": "",
            "stderr": "",
            "exit_code": None,
            "reason": f"Runtime not found: {str(e)}. Make sure the interpreter is installed.",
        }
    except Exception as e:
        return {
            "ran": False,
            "stdout": "",
            "stderr": "",
            "exit_code": None,
            "reason": f"Execution error: {str(e)}",
        }
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


def generate_diff(original: str, fixed: str, filename: str = "code") -> str:
    """Generate a unified diff between original and fixed code."""
    original_lines = original.splitlines(keepends=True)
    fixed_lines = fixed.splitlines(keepends=True)
    diff = list(
        difflib.unified_diff(
            original_lines,
            fixed_lines,
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
            lineterm="",
        )
    )
    if not diff:
        return "No changes detected."
    return "".join(diff)


def read_git_repo_files(
    repo_path: str,
    extensions: Optional[List[str]] = None,
    max_files: int = 20,
    max_bytes_per_file: int = 8000,
) -> dict:
    """
    Walk a local git repo and return file contents.
    Returns {"files": {relative_path: content}, "errors": [str], "truncated": bool}
    """
    if extensions is None:
        extensions = [
            ".py", ".js", ".ts", ".java", ".c", ".cpp", ".go",
            ".rs", ".sh", ".html", ".css", ".json", ".md",
        ]

    repo = Path(repo_path).expanduser().resolve()
    if not repo.exists():
        return {"files": {}, "errors": [f"Path does not exist: {repo_path}"], "truncated": False}
    if not repo.is_dir():
        return {"files": {}, "errors": [f"Path is not a directory: {repo_path}"], "truncated": False}

    is_git = (repo / ".git").exists()

    collected = {}
    errors = []
    truncated = False
    skipped_dirs = {
        ".git", "node_modules", "__pycache__", ".venv", "venv",
        "env", "dist", "build", ".next", ".nuxt", "target",
    }

    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in skipped_dirs and not d.startswith(".")]

        for fname in files:
            if len(collected) >= max_files:
                truncated = True
                break
            fpath = Path(root) / fname
            if fpath.suffix.lower() not in extensions:
                continue
            rel = str(fpath.relative_to(repo))
            try:
                content = fpath.read_text(encoding="utf-8", errors="replace")
                if len(content) > max_bytes_per_file:
                    content = content[:max_bytes_per_file] + f"\n... [truncated at {max_bytes_per_file} chars]"
                collected[rel] = content
            except Exception as e:
                errors.append(f"{rel}: {str(e)}")

        if truncated:
            break

    return {
        "files": collected,
        "errors": errors,
        "truncated": truncated,
        "is_git_repo": is_git,
        "total_files_found": len(collected),
    }


def extract_code_block(ai_response: str) -> str:
    """
    Pull the first fenced code block out of an AI response.
    Falls back to the whole response if no block found.
    """
    pattern = r"```(?:\w+)?\n(.*?)```"
    match = re.search(pattern, ai_response, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ai_response.strip()
