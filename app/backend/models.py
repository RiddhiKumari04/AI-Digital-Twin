"""
models.py — All Pydantic request/response models used across the backend.
"""

from typing import List
from pydantic import BaseModel


class UserRegister(BaseModel):
    name: str
    email: str
    password: str


class ResetPasswordRequest(BaseModel):
    email: str
    otp: str
    new_password: str


class DebugCodeRequest(BaseModel):
    user_id: str
    code: str
    language: str = "python"
    mode: str = "Find & Fix Bugs"   # Find & Fix Bugs | Code Review | Optimize Code | Explain This Code
    mood: str = "Natural"
    extra_context: str = ""
    run_code: bool = False           # execute original code before fixing?
    run_fixed: bool = False          # execute the fixed code after AI response?
    repo_path: str = ""              # optional: local repo path to include context


class NewsroomRequest(BaseModel):
    user_id: str
    mood: str = "Natural"                      # Professional | Natural | Sarcastic
    locations: List[str] = ["Delhi", "India"]  # user-defined locations
    extra_topics: List[str] = []               # any extra topics user wants
