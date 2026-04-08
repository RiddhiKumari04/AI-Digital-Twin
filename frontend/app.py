import streamlit as st
import requests
import json
import plotly.express as px
import plotly.graph_objects as go
import streamlit.components.v1 as components
from streamlit_mic_recorder import speech_to_text
import threading
import time
from streamlit.runtime.scriptrunner import add_script_run_ctx
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="AI Digital Twin Pro", layout="wide", initial_sidebar_state="expanded")

if "theme" not in st.session_state:
    st.session_state.theme = "dark"
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "name" not in st.session_state:
    st.session_state.name = ""
if "email" not in st.session_state:
    st.session_state.email = ""
if "auth_error" not in st.session_state:
    st.session_state.auth_error = ""
if "auth_success" not in st.session_state:
    st.session_state.auth_success = ""

# ── GUARANTEE ALL FP + AUTH STATE KEYS ALWAYS EXIST ─────────────────────────
for _k, _v in [
    ("fp_step", None), ("fp_email", ""), ("fp_otp_val", ""),
    ("otp_sent", False), ("auth_otp_email", ""),
    ("chat_history", []), ("chat_timestamps", []),
    ("show_chat_history", False), ("chip_inject", None),
    ("goto_shadow", False), ("current_session_id", None),
    ("profile_pic_b64", None), ("show_profile_edit", False),
    ("language", "English"), ("voice_enabled", True),
    ("last_answer", ""), ("suppress_next_prompt", False),
    ("voice_input_key", 0), ("webcam_mood_enabled", False),
    ("detected_emotion", "neutral"), ("style_mirror_history", []),
]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

_is_dark = st.session_state.theme == "dark"
_bg   = "#0f172a" if _is_dark else "#f0f4f8"
_bg2  = "#0d1829" if _is_dark else "#e2eaf3"
_text = "#e2e8f0" if _is_dark else "#1e293b"
_border = "rgba(56,189,248,0.15)" if _is_dark else "rgba(2,132,199,0.2)"

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&display=swap');
.stApp { background: #0f172a !important; color: #e2e8f0; font-family: 'DM Sans', sans-serif; }

.block-container { background: transparent !important; padding: 0 26px 60px 26px !important; max-width: 100% !important; }
header[data-testid="stHeader"] { background: transparent !important; }
footer { display: none !important; }
header[data-testid="stHeader"] { background: transparent !important; z-index: 100 !important; }
[data-testid="collapsedControl"] {
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    z-index: 99999 !important;
    background: #1e3a5f !important;
    border: 1.5px solid #38bdf8 !important;
    border-left: none !important;
    border-radius: 0 8px 8px 0 !important;
    box-shadow: 2px 0 10px rgba(56,189,248,0.25) !important;
}
[data-testid="collapsedControl"] svg {
    fill: #38bdf8 !important;
    color: #38bdf8 !important;
}

[data-testid="stSidebar"] {
    background: #0d1829 !important;
    border-right: 1px solid rgba(56,189,248,0.15) !important;
    display: block !important;
    visibility: visible !important;
    opacity: 1 !important;
    transform: none !important;
    left: 0 !important;
    position: relative !important;
    min-width: 260px !important;
    width: 260px !important;
    max-width: 320px !important;
}
[data-testid="stSidebar"] * {
    visibility: visible !important;
}
header[data-testid="stHeader"] button[kind="header"] { display: inline-flex !important; }
/* Allow sidebar toggle but hide other clutter */
[data-testid="stAppDeployButton"], [data-testid="stToolbar"], [data-testid="stDecoration"], 
.stAppToolbar, [data-testid="stToolbarActions"], [data-testid="stStatusWidget"], #MainMenu {
    display: none !important;
}

h1 { color: #38bdf8 !important; text-align: center; font-size: 3.2rem !important; font-weight: 900 !important; }
h2 { color: #e2e8f0 !important; font-size: 2rem !important; font-weight: 800 !important; }
h3 { color: #e2e8f0 !important; font-size: 1.6rem !important; font-weight: 700 !important; }
h1 a, h2 a, h3 a, h4 a, h5 a, h6 a { display: none !important; }
label, .stTextInput label, .stSelectbox label, .stRadio label, .stCheckbox label, .stTextArea label { font-size: 1.1rem !important; font-weight: 600 !important; color: #cbd5e1 !important; }
.stButton > button { width: 100%; border-radius: 10px; height: 3.2em; background: #0284c7; color: white; font-weight: 700 !important; font-size: 1.05rem !important; }
div[data-testid="stVerticalBlock"] > div:has(.export-report-anchor) + div [data-testid="stButton"] button {
    background: transparent !important; border: 1px solid rgba(255,255,255,0.1) !important; color: #94a3b8 !important; font-weight: 500 !important; height: 3.0em !important; transition: all 0.3s ease;
}
div[data-testid="stVerticalBlock"] > div:has(.export-report-anchor) + div [data-testid="stButton"] button:hover {
    background: #0284c7 !important; border-color: #0284c7 !important; color: white !important;
}
.stTextInput > div > div > input, .stTextArea textarea { font-size: 1.05rem !important; padding: 12px 16px !important; }
.profile-card { display: flex; flex-direction: column; align-items: center; padding: 18px 12px 14px 12px; background: linear-gradient(160deg, rgba(14,165,233,0.1), rgba(99,102,241,0.07)); border-bottom: 1px solid rgba(56,189,248,0.15); margin-bottom: 4px; }
.profile-avatar-wrap { position: relative; width: 72px; height: 72px; margin-bottom: 10px; }
.profile-avatar { width: 72px; height: 72px; border-radius: 50%; object-fit: cover; border: 2.5px solid #38bdf8; }
.profile-avatar-default { width: 72px; height: 72px; border-radius: 50%; background: linear-gradient(135deg, #1e3a5f, #0284c7); border: 2.5px solid #38bdf8; display: flex; align-items: center; justify-content: center; font-size: 2rem; }
.profile-name { color: #e2e8f0 !important; font-size: 1rem !important; font-weight: 700 !important; text-align: center; margin: 0 0 3px 0; }
.profile-badge { background: rgba(56,189,248,0.12); color: #38bdf8; font-size: 0.7rem !important; padding: 2px 10px; border-radius: 20px; border: 1px solid rgba(56,189,248,0.25); font-weight: 600; }
.memory-card { background: linear-gradient(135deg, rgba(14,165,233,0.07), rgba(56,189,248,0.04)); border: 1px solid rgba(56,189,248,0.2); border-left: 4px solid #38bdf8; border-radius: 12px; padding: 14px 18px; margin-bottom: 10px; }
.memory-card-text { color: #e2e8f0; font-size: 1rem !important; font-weight: 500; line-height: 1.5; margin-bottom: 8px; }
.memory-card-meta { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.memory-badge { display: inline-flex; align-items: center; gap: 4px; background: rgba(56,189,248,0.1); color: #7dd3fc; font-size: 0.75rem !important; font-weight: 600; padding: 3px 10px; border-radius: 20px; border: 1px solid rgba(56,189,248,0.2); }
.memory-badge-cat { display: inline-flex; align-items: center; gap: 4px; background: rgba(168,85,247,0.1); color: #c4b5fd; font-size: 0.75rem !important; font-weight: 600; padding: 3px 10px; border-radius: 20px; border: 1px solid rgba(168,85,247,0.2); }
.memory-count-badge { display: inline-block; background: rgba(56,189,248,0.15); color: #38bdf8; font-size: 0.82rem !important; font-weight: 700; padding: 4px 14px; border-radius: 20px; border: 1px solid rgba(56,189,248,0.3); margin-bottom: 14px; }
.conv-welcome { background: transparent; border: none; border-radius: 24px; padding: 45px 0 175px 0 !important; text-align: center; margin-bottom: 0 !important; }
.conv-welcome h3 { color: #e2e8f0 !important; font-size: 1.1rem !important; font-weight: 800 !important; margin: 0 0 4px 0 !important; }
.conv-welcome h3 span { color: #38bdf8; }
.conv-welcome p { color: #64748b !important; font-size: 0.82rem !important; margin: 0 !important; }
.conv-upload-slim { background: rgba(14,165,233,0.05); border: 1.5px dashed rgba(56,189,248,0.25); border-radius: 10px; padding: 6px 14px 10px 14px; margin-bottom: 6px; }
.conv-upload-slim-label { color: #38bdf8; font-size: 0.75rem !important; font-weight: 700; margin-bottom: 4px; display: block; }
.sess-panel { background: #0a1120; border: 1px solid rgba(56,189,248,0.18); border-radius: 14px; overflow: hidden; margin-bottom: 16px; }
.sess-header { background: linear-gradient(135deg, rgba(14,165,233,0.12), rgba(56,189,248,0.06)); border-bottom: 1px solid rgba(56,189,248,0.15); padding: 10px 16px; display: flex; align-items: center; justify-content: space-between; }
.sess-title { color: #38bdf8; font-size: 0.88rem !important; font-weight: 700; }
.ch-count { background: rgba(56,189,248,0.15); color: #7dd3fc; font-size: 0.75rem !important; font-weight: 700; padding: 3px 12px; border-radius: 20px; border: 1px solid rgba(56,189,248,0.25); }
.sess-item { padding: 10px 16px; border-bottom: 1px solid rgba(56,189,248,0.07); }
.sess-item-title { color: #e2e8f0; font-size: 0.85rem !important; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 260px; }
.sess-item-meta  { color: #475569; font-size: 0.72rem !important; margin-top: 2px; }
.sess-item-active { background: rgba(56,189,248,0.12) !important; border-left: 3px solid #38bdf8; }
.mirror-header { background: transparent; border: none; border-radius: 16px; padding: 18px 0; margin-bottom: 20px; }
.mirror-header h3 { color: #f472b6; margin: 0 0 6px 0; font-size: 1.1rem; }
.mirror-header p  { color: #94a3b8; margin: 0; font-size: 0.85rem; }
.score-badge { display: inline-block; background: linear-gradient(135deg, #ec4899, #a855f7); color: white; font-size: 2rem; font-weight: 900; padding: 12px 28px; border-radius: 50px; margin: 10px 0; }
.mirror-result { background: rgba(236,72,153,0.06); border: 1px solid rgba(236,72,153,0.3); border-radius: 14px; padding: 20px 24px; margin-top: 14px; border-left: 4px solid #ec4899; color: #fce7f3; }
.style-tip-card { background: rgba(168,85,247,0.07); border: 1px solid rgba(168,85,247,0.25); border-radius: 10px; padding: 10px 14px; margin-bottom: 8px; border-left: 4px solid #a855f7; font-size: 0.88em; color: #e9d5ff; }
.newsroom-header { background: transparent; border: none; border-radius: 16px; padding: 18px 0; margin-bottom: 20px; }
.newsroom-header h3 { color: #fbbf24; margin: 0 0 6px 0; font-size: 1.1rem; }
.newsroom-header p  { color: #94a3b8; margin: 0; font-size: 0.85rem; }
.briefing-card { background: rgba(251,191,36,0.05); border: 1px solid rgba(251,191,36,0.25); border-radius: 14px; padding: 22px 26px; margin-top: 14px; border-left: 4px solid #fbbf24; color: #fef3c7; line-height: 1.7; }
.news-meta-badge { display: inline-block; background: rgba(251,191,36,0.15); color: #fbbf24; font-size: 0.78em; font-weight: 600; padding: 3px 10px; border-radius: 20px; border: 1px solid rgba(251,191,36,0.3); margin: 2px 3px; }
.tech-tag { display: inline-block; background: rgba(14,165,233,0.12); color: #38bdf8; font-size: 0.78em; font-weight: 600; padding: 3px 10px; border-radius: 20px; border: 1px solid rgba(14,165,233,0.3); margin: 2px 3px; }
.shadow-header { background: transparent; border: none; border-radius: 14px; padding: 22px 0; margin-bottom: 20px; }
.shadow-header h3 { color: #38bdf8; margin: 0 0 6px 0; font-size: 1.1rem; }
.shadow-header p  { color: #94a3b8; margin: 0; font-size: 0.85rem; }
.code-style-card { background: rgba(99,102,241,0.07); border: 1px solid rgba(99,102,241,0.25); border-radius: 12px; padding: 14px 18px; margin-bottom: 10px; border-left: 4px solid #6366f1; font-size: 0.88em; color: #c4b5fd; }
.debug-result { background: rgba(16,185,129,0.07); border: 1px solid rgba(16,185,129,0.3); border-radius: 12px; padding: 16px 20px; margin-top: 12px; border-left: 4px solid #10b981; color: #d1fae5; }
.syntax-error-card { background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.35); border-radius: 10px; padding: 12px 16px; margin-bottom: 8px; border-left: 4px solid #ef4444; font-size: 0.87em; color: #fecaca; }
.syntax-warn-card { background: rgba(245,158,11,0.08); border: 1px solid rgba(245,158,11,0.35); border-radius: 10px; padding: 12px 16px; margin-bottom: 8px; border-left: 4px solid #f59e0b; font-size: 0.87em; color: #fde68a; }
.exec-card { background: rgba(14,165,233,0.07); border: 1px solid rgba(14,165,233,0.3); border-radius: 10px; padding: 14px 18px; margin-bottom: 10px; border-left: 4px solid #0ea5e9; font-size: 0.87em; color: #bae6fd; }
.diff-card { background: #0d1117; border: 1px solid rgba(99,102,241,0.3); border-radius: 10px; padding: 14px 18px; margin-bottom: 10px; font-family: monospace; font-size: 0.82em; overflow-x: auto; white-space: pre; color: #c9d1d9; }
.diff-add  { color: #3fb950; }
.diff-rem  { color: #f85149; }
.diff-meta { color: #8b949e; }
.repo-card { background: rgba(34,197,94,0.07); border: 1px solid rgba(34,197,94,0.3); border-radius: 10px; padding: 12px 16px; margin-bottom: 8px; border-left: 4px solid #22c55e; font-size: 0.87em; color: #bbf7d0; }
[data-testid="stHorizontalBlock"] [data-testid="stButton"] button { background: rgba(15,23,42,0.7) !important; border: 1px solid rgba(56,189,248,0.2) !important; color: #94a3b8 !important; border-radius: 30px !important; font-size: 0.8rem !important; font-weight: 500 !important; }
[data-testid="stHorizontalBlock"] [data-testid="stButton"] button:hover { border-color: #38bdf8 !important; color: #e2e8f0 !important; background: rgba(56,189,248,0.1) !important; }

/* ── RIGHT-SIDE FLOATING NAV MENU ── */
#twin-nav-btn {
    position: fixed; top: 12px; right: 16px; z-index: 99999;
    width: 44px; height: 44px;
    background: linear-gradient(135deg, #0284c7, #0ea5e9);
    border: none; border-radius: 12px; cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    box-shadow: 0 4px 16px rgba(2,132,199,0.5);
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}
#twin-nav-btn:hover { 
    transform: scale(1.1) rotate(5deg); 
    box-shadow: 0 6px 22px rgba(56,189,248,0.65);
    background: linear-gradient(135deg, #0ea5e9, #38bdf8);
}
#twin-nav-overlay {
    display: none; position: fixed; inset: 0;
    z-index: 99990; background: rgba(0,0,0,0.4); backdrop-filter: blur(3px);
    animation: fadeIn 0.2s ease-out;
}
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
#twin-nav-overlay.open { display: block; }

#twin-nav-panel {
    position: fixed; top: 66px; right: 16px; z-index: 99998;
    width: 240px; background: rgba(13, 24, 41, 0.95);
    border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 16px;
    padding: 10px 8px;
    box-shadow: 0 12px 48px rgba(0,0,0,0.6);
    backdrop-filter: blur(12px);
    opacity: 0; transform: translateY(-16px) scale(0.95);
    pointer-events: none;
    transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
}
#twin-nav-panel.open { opacity: 1; transform: translateY(0) scale(1); pointer-events: auto; }

#twin-nav-panel .nav-section-label {
    font-size: 11px; font-weight: 800; color: #475569;
    letter-spacing: 1.5px; text-transform: uppercase;
    padding: 6px 12px 8px 12px;
}
#twin-nav-panel button.twin-nav-item {
    display: flex; align-items: center; gap: 12px;
    width: 100%; background: transparent; border: none;
    border-radius: 10px; padding: 10px 14px;
    color: #94a3b8; font-size: 14px; font-weight: 600;
    font-family: 'DM Sans', sans-serif; cursor: pointer; text-align: left;
    transition: all 0.2s ease;
}
#twin-nav-panel button.twin-nav-item:hover { 
    background: rgba(56,189,248,0.12); 
    color: #f1f5f9;
    transform: translateX(6px);
}
#twin-nav-panel button.twin-nav-item.active { 
    background: linear-gradient(90deg, rgba(56,189,248,0.2), transparent);
    color: #38bdf8; 
    border-left: 3px solid #38bdf8;
    padding-left: 11px;
}
#twin-nav-panel button.twin-nav-item .nav-icon { 
    font-size: 18px; width: 22px; text-align: center; flex-shrink: 0; 
    transition: transform 0.2s ease;
}
#twin-nav-panel button.twin-nav-item:hover .nav-icon {
    transform: scale(1.2);
}

/* Hide only the clickable tab buttons (Conversation, Brain Explorer, etc.) 
   while keeping the screen content completely visible */
button[role="tab"] {
    opacity: 0 !important;
    height: 0 !important;
    width: 0 !important;
    padding: 0 !important;
    margin: 0 !important;
    overflow: hidden !important;
    position: absolute !important;
    pointer-events: auto !important;
}
[data-testid="stTabBar"] {
    height: 0 !important;
    overflow: hidden !important;
    margin: 0 !important;
    padding: 0 !important;
}
[data-baseweb="tab-list"], [data-baseweb="tab-border"] {
    border-color: transparent !important;
    background-color: transparent !important;
}
/* Pull-up for welcome chips into the welcome box (adjusted for user preference) */
div[data-testid="stVerticalBlock"] > div:has(.welcome-merge-anchor) + div {
    margin-top: -105px !important;
    padding-bottom: 80px !important;
    position: relative;
    z-index: 99 !important;
}
.switches-anchor + div,
.switches-anchor ~ div {
    /* Pull the composer controls above the fixed chat input */
    margin-top: -60px !important;
    position: relative;
    z-index: 99999 !important;
}
/* Match the same DOM pattern as the welcome box rule above */
div[data-testid="stVerticalBlock"] > div:has(.switches-anchor) + div {
    margin-top: -60px !important;
    position: relative;
    z-index: 99999 !important;
}
[data-testid="stChatInput"] {
    bottom: 10px !important;
}
/* Ensure the chips don't have extra background that breaks the look */
div[data-testid="stVerticalBlock"] > div:has(.welcome-merge-anchor) + div [data-testid="stHorizontalBlock"] {
    background: transparent !important;
}

/* Cinematic Chat Animations for the "Good Animation" requirement */
[data-testid="stChatMessage"] {
    animation: bubbleUp 0.6s cubic-bezier(0.165, 0.84, 0.44, 1.0) both;
}
@keyframes bubbleUp {
    from { opacity: 0; transform: translateY(20px) scale(0.98); }
    to { opacity: 1; transform: translateY(0) scale(1); }
}
/* Refined text appearance during streaming */
[data-testid="stChatMessage"] .stMarkdown {
    transition: all 0.2s ease;
}

/* ── ROBOT STATUS MESSAGES ── */
.thinking-status {
    color: #64748b;
    font-size: 0.88rem;
    font-weight: 500;
    margin-bottom: 8px;
    font-style: italic;
    animation: pulse 1.5s infinite;
}
@keyframes pulse {
    0% { opacity: 0.6; }
    50% { opacity: 1; }
    100% { opacity: 0.6; }
}

/* ── MOBILE RESPONSIVENESS (DYNAMIC SCALING) ── */
@media screen and (max-width: 768px) {
    .block-container { padding: 0 12px 40px 12px !important; }
    h1 { font-size: 2.2rem !important; }
    h2 { font-size: 1.6rem !important; }
    h3 { font-size: 1.3rem !important; }
    .conv-welcome { padding: 25px 0 100px 0 !important; }
    #twin-nav-floating-btn, #twin-nav-btn { width: 38px !important; height: 38px !important; top: 8px !important; right: 8px !important; }
    #twin-nav-panel { width: 220px !important; top: 54px !important; right: 8px !important; padding: 8px 6px !important; }
    .sess-item-title { max-width: 180px !important; }
}
</style>
""", unsafe_allow_html=True)


# ── AUTH HTML CARD ──────────────────────────────────────────────────────────
AUTH_CARD_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=0"/>
<style>
*{box-sizing:border-box;margin:0;padding:0}
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&display=swap');
html,body{width:100%;min-height:100vh;background:transparent;display:flex;align-items:center;justify-content:center;font-family:'DM Sans',-apple-system,BlinkMacSystemFont,sans-serif;padding:0}
.card{height:478px;margin-top:-32px;width:100%;max-width:440px;background:#141E2E;border:0.5px solid #1E2C40;border-radius:8px;padding:1rem 1.5rem 0.5rem;animation:fadeUp 220ms ease-out both}
@keyframes fadeUp{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
.logo{display:flex;align-items:center;justify-content:center;gap:8px;margin-bottom:0.75rem}
.logo-icon{width:28px;height:28px;background:#12213A;border:0.5px solid #253A5E;border-radius:6px;display:flex;align-items:center;justify-content:center}
.logo-name{font-size:14px;font-weight:500;color:#C8D5E4;letter-spacing:0.15px}
.tabs{display:flex;border-bottom:0.5px solid #1A2840;margin-bottom:1rem}
.tab{flex:1;text-align:center;font-size:13.5px;font-weight:400;color:#455972;padding-bottom:10px;border-bottom:2px solid transparent;margin-bottom:-1px;cursor:pointer;transition:all 160ms;background:none;border-left:none;border-right:none;border-top:none;font-family:inherit}
.tab.active{color:#E5E7EB;font-weight:600;border-bottom-color:#3B82F6}
.tab:hover:not(.active){color:#94A3B8}
.panel{display:none}.panel.active{display:block}
.field{margin-bottom:10px}
.lbl{display:block;font-size:10.5px;font-weight:600;color:#5A6F85;margin-bottom:4px;letter-spacing:0.5px;text-transform:uppercase}
input[type=text],input[type=email],input[type=password]{width:100%;background:#0D1625;border:0.5px solid #1A2C42;border-radius:6px;color:#E5E7EB;font-family:inherit;font-size:13px;padding:8px 12px;outline:none;transition:all 160ms;-webkit-appearance:none;padding-right:34px}
input::placeholder{color:#2E4159}
input:focus{border-color:#3B82F6;box-shadow:0 0 0 3px rgba(59,130,246,0.1)}
.pw-icon{position:absolute;right:10px;top:24px;cursor:pointer;color:#455972;transition:all 160ms;display:flex;align-items:center;height:30px}
.pw-icon:hover{color:#E5E7EB}
.forgot{text-align:right;margin-bottom:10px;margin-top:-2px}
.forgot a{font-size:11.5px;color:#3B82F6;text-decoration:none;cursor:pointer}
.forgot a:hover{color:#60A5FA}
.btn{width:100%;background:#1D4ED8;color:#F0F6FF;border:none;border-radius:6px;font-family:inherit;font-size:14px;font-weight:600;padding:10px 0;cursor:pointer;letter-spacing:0.15px;transition:all 160ms;margin-top:2px}
.btn:hover{background:#2563EB}
.btn:active{transform:scale(0.98)}
.divider{display:flex;align-items:center;gap:10px;margin:12px 0}
.divider-line{flex:1;height:0.5px;background:#192538}
.divider-text{font-size:11px;color:#2E4060}
.g-btn{width:100%;background:transparent;border:0.5px solid #1A2C42;border-radius:6px;color:#7A90A8;font-family:inherit;font-size:13.5px;padding:9px 0;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:8px;transition:all 160ms}
.g-btn:hover{border-color:#3B82F6;color:#E5E7EB;background:#0D1625}
.otp-link{font-size:11.5px;color:#4A8FE8;background:none;border:none;font-family:inherit;cursor:pointer;padding:0}
.otp-link:hover{color:#74B5FA}
.footer{font-size:11px;color:#2E4060;text-align:center;margin-top:10px;line-height:1.4}
.footer a{color:#3A5A80;text-decoration:none}
.footer a:hover{color:#4F9CF9}
.alert-err{background:rgba(239,68,68,0.07);border:0.5px solid rgba(239,68,68,0.22);border-radius:7px;color:#F87171;font-size:13px;padding:10px 14px;margin-bottom:14px;text-align:center;display:none}
.alert-ok{background:rgba(34,197,94,0.07);border:0.5px solid rgba(34,197,94,0.22);border-radius:7px;color:#4ADE80;font-size:13px;padding:10px 14px;margin-bottom:14px;text-align:center;display:none}
.hint{font-size:13px;color:#3A5472;margin-bottom:14px;line-height:1.5}
.hint b{color:#4A8FE8;font-weight:600}
.step-badge{display:inline-block;background:rgba(59,130,246,0.1);border:0.5px solid rgba(59,130,246,0.25);color:#4A8FE8;font-size:11.5px;font-weight:600;padding:4px 14px;border-radius:30px;margin-bottom:16px}
.method-row{display:flex;gap:8px;margin-bottom:14px}
.method-btn{flex:1;background:transparent;border:0.5px solid #1A2C42;border-radius:7px;color:#455972;font-family:inherit;font-size:14px;padding:9px 0;cursor:pointer;transition:all 160ms}
.method-btn.active{background:#12213A;border-color:#3B82F6;color:#7DD3FC;font-weight:600}
.method-btn:hover:not(.active){border-color:#253A58;color:#94A3B8}
@media screen and (max-width: 480px) {
    .card { padding: 1rem 1rem 0.5rem; height: auto; min-height: 480px; margin-top: 0; }
    .tabs { margin-bottom: 0.75rem; }
    input[type=text], input[type=email], input[type=password] { font-size: 14px; padding: 10px 12px; }
}
</style>
</head>
<body>
<div class="card">
  <div class="logo">
    <div class="logo-icon">
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <circle cx="8" cy="8" r="5" stroke="#4F9CF9" stroke-width="1.4"/>
        <circle cx="8" cy="8" r="2" fill="#4F9CF9"/>
      </svg>
    </div>
    <span class="logo-name">AI Digital Twin</span>
  </div>

  <div class="alert-err" id="alertErr"></div>
  <div class="alert-ok"  id="alertOk"></div>

  <div id="fpBlock" style="display:none">
    <div id="fp1">
      <span class="step-badge">Step 1 of 3 — Email address</span>
      <div class="field" style="position:relative"><label class="lbl">Registered email</label>
        <input type="email" id="fpEmail" placeholder="you@example.com"/></div>
      <button class="btn" onclick="submitFP1()">Send reset code</button>
      <div style="text-align:center;margin-top:12px">
        <button class="otp-link" onclick="showMain()">← Back to sign in</button></div>
    </div>
    <div id="fp2" style="display:none">
      <span class="step-badge">Step 2 of 3 — Verify code</span>
      <p class="hint">Code sent to <b id="fp2Email"></b>. Expires in 10 min.</p>
      <div class="field" style="position:relative"><label class="lbl">6-digit code</label>
        <input type="text" id="fpOtp" placeholder="000000" maxlength="6"/></div>
      <button class="btn" onclick="submitFP2()">Verify code</button>
      <div style="text-align:center;margin-top:12px">
        <button class="otp-link" onclick="showFP1()">Resend code</button></div>
    </div>
    <div id="fp3" style="display:none">
      <span class="step-badge">Step 3 of 3 — New password</span>
      <div class="field" style="position:relative"><label class="lbl">New password</label>
        <input type="password" id="fpNewPw" placeholder="Min. 6 characters"/>
        <span class="pw-icon" onclick="togglePassword('fpNewPw')">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
        </span>
      </div>
      <div class="field" style="position:relative"><label class="lbl">Confirm password</label>
        <input type="password" id="fpConfPw" placeholder="Re-enter password"/>
        <span class="pw-icon" onclick="togglePassword('fpConfPw')">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
        </span>
      </div>
      <button class="btn" onclick="submitFP3()">Reset password</button>
      <div style="text-align:center;margin-top:12px">
        <button class="otp-link" onclick="showFP2From3()">← Back</button></div>
    </div>
  </div>

  <div id="mainBlock">
    <div class="tabs">
      <button class="tab active" id="tabLogin">Sign in</button>
      <button class="tab"         id="tabRegister">Create account</button>
    </div>

    <div class="panel active" id="panelLogin">
      <div class="method-row">
        <button class="method-btn active" id="mPwd">Password</button>
        <button class="method-btn"         id="mOtp">Email code</button>
      </div>

      <div id="pwdFlow">
        <div class="field" style="position:relative"><label class="lbl">Email</label>
          <input type="email" id="loginEmail" placeholder="you@example.com"/></div>
        <div class="field" style="position:relative"><label class="lbl">Password</label>
          <input type="password" id="loginPwd" placeholder="••••••••"
            onkeydown="if(event.key==='Enter')submitLogin()"/>
          <span class="pw-icon" onclick="togglePassword('loginPwd')">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
          </span>
        </div>
        <div class="forgot"><a onclick="showFP1()">Forgot password?</a></div>
        <button class="btn" id="loginBtn">Continue</button>
        <div class="divider"><div class="divider-line"></div><span class="divider-text">or</span><div class="divider-line"></div></div>
        <button class="g-btn" id="googleBtn1">
          <svg width="15" height="15" viewBox="0 0 18 18" fill="none">
            <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844a4.14 4.14 0 01-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615z" fill="#4285F4"/>
            <path d="M9 18c2.43 0 4.467-.806 5.956-2.184l-2.908-2.259c-.806.54-1.837.859-3.048.859-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 009 18z" fill="#34A853"/>
            <path d="M3.964 10.705A5.41 5.41 0 013.682 9c0-.593.102-1.17.282-1.705V4.963H.957A8.996 8.996 0 000 9c0 1.452.348 2.827.957 4.037l3.007-2.332z" fill="#FBBC05"/>
            <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 00.957 4.963L3.964 7.295C4.672 5.168 6.656 3.58 9 3.58z" fill="#EA4335"/>
          </svg>
          Continue with Google
        </button>
      </div>

      <div id="otpFlow" style="display:none">
        <div id="otpStep1">
          <span class="step-badge">Step 1 of 2 — Email address</span>
          <div class="field" style="position:relative"><label class="lbl">Registered email</label>
            <input type="email" id="otpEmail" placeholder="you@example.com"/></div>
          <button class="btn" onclick="submitOTPSend()">Send one-time code</button>
        </div>
        <div id="otpStep2" style="display:none">
          <span class="step-badge">Step 2 of 2 — Enter code</span>
          <p class="hint">Code sent to <b id="otpEmailDisplay"></b>. Expires in 10 min.</p>
          <div class="field" style="position:relative"><label class="lbl">6-digit code</label>
            <input type="text" id="otpCode" placeholder="000000" maxlength="6"
              style="letter-spacing:6px;font-size:18px;text-align:center"
              onkeydown="if(event.key==='Enter')submitOTPVerify()"/></div>
          <button class="btn" onclick="submitOTPVerify()">Verify and sign in</button>
          <div style="text-align:center;margin-top:12px">
            <button class="otp-link" onclick="backOTPStep1()">Resend code</button></div>
        </div>
      </div>

      <p class="footer">By continuing you agree to our
        <a href="#">Terms of Service</a> and <a href="#">Privacy Policy</a></p>
    </div>

    <div class="panel" id="panelRegister">
      <div class="field" style="position:relative"><label class="lbl">Full name</label>
        <input type="text" id="regName" placeholder="Alex Sharma"/></div>
      <div class="field" style="position:relative"><label class="lbl">Email</label>
        <input type="email" id="regEmail" placeholder="you@example.com"/></div>
      <div class="field" style="position:relative"><label class="lbl">Password</label>
        <input type="password" id="regPwd" placeholder="Min. 6 characters"/>
        <span class="pw-icon" onclick="togglePassword('regPwd')">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
        </span>
      </div>
      <div class="field" style="position:relative"><label class="lbl">Confirm password</label>
        <input type="password" id="regConfPwd" placeholder="Re-enter password"
          onkeydown="if(event.key==='Enter')submitRegister()"/>
        <span class="pw-icon" onclick="togglePassword('regConfPwd')">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
        </span>
      </div>
      <button class="btn" id="registerBtn" style="margin-top:8px">Create account</button>
      <div class="divider"><div class="divider-line"></div><span class="divider-text">or</span><div class="divider-line"></div></div>
      <button class="g-btn" id="googleBtn2">
        <svg width="15" height="15" viewBox="0 0 18 18" fill="none">
          <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844a4.14 4.14 0 01-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615z" fill="#4285F4"/>
          <path d="M9 18c2.43 0 4.467-.806 5.956-2.184l-2.908-2.259c-.806.54-1.837.859-3.048.859-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 009 18z" fill="#34A853"/>
          <path d="M3.964 10.705A5.41 5.41 0 013.682 9c0-.593.102-1.17.282-1.705V4.963H.957A8.996 8.996 0 000 9c0 1.452.348 2.827.957 4.037l3.007-2.332z" fill="#FBBC05"/>
          <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 00.957 4.963L3.964 7.295C4.672 5.168 6.656 3.58 9 3.58z" fill="#EA4335"/>
        </svg>
        Continue with Google
      </button>
      <p class="footer" style="margin-top:14px">
        Already have an account? <a onclick="switchTab('login');return false;" href="#">Sign in</a><br>
        By continuing you agree to our <a href="#">Terms</a> and <a href="#">Privacy Policy</a></p>
    </div>
  </div>
</div>

<script>
var STATE = {};
var BACKEND_URL = "{BACKEND_URL}";


function togglePassword(id) {
  var x = document.getElementById(id);
  if (x.type === "password") x.type = "text";
  else x.type = "password";
}

function showAlert(type, msg) {
  var e = document.getElementById(type==='err'?'alertErr':'alertOk');
  var o = document.getElementById(type==='err'?'alertOk':'alertErr');
  e.textContent = msg; e.style.display = msg ? 'block' : 'none';
  o.style.display = 'none';
}

function switchTab(name) {
  ['Login','Register'].forEach(function(t) {
    var lower = t.toLowerCase();
    document.getElementById('tab'+t).classList.toggle('active', lower===name);
    document.getElementById('panel'+t).classList.toggle('active', lower===name);
  });
}

function switchMethod(m) {
  document.getElementById('mPwd').classList.toggle('active', m==='pwd');
  document.getElementById('mOtp').classList.toggle('active', m==='otp');
  document.getElementById('pwdFlow').style.display = m==='pwd' ? 'block' : 'none';
  document.getElementById('otpFlow').style.display = m==='otp' ? 'block' : 'none';
}

function showFP1() {
  document.getElementById('mainBlock').style.display = 'none';
  document.getElementById('fpBlock').style.display   = 'block';
  document.getElementById('fp1').style.display = 'block';
  document.getElementById('fp2').style.display = 'none';
  document.getElementById('fp3').style.display = 'none';
  showAlert('err',''); showAlert('ok','');
}
function showFP2From3() {
  document.getElementById('fp1').style.display = 'none';
  document.getElementById('fp2').style.display = 'block';
  document.getElementById('fp3').style.display = 'none';
}
function showMain() {
  document.getElementById('fpBlock').style.display   = 'none';
  document.getElementById('mainBlock').style.display = 'block';
  showAlert('err',''); showAlert('ok','');
}

function post(action, fields) {
  try {
    var params = new URLSearchParams();
    params.set('_act', action);
    for (var k in fields) { params.set('_'+k, fields[k]); }
    var url = '?' + params.toString();
    var p = window.parent.document;
    var s = p.createElement('script');
    s.textContent = 'location.assign(' + JSON.stringify(url) + ');';
    p.head.appendChild(s);
    p.head.removeChild(s);
  } catch(e) { console.error('post() error:', e); }
}

function startGoogle() {
  fetch(`${BACKEND_URL}/auth/google/start`)
    .then(r => r.json())
    .then(data => {
      if (data.url) {
        var p = window.parent.document;
        var s = p.createElement('script');
        s.textContent = 'location.assign(' + JSON.stringify(data.url) + ');';
        p.head.appendChild(s);
        p.head.removeChild(s);
      }
    })
    .catch(e => console.error('Google auth error:', e));
}

function submitLogin() {
  var e=document.getElementById('loginEmail').value.trim();
  var p=document.getElementById('loginPwd').value;
  if (!e||!p){showAlert('err','Please fill in all fields.');return;}
  post('login',{email:e,pwd:p});
}
function submitRegister() {
  var n=document.getElementById('regName').value.trim();
  var e=document.getElementById('regEmail').value.trim();
  var p=document.getElementById('regPwd').value;
  var c=document.getElementById('regConfPwd').value;
  if (!n||!e||!p){showAlert('err','All fields are required.');return;}
  if (p.length<6){showAlert('err','Password must be at least 6 characters.');return;}
  if (p!==c){showAlert('err','Passwords do not match.');return;}
  post('register',{name:n,email:e,pwd:p});
}
function submitOTPSend() {
  var e=document.getElementById('otpEmail').value.trim();
  if (!e){showAlert('err','Please enter your email.');return;}
  document.getElementById('otpEmailDisplay').textContent=e;
  post('otp_send',{email:e});
}
function backOTPStep1() {
  document.getElementById('otpStep1').style.display='block';
  document.getElementById('otpStep2').style.display='none';
}
function submitOTPVerify() {
  var c=document.getElementById('otpCode').value.trim();
  var e=document.getElementById('otpEmailDisplay').textContent;
  if (c.length!==6){showAlert('err','Code must be 6 digits.');return;}
  post('otp_verify',{email:e,code:c});
}
function submitFP1() {
  var e=document.getElementById('fpEmail').value.trim();
  if (!e){showAlert('err','Please enter your email.');return;}
  document.getElementById('fp2Email').textContent=e;
  post('fp_send',{email:e});
}
function submitFP2() {
  var o=document.getElementById('fpOtp').value.trim();
  var e=document.getElementById('fp2Email').textContent.trim();
  if (o.length!==6){showAlert('err','Code must be 6 digits.');return;}
  post('fp_verify',{otp:o,email:e});
}
function submitFP3() {
  var np=document.getElementById('fpNewPw').value;
  var cp=document.getElementById('fpConfPw').value;
  if (np.length<6){showAlert('err','Password must be at least 6 characters.');return;}
  if (np!==cp){showAlert('err','Passwords do not match.');return;}
  post('fp_reset',{newpwd:np});
}

// Add event listeners after DOM loads
document.addEventListener('DOMContentLoaded', function() {
  // Tab buttons
  document.getElementById('tabLogin').addEventListener('click', function() { switchTab('login'); });
  document.getElementById('tabRegister').addEventListener('click', function() { switchTab('register'); });
  
  // Method buttons
  document.getElementById('mPwd').addEventListener('click', function() { switchMethod('pwd'); });
  document.getElementById('mOtp').addEventListener('click', function() { switchMethod('otp'); });
  
  // Login/Register buttons
  document.getElementById('loginBtn').addEventListener('click', submitLogin);
  document.getElementById('registerBtn').addEventListener('click', submitRegister);
  
  // Google buttons
  document.getElementById('googleBtn1').addEventListener('click', startGoogle);
  document.getElementById('googleBtn2').addEventListener('click', startGoogle);
  
  // Keydown events
  document.getElementById('regConfPwd').addEventListener('keydown', function(e) {
    if (e.key === 'Enter') submitRegister();
  });
  document.getElementById('loginPwd').addEventListener('keydown', function(e) {
    if (e.key === 'Enter') submitLogin();
  });
  document.getElementById('otpCode').addEventListener('keydown', function(e) {
    if (e.key === 'Enter') submitOTPVerify();
  });
});

// Also try immediately in case DOMContentLoaded doesn't fire
try {
  document.getElementById('tabLogin').addEventListener('click', function() { switchTab('login'); });
  document.getElementById('tabRegister').addEventListener('click', function() { switchTab('register'); });
  document.getElementById('mPwd').addEventListener('click', function() { switchMethod('pwd'); });
  document.getElementById('mOtp').addEventListener('click', function() { switchMethod('otp'); });
  document.getElementById('loginBtn').addEventListener('click', submitLogin);
  document.getElementById('registerBtn').addEventListener('click', submitRegister);
  document.getElementById('googleBtn1').addEventListener('click', startGoogle);
  document.getElementById('googleBtn2').addEventListener('click', startGoogle);
} catch(e) {}
</script>
</body>
</html>"""


def _auth_card_with_state(err="", ok="", fp_step="", fp_email="", otp_sent=False, otp_email="", backend_url="http://localhost:8000"):
    state_js = (
        "STATE = {"
        f'"err":{repr(err)},"ok":{repr(ok)},'
        f'"fp_step":{repr(fp_step)},"fp_email":{repr(fp_email)},'
        f'"otp_sent":{"true" if otp_sent else "false"},"otp_email":{repr(otp_email)}'
        "};"
        "(function(){"
        "if(STATE.err){showAlert('err',STATE.err);}"
        "if(STATE.ok){showAlert('ok',STATE.ok);}"
        "if(STATE.fp_step==='enter_otp'){"
        "document.getElementById('mainBlock').style.display='none';"
        "document.getElementById('fpBlock').style.display='block';"
        "document.getElementById('fp1').style.display='none';"
        "document.getElementById('fp2').style.display='block';"
        "document.getElementById('fp2Email').textContent=STATE.fp_email;}"
        "if(STATE.fp_step==='new_password'){"
        "document.getElementById('mainBlock').style.display='none';"
        "document.getElementById('fpBlock').style.display='block';"
        "document.getElementById('fp1').style.display='none';"
        "document.getElementById('fp2').style.display='none';"
        "document.getElementById('fp3').style.display='block';}"
        "if(STATE.otp_sent&&STATE.otp_email){"
        "switchMethod('otp');"
        "document.getElementById('otpStep1').style.display='none';"
        "document.getElementById('otpStep2').style.display='block';"
        "document.getElementById('otpEmailDisplay').textContent=STATE.otp_email;}"
        "})();"
    )
    html = AUTH_CARD_HTML.replace("var STATE = {};", "var STATE = {};\n" + state_js)
    html = html.replace("{BACKEND_URL}", backend_url)
    return html


def speak_text(text):
    clean = (text.replace("\\", "\\\\").replace('"', '\\"')
             .replace("'", "\\'").replace("\n", "\\n").replace("\r", ""))
    components.html(f'<script>window.speechSynthesis.cancel();'
                    f'if("{clean}".length>0){{var m=new SpeechSynthesisUtterance("{clean}");window.speechSynthesis.speak(m);}}'
                    f'</script>', height=0)


def stop_speech():
    components.html("<script>window.speechSynthesis.cancel();</script>", height=0)


def _typewriter_stream(text: str):
    """Simulates a stream for non-streaming response sources."""
    import time
    for word in text.split(" "):
        yield word + " "
        time.sleep(0.015)


class ThinkingManager:
    """Manages background thinking status cycle while main logic processes."""
    def __init__(self, placeholder=None):
        self.p = placeholder if placeholder else st.empty()
        self.stop_ev = threading.Event()
        self.t = None
    
    def __enter__(self):
        self.start(); return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def start(self):
        def _run():
            msgs = [
                "🧬 Accessing Twin memories...",
                "🧠 Analyzing question intent...",
                "🔍 Scanning personal context...",
                "⚡ Synthesizing response...",
                "🤖 Embodying persona..."
            ]
            idx = 0
            while not self.stop_ev.is_set():
                self.p.markdown(f'<div class="thinking-status">{msgs[idx % len(msgs)]}</div>', unsafe_allow_html=True)
                idx += 1
                for _ in range(25): # Cycle every 2.5s with frequent stop-checks
                    if self.stop_ev.is_set(): break
                    time.sleep(0.1)
            self.p.empty()
        self.t = threading.Thread(target=_run, daemon=True)
        add_script_run_ctx(self.t)
        self.t.start()
        
    def stop(self):
        self.stop_ev.set()
        if self.t and self.t.is_alive(): self.t.join(timeout=0.1)
        self.p.empty()

def _show_thinking_status():
    """Fallback if someone still calls the old function."""
    with ThinkingManager(): time.sleep(2.5) # Minimum cycle for fixed calls


def _api_get(url, params=None, timeout=5, cache_key=None, cache_ttl=30):
    """Cached GET helper — avoids duplicate requests on rapid reruns."""
    import time as _time
    if cache_key:
        cached = st.session_state.get(f"_cache_{cache_key}")
        ts     = st.session_state.get(f"_cache_{cache_key}_ts", 0)
        if cached is not None and (_time.time() - ts) < cache_ttl:
            return cached
    try:
        r = requests.get(url, params=params, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        if cache_key:
            st.session_state[f"_cache_{cache_key}"] = data
            st.session_state[f"_cache_{cache_key}_ts"] = _time.time()
        return data
    except Exception:
        return None


def _invalidate_cache(*keys):
    """Clear one or more cache entries so the next call re-fetches."""
    for k in keys:
        st.session_state.pop(f"_cache_{k}", None)
        st.session_state.pop(f"_cache_{k}_ts", None)


def mood_detector_component():
    components.html("""<!DOCTYPE html><html><head>
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=0"/>
<style>body{margin:0;background:transparent;font-family:sans-serif}
#container{display:flex;flex-direction:column;align-items:center;gap:8px;padding:8px}
video{width:220px;height:160px;border-radius:12px;border:2px solid #38bdf8;object-fit:cover}
#status{font-size:12px;color:#94a3b8;text-align:center;min-height:18px}
#moodBadge{font-size:14px;font-weight:bold;color:#38bdf8;background:rgba(56,189,248,0.1);padding:4px 14px;border-radius:20px;border:1px solid #38bdf8}
</style></head><body>
<div id="container"><video id="video" autoplay muted playsinline></video>
<div id="moodBadge">😐 Neutral</div><div id="status">Loading face models...</div></div>
<script src="https://cdn.jsdelivr.net/npm/face-api.js@0.22.2/dist/face-api.min.js"></script>
<script>
const MODEL_URL='https://cdn.jsdelivr.net/npm/@vladmandic/face-api@1.7.12/model/';
const video=document.getElementById('video'),status=document.getElementById('status'),moodBadge=document.getElementById('moodBadge');
const EMOJI={happy:'😊',sad:'😢',angry:'😠',disgusted:'🤢',fearful:'😨',surprised:'😲',neutral:'😐'};
function pushEmotion(emotion){try{const inputs=window.parent.document.querySelectorAll('input[type="text"]');for(const inp of inputs){const label=inp.closest('[data-testid="stTextInput"]');if(label&&label.querySelector('label')&&label.querySelector('label').textContent.includes('__mood_hidden__')){const s=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;s.call(inp,emotion);inp.dispatchEvent(new Event('input',{bubbles:true}));break;}}}catch(e){}}
async function loadModels(){try{await faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL);await faceapi.nets.faceExpressionNet.loadFromUri(MODEL_URL);status.textContent='Models ready';await startCamera();}catch(e){status.textContent='Model load failed.';}}
async function startCamera(){try{const stream=await navigator.mediaDevices.getUserMedia({video:true,audio:false});video.srcObject=stream;video.addEventListener('loadedmetadata',()=>{status.textContent='Mood detection active';detectLoop();});}catch(e){status.textContent='Camera denied.';}}
async function detectLoop(){try{const result=await faceapi.detectSingleFace(video,new faceapi.TinyFaceDetectorOptions({inputSize:224})).withFaceExpressions();if(result){const top=Object.entries(result.expressions).sort((a,b)=>b[1]-a[1])[0];const emotion=top[0];moodBadge.textContent=(EMOJI[emotion]||'😐')+' '+emotion.charAt(0).toUpperCase()+emotion.slice(1);pushEmotion(emotion);}}catch(e){}setTimeout(detectLoop,1500);}
loadModels();
</script></body></html>""", height=230)


def render_diff_html(diff_text):
    lines = diff_text.splitlines()
    out = []
    for line in lines:
        if line.startswith("+") and not line.startswith("+++"):
            out.append(f'<span class="diff-add">{line}</span>')
        elif line.startswith("-") and not line.startswith("---"):
            out.append(f'<span class="diff-rem">{line}</span>')
        elif line.startswith("@@") or line.startswith("---") or line.startswith("+++"):
            out.append(f'<span class="diff-meta">{line}</span>')
        else:
            out.append(line)
    return "\n".join(out)


# ── RIGHT-SIDE FLOATING NAV MENU ─────────────────────────────────────────────
def _inject_nav_menu(active_tab="chat"):
    """
    Robust floating menu injection. 
    Injects the button and panel directly into the parent document to avoid iframe clipping/scoping issues.
    """
    nav_items = [
        ("chat",      "💬", "Conversation"),
        ("brain",     "🧠", "Think Space"),
        ("shadow",    "👾", "Code Assistant"),
        ("mirror",    "🪞", "My Style"),
        ("news",      "📰", "My Feed"),
        ("analytics", "📊", "Analytics"),
        ("goals",     "🎯", "Goals"),
        ("calendar",  "📅", "Calendar"),
        ("feedback",  "📝", "Feedback"),
    ]
    
    # Generate the menu items HTML
    btns_html = "".join(
        f'<button class="twin-nav-item{" active" if key == active_tab else ""}" onclick="window.parent.twinNavTo(\'{key}\')">'
        f'<span class="twin-nav-icon">{icon}</span>{label}</button>'
        for key, icon, label in nav_items
    )

    injection_js = f"""
    (function() {{
        const p = window.parent.document;
        const w = window.parent;
        
        // 1. Inject Styles with Cinematic Animations
        if (!p.getElementById('twin-nav-styles')) {{
            const style = p.createElement('style');
            style.id = 'twin-nav-styles';
            style.textContent = `
                #twin-nav-floating-btn {{
                    position: fixed; top: 12px; right: 16px; z-index: 1000001;
                    width: 44px; height: 44px;
                    background: linear-gradient(135deg, #0284c7, #0ea5e9);
                    border: none; border-radius: 12px; cursor: pointer;
                    display: flex; align-items: center; justify-content: center;
                    box-shadow: 0 4px 16px rgba(2,132,199,0.5);
                    transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
                }}
                #twin-nav-floating-btn:hover {{ 
                    transform: scale(1.1) rotate(5deg); 
                    box-shadow: 0 6px 22px rgba(56,189,248,0.65);
                    background: linear-gradient(135deg, #0ea5e9, #38bdf8);
                }}
                #twin-nav-overlay {{
                    display: none; position: fixed; inset: 0;
                    z-index: 1000000; background: rgba(0,0,0,0.4); backdrop-filter: blur(4px);
                    transition: opacity 0.4s ease;
                }}
                #twin-nav-overlay.open {{ display: block; }}
                
                #twin-nav-panel {{
                    position: fixed; top: 66px; right: 16px; z-index: 1000001;
                    width: 240px; background: rgba(13, 24, 41, 0.98);
                    border: 1px solid rgba(56, 189, 248, 0.4); border-radius: 20px;
                    padding: 12px 8px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.7);
                    backdrop-filter: blur(16px);
                    
                    /* Initial state: diagonally hidden at top-right */
                    opacity: 0; 
                    transform: translate(40px, -40px) scale(0.8) rotate(8deg);
                    pointer-events: none;
                    transition: all 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275);
                    transform-origin: top right;
                }}
                
                /* Opening state: glides in diagonally from top */
                #twin-nav-panel.open {{ 
                    opacity: 1; 
                    transform: translate(0, 0) scale(1) rotate(0deg); 
                    pointer-events: auto; 
                }}
                
                /* Closing state: glides out diagonally towards bottom */
                #twin-nav-panel.exit {{ 
                    opacity: 0; 
                    transform: translate(-30px, 40px) scale(0.8) rotate(-8deg); 
                    pointer-events: none;
                }}

                .twin-nav-label {{
                    font-size: 11px; font-weight: 800; color: #475569;
                    letter-spacing: 2px; text-transform: uppercase;
                    padding: 6px 14px 10px 14px; opacity: 0.6;
                }}
                .twin-nav-item {{
                    display: flex; align-items: center; gap: 14px;
                    width: 100%; background: transparent; border: none;
                    border-radius: 12px; padding: 11px 16px;
                    color: #94a3b8; font-size: 14px; font-weight: 600;
                    font-family: 'DM Sans', sans-serif; cursor: pointer; text-align: left;
                    transition: all 0.25s ease;
                    opacity: 0; transform: translateX(10px); /* staggers in */
                }}
                /* Stagger animation when parent is open */
                /* Stagger animation when parent is open */
                #twin-nav-panel.open .twin-nav-item {{ 
                    opacity: 1; transform: translateX(0); 
                }}
                
                /* Sequence styles for smooth entrance */
                #twin-nav-panel.open .twin-nav-item:nth-child(1) {{ transition-delay: 0.05s; }}
                #twin-nav-panel.open .twin-nav-item:nth-child(2) {{ transition-delay: 0.10s; }}
                #twin-nav-panel.open .twin-nav-item:nth-child(3) {{ transition-delay: 0.15s; }}
                #twin-nav-panel.open .twin-nav-item:nth-child(4) {{ transition-delay: 0.20s; }}
                #twin-nav-panel.open .twin-nav-item:nth-child(5) {{ transition-delay: 0.25s; }}
                #twin-nav-panel.open .twin-nav-item:nth-child(6) {{ transition-delay: 0.30s; }}
                #twin-nav-panel.open .twin-nav-item:nth-child(7) {{ transition-delay: 0.35s; }}
                #twin-nav-panel.open .twin-nav-item:nth-child(8) {{ transition-delay: 0.40s; }}
                #twin-nav-panel.open .twin-nav-item:nth-child(9) {{ transition-delay: 0.45s; }}

                .twin-nav-item:hover {{ 
                    background: rgba(56, 189, 248, 0.15); color: #f1f5f9;
                    transform: translateX(8px) !important;
                    transition-delay: 0s !important;
                    opacity: 1 !important;
                }}
                .twin-nav-item.active {{ 
                    background: linear-gradient(90deg, rgba(56, 189, 248, 0.25), transparent);
                    color: #38bdf8; border-left: 4px solid #38bdf8; padding-left: 12px;
                }}
                .twin-nav-icon {{ font-size: 18px; width: 22px; text-align: center; transition: transform 0.2s ease; }}
                .twin-nav-item:hover .twin-nav-icon {{ transform: scale(1.2) rotate(10deg); }}
            `;
            p.head.appendChild(style);
        }}

        // 2. Inject Elements
        if (!p.getElementById('twin-nav-floating-btn')) {{
            const btn = p.createElement('button');
            btn.id = 'twin-nav-floating-btn';
            btn.title = 'Navigation Menu';
            btn.innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.8" stroke-linecap="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>`;
            btn.onclick = () => {{
                const pnl = p.getElementById('twin-nav-panel');
                const ovr = p.getElementById('twin-nav-overlay');
                if(pnl.classList.contains('open')) {{
                    pnl.classList.remove('open');
                    pnl.classList.add('exit');
                    ovr.classList.remove('open');
                    setTimeout(() => pnl.classList.remove('exit'), 500);
                }} else {{
                    pnl.classList.remove('exit');
                    pnl.classList.add('open');
                    ovr.classList.add('open');
                }}
            }};
            p.body.appendChild(btn);

            const overlay = p.createElement('div');
            overlay.id = 'twin-nav-overlay';
            overlay.onclick = () => {{
                const pnl = p.getElementById('twin-nav-panel');
                pnl.classList.remove('open');
                pnl.classList.add('exit');
                overlay.classList.remove('open');
                setTimeout(() => pnl.classList.remove('exit'), 500);
            }};
            p.body.appendChild(overlay);

            const panel = p.createElement('div');
            panel.id = 'twin-nav-panel';
            panel.innerHTML = '<div class="twin-nav-label">Go to</div><div id="twin-nav-content"></div>';
            p.body.appendChild(panel);
        }}

        // 3. Define Global Nav function on parent window
        // It clicks the hidden native Streamlit tabs to trigger instant, state-preserved navigation.
        w.twinNavTo = function(key) {{
            const pnl = p.getElementById('twin-nav-panel');
            const ovr = p.getElementById('twin-nav-overlay');
            if(pnl) {{
                pnl.classList.remove('open');
                pnl.classList.add('exit');
                setTimeout(() => pnl.classList.remove('exit'), 500);
            }}
            if(ovr) ovr.classList.remove('open');
            
            const options = ["chat", "brain", "shadow", "mirror", "news", "analytics", "goals", "calendar", "feedback"];
            const idx = options.indexOf(key);
            if (idx === -1) return;

            // Target ONLY the individual tabs in the hidden native tab bar
            const tabs = p.querySelectorAll('[data-testid="stTabBar"] [role="tab"]');
            if (tabs && tabs[idx]) {{
                tabs[idx].click();
            }} else {{
                // Fallback for different DOM structure
                const fbTabs = p.querySelectorAll('[data-testid="stTabs"] [role="tab"]');
                if (fbTabs && fbTabs[idx]) fbTabs[idx].click();
            }}
        }};

        // 4. Update panel items
        const inner = p.getElementById('twin-nav-content');
        if(inner) {{
            inner.innerHTML = {json.dumps(btns_html)};
        }}
    }})();
    """
    components.html("<script>" + injection_js + "</script>", height=0)


def _inject_floating_feedback():
    injection_js = """
    (function() {
        const p = window.parent.document;
        if (!p.getElementById('ff-btn')) {
            const style = p.createElement('style');
            style.id = 'ff-styles';
            style.textContent = `
                @keyframes ffFadeIn { from { opacity: 0; } to { opacity: 1; } }
                .ff-modal-overlay { position: fixed; inset: 0; background: rgba(2, 6, 23, 0.85); backdrop-filter: blur(12px); z-index: 9998; display: none; animation: ffFadeIn 0.4s ease; }
                .ff-modal-overlay.ff-show { display: block; }
                .ff-btn { position: fixed; bottom: 24px; right: 24px; background: linear-gradient(135deg, #0284c7, #0ea5e9); color: white; border: none; border-radius: 12px; padding: 12px 20px; font-size: 15px; font-family: 'DM Sans', sans-serif; font-weight: 600; cursor: pointer; box-shadow: 0 4px 16px rgba(2,132,199,0.4); transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1); z-index: 9997; display: flex; align-items: center; gap: 8px; }
                .ff-btn:hover { transform: scale(1.05) translateY(-3px); box-shadow: 0 6px 22px rgba(56,189,248,0.5); background: linear-gradient(135deg, #0ea5e9, #38bdf8); }
                .ff-popup { position: fixed; top: 50%; left: 50%; width: 70%; max-width: 950px; background: rgba(13, 24, 41, 0.98); border-radius: 28px; box-shadow: 0 50px 120px rgba(0,0,0,0.7); opacity: 0; visibility: hidden; transform: translate(-50%, -45%) scale(0.96); transition: all 0.5s cubic-bezier(0.19, 1, 0.22, 1); z-index: 9999; font-family: 'DM Sans', sans-serif; border: 1px solid rgba(56, 189, 248, 0.25); overflow: hidden; }
                .ff-popup.ff-open { opacity: 1; visibility: visible; transform: translate(-50%, -50%) scale(1); }
                .ff-header { background: rgba(56, 189, 248, 0.04); padding: 30px 40px; border-bottom: 1px solid rgba(56, 189, 248, 0.15); display: flex; justify-content: space-between; align-items: center; }
                .ff-header h4 { margin: 0; color: #f8fafc; font-size: 24px; font-weight: 800; letter-spacing: -0.5px; }
                .ff-close { background: rgba(56, 189, 248, 0.08); border: none; width: 36px; height: 36px; border-radius: 10px; font-size: 22px; color: #94a3b8; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.3s; }
                .ff-close:hover { background: rgba(239, 68, 68, 0.2); color: #f87171; transform: rotate(90deg); }
                #ff-form { padding: 40px; margin: 0; display: grid; gap: 25px; }
                .ff-group { text-align: left; }
                .ff-group label { display: block; font-size: 12px; color: #38bdf8; margin-bottom: 10px; font-weight: 800; text-transform: uppercase; letter-spacing: 1.5px; }
                .ff-required { color: #f87171; }
                .ff-group input, .ff-group textarea { width: 100%; padding: 16px 20px; border: 1px solid rgba(56, 189, 248, 0.15); border-radius: 14px; font-size: 15px; color: #f1f5f9; font-family: inherit; transition: all 0.3s ease; box-sizing: border-box; background: rgba(15, 23, 42, 0.8); }
                .ff-group input:focus, .ff-group textarea:focus { outline: none; border-color: #38bdf8; background: rgba(15, 23, 42, 1); box-shadow: 0 0 0 4px rgba(56, 189, 248, 0.1); }
                .ff-group input::placeholder, .ff-group textarea::placeholder { color: #475569; }
                .ff-error { color: #f87171; font-size: 13px; margin-top: 8px; display: none; font-weight: 600; }
                .ff-group.has-error .ff-error { display: block; }
                .ff-group.has-error input { border-color: #f87171; }
                .ff-submit { width: 100%; background: linear-gradient(135deg, #0284c7, #0ea5e9); color: white; border: none; border-radius: 14px; padding: 18px; font-size: 16px; font-weight: 800; cursor: pointer; transition: all 0.3s ease; box-shadow: 0 10px 25px rgba(2, 132, 199, 0.3); letter-spacing: 0.5px; }
                .ff-submit:hover:not(:disabled) { transform: translateY(-3px); box-shadow: 0 15px 30px rgba(56, 189, 248, 0.4); background: linear-gradient(135deg, #0ea5e9, #38bdf8); }
                .ff-submit:disabled { background: #334155; opacity: 0.5; color: #64748b; cursor: not-allowed; box-shadow: none; transform: none; }
                .ff-toast { position: fixed; top: 30px; left: 50%; transform: translateX(-50%) translateY(-20px); background: #10b981; color: white; padding: 16px 32px; border-radius: 50px; box-shadow: 0 10px 40px rgba(0,0,0,0.4); font-family: 'DM Sans', sans-serif; font-size: 15px; font-weight: 700; z-index: 10001; opacity: 0; visibility: hidden; transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275); display: flex; align-items: center; gap: 12px; }
                .ff-toast.ff-show { opacity: 1; visibility: visible; transform: translateX(-50%) translateY(0); }
                @media (max-width: 1000px) { .ff-popup { width: 90%; } }
            `;
            p.head.appendChild(style);

            const overlay = p.createElement('div');
            overlay.id = 'ff-overlay';
            overlay.className = 'ff-modal-overlay';
            p.body.appendChild(overlay);

            const btn = p.createElement('button');
            btn.id = 'ff-btn';
            btn.className = 'ff-btn';
            btn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg> <span>Report Your Problem</span>';
            p.body.appendChild(btn);

            const popup = p.createElement('div');
            popup.id = 'ff-popup';
            popup.className = 'ff-popup';
            popup.innerHTML = `
                <div class="ff-header">
                    <h4>Report Your Problem</h4>
                    <button id="ff-close" class="ff-close"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg></button>
                </div>
                <form id="ff-form">
                    <div class="ff-group">
                        <label>SUBJECT <span class="ff-required">*</span></label>
                        <input type="text" id="ff-subject" placeholder="What exactly is the issue?">
                        <span id="ff-error" class="ff-error">Subject is mandatory.</span>
                    </div>
                    <div class="ff-group">
                        <label>DESCRIPTION</label>
                        <textarea id="ff-description" rows="5" placeholder="Deep dive into the problem... (optional)"></textarea>
                    </div>
                    <button type="submit" id="ff-submit" class="ff-submit" disabled>Report Your Problem</button>
                    <div id="ff-success-msg" style="display:none; color:#10b981; font-weight:700; font-size:1rem; text-align:center; padding:18px; border:1px solid rgba(16,185,129,0.3); background:rgba(16,185,129,0.08); border-radius:15px; margin-top:25px; animation: ffFadeIn 0.4s ease;">
                        We have received your report and our team will surely look into this matter. Thank you for your patience! ✅
                    </div>
                </form>
            `;
            p.body.appendChild(popup);

            const toast = p.createElement('div');
            toast.id = 'ff-toast';
            toast.className = 'ff-toast';
            toast.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg> <span>Problem Reported Successfully! ✅</span>';
            p.body.appendChild(toast);

            const openForm = () => { 
                overlay.classList.add('ff-show'); 
                popup.classList.add('ff-open'); 
                // Hide Photo/Voice toggles using robust text matching
                [...p.querySelectorAll('label')].forEach(label => {
                    if (label.innerText.includes('Photo') || label.innerText.includes('Voice')) {
                        const toggleWrap = label.closest('[data-testid="stToggle"]') || label.closest('.stCheckbox') || label.parentElement;
                        if(toggleWrap) {
                           toggleWrap.setAttribute('data-ff-hidden', 'true');
                           toggleWrap.style.display = 'none';
                        }
                    }
                });
            };
            const closeForm = () => { 
                overlay.classList.remove('ff-show'); 
                popup.classList.remove('ff-open'); 
                // Restore toggles
                p.querySelectorAll('[data-ff-hidden="true"]').forEach(el => {
                    el.style.display = '';
                    el.removeAttribute('data-ff-hidden');
                });
            };

            btn.addEventListener('click', openForm);
            p.getElementById('ff-close').addEventListener('click', closeForm);
            overlay.addEventListener('click', closeForm);
            
            const subjectInput = p.getElementById('ff-subject');
            const submitBtn = p.getElementById('ff-submit');

            subjectInput.addEventListener('input', () => {
                const val = subjectInput.value.trim();
                submitBtn.disabled = (val === '');
                if (val !== '') {
                    subjectInput.closest('.ff-group').classList.remove('has-error');
                }
            });

            const form = p.getElementById('ff-form');
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                const subject = subjectInput.value.trim();
                const description = p.getElementById('ff-description').value.trim();
                if (!subject) {
                    subjectInput.closest('.ff-group').classList.add('has-error');
                    return;
                }
                const submitBtn = p.getElementById('ff-submit');

                const originalText = submitBtn.innerText;
                submitBtn.disabled = true;
                submitBtn.innerText = 'Sending...';

                try {
                    await fetch("https://formsubmit.co/ajax/twinx.techai@gmail.com", {
                        method: "POST",
                        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                        body: JSON.stringify({
                            _subject: `New Problem Reported: ${subject}`,
                            Subject: subject, Description: description || 'No detail.'
                        })
                    });
                    
                    // Show inline success message
                    const inlineMsg = p.getElementById('ff-success-msg');
                    if(inlineMsg) {
                        form.style.opacity = '0.4'; // Dim form
                        form.style.pointerEvents = 'none';
                        submitBtn.style.display = 'none';
                        inlineMsg.style.display = 'block';
                    }
                    
                    setTimeout(() => {
                        form.reset();
                        form.style.opacity = '1';
                        form.style.pointerEvents = 'all';
                        submitBtn.style.display = 'block';
                        if(inlineMsg) inlineMsg.style.display = 'none';
                        closeForm();
                    }, 5000);
                } catch(err) {
                    alert("Submission failed.");
                } finally {
                    submitBtn.disabled = false;
                    submitBtn.innerText = 'Report Your Problem';
                }
            });
        }
    })();
    """
    components.html("<script>" + injection_js + "</script>", height=0)


EMOTION_TONE = {

    "happy":     ("upbeat and enthusiastic",        "😊 You look really happy today!"),
    "sad":       ("warm, gentle and comforting",     "😢 You seem a bit sad. I'm here for you."),
    "angry":     ("calm, patient and de-escalating","😠 You seem a bit tense. Take a breath."),
    "disgusted": ("light, positive and distracting","🤢 Something bugging you? Let me help."),
    "fearful":   ("reassuring and confident",       "😨 Don't stress — I'll help."),
    "surprised": ("energetic and curious",          "😲 You look surprised! Let's dig in."),
    "neutral":   ("natural and conversational",     ""),
}

twin_mood = "Natural"

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
if st.session_state.logged_in:
    import datetime as _dt
    import uuid as _uuid

    if not st.session_state.get("current_session_id"):
        st.session_state.current_session_id = str(_uuid.uuid4())

    def _save_session():
        hist = st.session_state.chat_history
        ts   = st.session_state.chat_timestamps
        if not hist: return
        first_user = next((m["content"] for m in hist if m["role"] == "user"), "New Chat")
        title = first_user[:48] + ("…" if len(first_user) > 48 else "")
        try:
            requests.post(f"{BACKEND_URL}/chat/save", json={
                "user_id": st.session_state.email,
                "session_id": st.session_state.current_session_id,
                "messages": hist, "timestamps": ts, "title": title,
            }, timeout=3)
        except Exception:
            pass

    # ── Lazy photo load after login ──────────────────────────────────────────
    if st.session_state.get("load_photo_on_next_render"):
        st.session_state.load_photo_on_next_render = False
        try:
            _pic_lazy = requests.get(f"{BACKEND_URL}/profile/get_photo",
                                     params={"user_id": st.session_state.email}, timeout=2).json()
            st.session_state.profile_pic_b64 = _pic_lazy.get("pic_b64")
        except Exception:
            pass





# ── MAIN CONTENT ──────────────────────────────────────────────────────────────
if not st.session_state.logged_in:

    st.markdown("""<style>.block-container { padding: 0 26px 60px 26px !important; }</style>""", unsafe_allow_html=True)

    _qp      = st.query_params
    _act     = _qp.get("_act", "")
    _email   = _qp.get("_email", "")
    _name    = _qp.get("_name", "")
    _pwd     = _qp.get("_pwd", "")
    _otp     = _qp.get("_otp", "")
    _code    = _qp.get("_code", "")
    _newpwd  = _qp.get("_newpwd", "")
    _go      = bool(_act)

    if _go and _act:
        act = _act.strip()
        st.query_params.clear()

        if act == "login":
            try:
                r = requests.get(f"{BACKEND_URL}/login",
                                  params={"email": _email.strip(), "password": _pwd}, timeout=60)
                if r.status_code == 200:
                    data = r.json()
                    import uuid as _u
                    _new_sid = str(_u.uuid4())
                    for _k in list(st.session_state.keys()):
                        del st.session_state[_k]
                    st.session_state.update({
                        "logged_in": True, "email": _email.strip(), "name": data["name"],
                        "chat_history": [], "chat_timestamps": [],
                        "current_session_id": _new_sid,
                        "show_chat_history": False, "voice_enabled": True,
                        "last_answer": "", "suppress_next_prompt": False,
                        "voice_input_key": 0, "webcam_mood_enabled": False,
                        "detected_emotion": "neutral", "style_mirror_history": [],
                        "profile_pic_b64": None, "show_profile_edit": False,
                        "theme": "dark", "language": "English",
                        "active_page": "conversation", "chip_inject": None,
                        "goto_shadow": False, "load_photo_on_next_render": True,
                        "fp_step": None, "fp_email": "", "fp_otp_val": "",
                        "otp_sent": False, "auth_otp_email": "",
                        "auth_error": "", "auth_success": "",
                        "show_onboarding": data.get("is_first_login", False),
                    })
                    st.rerun()
                elif r.status_code == 401:
                    st.session_state.auth_error = "Incorrect email or password."
                else:
                    st.session_state.auth_error = f"Login error ({r.status_code})."
            except Exception as ex:
                st.session_state.auth_error = f"Connection error: {ex}"

        elif act == "register":
            try:
                r = requests.post(f"{BACKEND_URL}/register",
                                   json={"name": _name.strip(), "email": _email.strip(), "password": _pwd}, timeout=60)
                if r.status_code == 200:
                    st.session_state.auth_success = "Account created! Switch to Sign In."
                    st.session_state.auth_error   = ""
                elif r.status_code == 409:
                    st.session_state.auth_error   = "Email already registered."
                    st.session_state.auth_success = ""
                else:
                    st.session_state.auth_error = f"Registration failed ({r.status_code})."
            except Exception as ex:
                st.session_state.auth_error = f"Connection error: {ex}"

        elif act == "otp_send":
            try:
                r = requests.post(f"{BACKEND_URL}/login_otp/send",
                                   params={"email": _email.strip()}, timeout=15)
                if r.status_code == 200:
                    st.session_state.otp_sent        = True
                    st.session_state.auth_otp_email = _email.strip()
                    st.session_state.auth_success   = f"Code sent to {_email.strip()}"
                    st.session_state.auth_error      = ""
                else:
                    st.session_state.auth_error = r.json().get("detail", "Failed to send OTP.")
            except Exception as ex:
                st.session_state.auth_error = f"Connection error: {ex}"

        elif act == "otp_verify":
            try:
                r = requests.post(f"{BACKEND_URL}/login_otp/verify",
                                   params={"email": _email.strip(), "otp": _code.strip()}, timeout=60)
                if r.status_code == 200:
                    data = r.json()
                    import uuid as _u2
                    _new_sid2 = str(_u2.uuid4())
                    for _k in list(st.session_state.keys()):
                        del st.session_state[_k]
                    st.session_state.update({
                        "logged_in": True, "email": _email.strip(), "name": data["name"],
                        "chat_history": [], "chat_timestamps": [],
                        "current_session_id": _new_sid2,
                        "show_chat_history": False, "voice_enabled": True,
                        "last_answer": "", "suppress_next_prompt": False,
                        "voice_input_key": 0, "webcam_mood_enabled": False,
                        "detected_emotion": "neutral", "style_mirror_history": [],
                        "profile_pic_b64": None, "show_profile_edit": False,
                        "theme": "dark", "language": "English",
                        "active_page": "conversation", "chip_inject": None,
                        "goto_shadow": False, "load_photo_on_next_render": True,
                        "fp_step": None, "fp_email": "", "fp_otp_val": "",
                        "otp_sent": False, "auth_otp_email": "",
                        "auth_error": "", "auth_success": "",
                        "show_onboarding": data.get("is_first_login", False),
                    })
                    st.rerun()
                else:
                    st.session_state.auth_error = r.json().get("detail", "Invalid code.")
            except Exception as ex:
                st.session_state.auth_error = f"Connection error: {ex}"

        elif act == "fp_send":
            try:
                _fp_em = _email.strip()
                r = requests.post(f"{BACKEND_URL}/forgot_password/send_otp",
                                   params={"email": _fp_em}, timeout=15)
                if r.status_code == 200:
                    st.session_state["fp_email"]     = _fp_em
                    st.session_state["fp_step"]      = "enter_otp"
                    st.session_state["auth_success"] = f"Reset code sent to {_fp_em}"
                    st.session_state["auth_error"]   = ""
                else:
                    st.session_state["auth_error"] = r.json().get("detail", "Failed.")
            except Exception as ex:
                st.session_state["auth_error"] = f"Connection error: {ex}"

        elif act == "fp_verify":
            try:
                # ── FIX: always get email from query param (JS now sends it) ──
                _fp_email_use = _email.strip() or st.session_state.get("fp_email", "").strip()
                r = requests.post(f"{BACKEND_URL}/forgot_password/verify_otp",
                                   params={"email": _fp_email_use, "otp": _otp.strip()}, timeout=60)
                if r.status_code == 200:
                    st.session_state["fp_email"]   = _fp_email_use
                    st.session_state["fp_otp_val"] = _otp.strip()
                    st.session_state["fp_step"]    = "new_password"
                    st.session_state["auth_error"] = ""
                else:
                    st.session_state["auth_error"] = r.json().get("detail", "Invalid code.")
            except Exception as ex:
                st.session_state["auth_error"] = f"Connection error: {ex}"

        elif act == "fp_reset":
            try:
                _fp_email_rst = st.session_state.get("fp_email", "").strip() or _email.strip()
                _fp_otp_rst   = st.session_state.get("fp_otp_val", "").strip() or _otp.strip()
                r = requests.post(f"{BACKEND_URL}/forgot_password/reset",
                                   json={"email": _fp_email_rst,
                                         "otp":   _fp_otp_rst,
                                         "new_password": _newpwd}, timeout=60)
                if r.status_code == 200:
                    st.session_state["fp_step"]      = None
                    st.session_state["fp_email"]     = ""
                    st.session_state["fp_otp_val"]   = ""
                    st.session_state["auth_success"]  = "Password reset! You can now sign in."
                    st.session_state["auth_error"]    = ""
                else:
                    st.session_state["auth_error"] = r.json().get("detail", "Reset failed.")
            except Exception as ex:
                st.session_state["auth_error"] = f"Connection error: {ex}"

        elif act == "google_login":
            if _email and _name:
                import uuid as _u3
                _new_sid3 = str(_u3.uuid4())
                for _k in list(st.session_state.keys()):
                    del st.session_state[_k]
                st.session_state.update({
                    "logged_in": True, "email": _email, "name": _name,
                    "chat_history": [], "chat_timestamps": [],
                    "current_session_id": _new_sid3,
                    "show_chat_history": False, "voice_enabled": True,
                    "last_answer": "", "suppress_next_prompt": False,
                    "voice_input_key": 0, "webcam_mood_enabled": False,
                    "detected_emotion": "neutral", "style_mirror_history": [],
                    "profile_pic_b64": None, "show_profile_edit": False,
                    "theme": "dark", "language": "English",
                    "active_page": "conversation", "chip_inject": None,
                    "goto_shadow": False, "load_photo_on_next_render": True,
                    "fp_step": None, "fp_email": "", "fp_otp_val": "",
                    "otp_sent": False, "auth_otp_email": "",
                    "auth_error": "", "auth_success": "",
                    "show_onboarding": False,
                })
                st.rerun()

        st.rerun()

    # ── RENDER AUTH INTERFACE ─────────────────────────────────────────────────
    st.markdown("""
    <style>
    @keyframes pulse { 0%{opacity:0.6;transform:scale(0.9)}50%{opacity:1;transform:scale(1)}100%{opacity:0.6;transform:scale(0.9)} }
    .landing-left{padding:0.5rem 0;animation:fadeIn 0.8s ease-out;}
    .logo-section{display:flex;align-items:center;gap:8px;margin-bottom:0.5rem}
    .logo-text{font-size:2.1rem;font-weight:700;color:#e2e8f0}
    .live-badge{display:inline-flex;align-items:center;gap:6px;background:rgba(56,189,248,0.1);color:#38bdf8;padding:4px 10px;border-radius:30px;font-size:0.70rem;font-weight:600;border:1px solid rgba(56,189,248,0.2);margin-bottom:0.75rem}
    .headline{font-size:3rem;font-weight:900;line-height:1.05;margin-bottom:0.5rem;color:#f8fafc;letter-spacing:-1px}
    .headline span{color:#38bdf8}
    .subheadline{font-size:0.95rem;color:#94a3b8;line-height:1.4;margin-bottom:1rem;max-width:440px}
    .feature-card{background:rgba(15,23,42,0.3);border:1px solid rgba(56,189,248,0.08);border-radius:10px;padding:0.6rem 0.85rem;margin-bottom:0.5rem;display:flex;align-items:center;gap:1rem;transition:all 0.3s ease}
    .feature-card:hover{transform:translateX(8px);background:rgba(15,23,42,0.6);border-color:rgba(56,189,248,0.3)}
    .feature-icon{width:36px;height:36px;background:rgba(56,189,248,0.1);border-radius:8px;display:flex;align-items:center;justify-content:center;color:#38bdf8;flex-shrink:0}
    .feature-title{font-size:0.95rem;font-weight:700;color:#f1f5f9;margin-bottom:0.1rem}
    .feature-desc{color:#64748b;font-size:0.8rem}
    @keyframes fadeIn{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:translateY(0)}}
    </style>""", unsafe_allow_html=True)

    col1, col2 = st.columns([1.4, 1])
    with col1:
        st.markdown("""<div class="landing-left">
<div class="logo-section">
<div style="background:#1e293b;padding:8px;border-radius:10px;border:1px solid #334155;">
<svg width="20" height="20" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="5" stroke="#38bdf8" stroke-width="1.8"/><circle cx="8" cy="8" r="2" fill="#38bdf8"/></svg>
</div><span class="logo-text">AI Digital Twin</span></div>
<div class="live-badge"><span style="display:inline-block;width:6px;height:6px;background:#38bdf8;border-radius:50%;box-shadow:0 0 8px #38bdf8;animation:pulse 2s infinite;"></span>Live & Learning</div>
<div class="headline">Your AI self,<br><span>always on.</span></div>
<div class="subheadline">A digital twin that knows your style, your code, your people — and grows smarter every day.</div>
<div class="feature-card"><div class="feature-icon"><svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" stroke-linecap="round" stroke-linejoin="round"></path></svg></div><div><div class="feature-title">Persistent Memory</div><div class="feature-desc">Remembers your preferences across all sessions</div></div></div>
<div class="feature-card"><div class="feature-icon"><svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" stroke-linecap="round" stroke-linejoin="round"></path></svg></div><div><div class="feature-title">Shadow Developer</div><div class="feature-desc">Debugs code in your exact style and voice</div></div></div>
<div class="feature-card"><div class="feature-icon"><svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" stroke-linecap="round" stroke-linejoin="round"></path></svg></div><div><div class="feature-title">Mood-Aware Responses</div><div class="feature-desc">Adapts its tone to how you feel in real time</div></div></div>
</div>""", unsafe_allow_html=True)

    with col2:
        card_html = _auth_card_with_state(
            err      = st.session_state.get("auth_error", ""),
            ok       = st.session_state.get("auth_success", ""),
            fp_step  = st.session_state.get("fp_step") or "",
            fp_email = st.session_state.get("fp_email", ""),
            otp_sent = st.session_state.get("otp_sent", False),
            otp_email= st.session_state.get("auth_otp_email", ""),
            backend_url=BACKEND_URL,
        )
        st.session_state.auth_error   = ""
        st.session_state.auth_success = ""
        components.html(card_html, height=520, scrolling=False)


# ── LOGGED-IN APP ─────────────────────────────────────────────────────────────
else:
    if st.session_state.get("show_onboarding", False):
        st.markdown("""
        <style>
        html, body, [data-testid="stAppViewContainer"] { overflow: hidden !important; }
        .block-container { padding-top: 5vh !important; max-width: 100% !important; }
        header[data-testid="stHeader"] { display: none !important; }

        .onb-title { text-align: center; color: #f8fafc; font-size: 2.2rem; font-weight: 800; margin-bottom: 8px; letter-spacing:-0.5px;}
        .onb-sub   { text-align: center; color: #94a3b8; font-size: 1.05rem; margin-bottom: 24px; }
        
        div[data-testid="stRadio"] { width: 100% !important; display: block !important; }
        div[data-testid="stRadio"] > div { gap: 10px; width: 100% !important; display: flex; flex-direction: column; }
        div[data-testid="stRadio"] label[data-baseweb="radio"] {
            background: transparent; border: 1px solid transparent; 
            padding: 14px 20px; border-radius: 12px; transition: all 0.2s ease; cursor: pointer;
            width: 100% !important; display: flex; align-items: center; box-sizing: border-box;
        }
        /* Hide the radio circle */
        div[data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child { display: none !important; }
        
        div[data-testid="stRadio"] label[data-baseweb="radio"]:hover {
            background: rgba(56,189,248,0.05); border-color: rgba(56,189,248,0.4);
        }
        div[data-testid="stRadio"] label[data-baseweb="radio"][aria-checked="true"],
        div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) {
            background: rgba(56,189,248,0.1) !important; border-color: #38bdf8 !important;
        }
        div[data-testid="stRadio"] div[data-testid="stMarkdownContainer"] {
            width: 100% !important; display: block !important;
        }
        div[data-testid="stRadio"] div[data-testid="stMarkdownContainer"] p {
            font-size: 1.1rem; font-weight: 500; color: #e2e8f0; margin: 0; width: 100%;
        }
        
        div[data-testid="stButton"] { display: flex; justify-content: center; width: 100%; box-sizing: border-box;}
        div[data-testid="stButton"] button[kind="primary"] {
            background: #0ea5e9 !important; color: white !important; font-weight: 800 !important;
            border-radius: 30px !important; margin-top: 16px; height: 3.2em !important; font-size: 1.15rem !important; width: 100%; border: none !important;
            transition: all 0.2s ease;
        }
        div[data-testid="stButton"] button[kind="primary"]:hover {
            background: #38bdf8 !important; opacity: 1.0; box-shadow: 0 4px 14px rgba(2,132,199,0.4) !important;
        }
        div[data-testid="stButton"] button[kind="secondary"] {
            background: transparent !important; color: #94a3b8 !important; border: 1px solid rgba(255,255,255,0.1) !important;
            font-weight: 600 !important; height: 3.2em !important; margin-top: 8px; width: 100%; border-radius: 30px !important;
            transition: all 0.2s ease;
        }
        div[data-testid="stButton"] button[kind="secondary"]:hover {
            color: #f8fafc !important; background: rgba(255,255,255,0.05) !important; border-color: rgba(255,255,255,0.3) !important;
        }
        div[data-testid="stButton"] button[kind="secondary"]:active {
            color: #f8fafc !important; background: transparent !important; box-shadow: none !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        if "onboarding_step" not in st.session_state:
            st.session_state.onboarding_step = 1

        _, c2, _ = st.columns([1, 1.4, 1])
        with c2:
            if st.session_state.onboarding_step == 1:
                st.markdown('<div class="onb-title">What brings you to TwinX?</div>', unsafe_allow_html=True)
                st.markdown('<div class="onb-sub">We\'ll use this information to suggest ideas you might find useful.</div>', unsafe_allow_html=True)
                
                choice = st.radio("Options", [
                    "🎓  School", 
                    "💼  Work", 
                    "✨  Personal tasks", 
                    "🎭  Fun and entertainment", 
                    "📁  Other"
                ], label_visibility="collapsed", key="onb_choice_radio", index=None)
                
                if st.button("Next", type="primary", use_container_width=True, disabled=(choice is None), key="next_1"):
                    st.session_state.onboarding_step = 2
                    st.rerun()
                    
                if st.button("Skip", type="secondary", use_container_width=True, key="skip_1"):
                    st.session_state.onboarding_step = 2
                    st.rerun()
                    
            elif st.session_state.onboarding_step == 2:
                st.markdown('<div class="onb-title" style="margin-bottom: 32px;">How do you plan to use TwinX?</div>', unsafe_allow_html=True)
                
                choice2 = st.radio("Options2", [
                    "👤  For myself", 
                    "👥  With a team"
                ], label_visibility="collapsed", key="onb_choice_radio2", index=None)
                
                if choice2 == "👥  With a team":
                    if "team_members_count" not in st.session_state:
                        st.session_state.team_members_count = 1
                        
                    st.markdown('<div style="margin-top: 16px;"></div>', unsafe_allow_html=True)
                    for i in range(st.session_state.team_members_count):
                        st.text_input(f"Team Member {i+1}", placeholder=f"Name of team member {i+1}" if i > 0 else "Name of team member", label_visibility="collapsed", key=f"team_member_input_{i}")
                        
                    if st.button("➕ Add a new team member", type="secondary", use_container_width=True, key="add_team_btn"):
                        st.session_state.team_members_count += 1
                        st.rerun()
                    st.markdown('<div style="margin-bottom: 8px;"></div>', unsafe_allow_html=True)
                else:
                    st.session_state.team_members_count = 1
                
                if st.button("Continue", type="primary", use_container_width=True, disabled=(choice2 is None), key="continue_2"):
                    st.session_state.onboarding_step = 3
                    st.rerun()
                    
                if st.button("Skip", type="secondary", use_container_width=True, key="skip_2"):
                    st.session_state.onboarding_step = 3
                    st.rerun()
                    
            elif st.session_state.onboarding_step == 3:
                st.markdown('<div style="height: 15vh;"></div>', unsafe_allow_html=True)
                st.markdown('<div class="onb-title">Ask anything</div>', unsafe_allow_html=True)
                st.markdown('<div class="onb-sub">From quick questions to big ideas, TwinX is here to help.</div>', unsafe_allow_html=True)
                
                st.markdown('<div style="margin-bottom: 32px;"></div>', unsafe_allow_html=True)
                
                if st.button("Next", type="primary", use_container_width=True, key="next_3"):
                    st.session_state.onboarding_step = 4
                    st.rerun()
                    
            elif st.session_state.onboarding_step == 4:
                st.markdown('<div style="height: 10vh;"></div>', unsafe_allow_html=True)
                st.markdown('''
                <div style="text-align: center; margin-bottom: 24px;">
                    <div style="display: inline-flex; justify-content: center; align-items: center; width: 44px; height: 44px; background-color: #f8fafc; border-radius: 50%;">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#0f172a" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round">
                            <polyline points="20 6 9 17 4 12"></polyline>
                        </svg>
                    </div>
                </div>
                ''', unsafe_allow_html=True)
                st.markdown('<div class="onb-title" style="margin-bottom: 4px; font-weight: 500;">You\'re all set</div>', unsafe_allow_html=True)
                st.markdown('<div style="text-align: center; font-size: 1.65rem; font-weight: bold; color: #f8fafc; margin-bottom: 24px;">Ready to explore? 😊</div>', unsafe_allow_html=True)
                
                st.markdown('''
                <div style="text-align: center; color: #cbd5e1; font-size: 1.05rem; line-height: 1.6; margin-bottom: 32px; font-weight: 500;">
                    TwinX can make mistakes. Chats may be reviewed and used for training. <br><a href="#" style="color: #cbd5e1; text-decoration: underline;">Learn about your choices</a>
                </div>
                ''', unsafe_allow_html=True)
                
                if st.button("Continue", type="primary", use_container_width=True, key="continue_4"):
                    st.session_state.show_onboarding = False
                    st.rerun()
                    
                st.markdown('''
                <div style="text-align: center; color: #94a3b8; font-size: 0.85rem; line-height: 1.5; margin-top: 16px;">
                    By continuing, you agree to our <a href="#" style="color: #94a3b8; text-decoration: underline;">Terms</a> and have read our <a href="#" style="color: #94a3b8; text-decoration: underline;">Privacy Policy</a>. See <a href="#" style="color: #94a3b8; text-decoration: underline;">Cookie Preferences</a>.
                </div>
                ''', unsafe_allow_html=True)
                
        st.stop()

    # Handle goto_shadow flag
    _goto_shadow = st.session_state.get("goto_shadow", False)

    # Init active tab state if not present

    if "active_tab" not in st.session_state:
        st.session_state["active_tab"] = "chat"

    _active = st.session_state["active_tab"]
    _inject_nav_menu(active_tab=_active)  # ── floating right-side nav menu
    _inject_floating_feedback()

    # ── SIDEBAR RENDER (Prioritized) ──────────────────────────────────────────
    with st.sidebar:
        import base64 as _b64
        full_name  = st.session_state.name or ""
        first_name = full_name.split()[0] if full_name else "User"
        last_name  = " ".join(full_name.split()[1:]) if len(full_name.split()) > 1 else ""
        pic_b64    = st.session_state.get("profile_pic_b64")
        if pic_b64:
            avatar_html = f'<img class="profile-avatar" src="data:image/png;base64,{pic_b64}" />'
        else:
            initials = (first_name[0] + (last_name[0] if last_name else "")).upper()
            avatar_html = f'<div class="profile-avatar-default">{initials}</div>'

        st.markdown(f"""
        <div class="profile-card">
          <div class="profile-avatar-wrap">{avatar_html}</div>
          <div class="profile-name">{first_name}<br><span style="color:#94a3b8;font-weight:500">{last_name}</span></div>
          <span class="profile-badge">✨ Digital Twin</span>
        </div>""", unsafe_allow_html=True)

        show_edit = st.session_state.get("show_profile_edit", False)
        if st.button("📷 Change Photo" if not show_edit else "✖ Cancel", key="toggle_profile_edit", use_container_width=True):
            st.session_state.show_profile_edit = not show_edit
            st.rerun()
        if st.session_state.get("show_profile_edit", False):
            uploaded_pic = st.file_uploader("Upload photo", type=["jpg","jpeg","png"], key="profile_uploader", label_visibility="collapsed")
            if uploaded_pic:
                raw = uploaded_pic.read()
                pic_b64_new = _b64.b64encode(raw).decode()
                st.session_state.profile_pic_b64 = pic_b64_new
                st.session_state.show_profile_edit = False
                try:
                    requests.post(f"{BACKEND_URL}/profile/save_photo",
                                  json={"user_id": st.session_state.email, "pic_b64": pic_b64_new}, timeout=3)
                except Exception:
                    pass
                st.rerun()
            if st.session_state.get("profile_pic_b64"):
                if st.button("🗑️ Remove Photo", key="remove_photo", use_container_width=True):
                    st.session_state.profile_pic_b64 = None
                    st.session_state.show_profile_edit = False
                    try:
                        requests.post(f"{BACKEND_URL}/profile/save_photo",
                                      json={"user_id": st.session_state.email, "pic_b64": None}, timeout=3)
                    except Exception:
                        pass
                    st.rerun()

        st.markdown("---")
        
        # ── PROFESSIONAL SIDEBAR CHAT CONTROLS ──────────────────────────────────────
        st.markdown("""
        <style>
        .sb-chat-controls [data-testid="stButton"] button {
            background: linear-gradient(135deg, rgba(14,165,233,0.1), rgba(56,189,248,0.05)) !important;
            border: 1px solid rgba(56,189,248,0.18) !important;
            color: #e2e8f0 !important;
            border-radius: 12px !important;
            height: 3rem !important;
            font-size: 0.92rem !important;
            display: flex !important;
            align-items: center !important;
            justify-content: flex-start !important;
            padding-left: 1.2rem !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            text-shadow: 0 1px 2px rgba(0,0,0,0.2) !important;
            text-align: left !important;
        }
        .sb-chat-controls [data-testid="stButton"] button:hover {
            background: rgba(56,189,248,0.15) !important;
            border-color: #38bdf8 !important;
            color: #38bdf8 !important;
            transform: translateX(6px) !important;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3) !important;
        }
        </style>
        """, unsafe_allow_html=True)

        st.markdown('<div class="sb-chat-controls">', unsafe_allow_html=True)
        # 1. New Chat (Primary Action)
        if st.button("✏️ New Conversation", key="new_chat_btn_side", use_container_width=True):
            _save_session()
            st.session_state.chat_history       = []
            st.session_state.chat_timestamps    = []
            st.session_state.current_session_id = str(_uuid.uuid4())
            st.session_state.show_chat_history  = False
            st.rerun()

        # 2. History Toggle
        hist_label = "🕘 Hide History" if st.session_state.get("show_chat_history") else "🕘 Chat History"
        if st.button(hist_label, key="toggle_chat_history_side", use_container_width=True):
            st.session_state.show_chat_history = not st.session_state.get("show_chat_history", False)
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("🎭 Mood Detector")
        webcam_on = st.toggle("Enable Webcam Mood Detection", value=st.session_state.get("webcam_mood_enabled", False))
        st.session_state.webcam_mood_enabled = webcam_on
        if webcam_on:
            st.caption("🔒 Fully private — runs in your browser only.")
            detected_raw = st.text_input("__mood_hidden__", value=st.session_state.get("detected_emotion", "neutral"), label_visibility="hidden", key="mood_input_field")
            if detected_raw and detected_raw.strip() in EMOTION_TONE:
                st.session_state.detected_emotion = detected_raw.strip()
            mood_detector_component()
            emotion = st.session_state.get("detected_emotion", "neutral")
            tone_label, _ = EMOTION_TONE.get(emotion, EMOTION_TONE["neutral"])
            if emotion and emotion != "neutral":
                st.info(f"Detected: **{emotion.capitalize()}** \nTwin tone: *{tone_label}*")
            else:
                st.caption("Waiting for face detection...")
        else:
            st.session_state.detected_emotion = "neutral"
            st.caption("Turn on to let your twin react to your mood.")


        st.markdown("---")
        st.session_state.voice_enabled = st.checkbox("🔊 Voice Response", value=st.session_state.get("voice_enabled", True))
        if st.session_state.voice_enabled and st.button("🔊 Test Voice"):
            stop_speech(); speak_text("This is a test voice from your AI digital twin.")
        if st.session_state.voice_enabled and st.button("⏹ Stop Voice"):
            stop_speech()

        st.markdown("---")
        twin_mood = st.select_slider("Personality", options=["Professional", "Natural", "Sarcastic"])
        lang_opts = ["English", "Hindi", "Spanish", "French", "German", "Japanese", "Arabic", "Portuguese"]
        cur_lang  = st.session_state.get("language", "English")
        new_lang  = st.selectbox("🌍 Response Language", lang_opts, index=lang_opts.index(cur_lang) if cur_lang in lang_opts else 0, key="lang_select")
        if new_lang != cur_lang:
            st.session_state.language = new_lang

        # ── BACKEND HEALTH STATUS ────────────────────────────────────────────
        st.markdown("---")
        st.markdown("**🛰 Backend Status**")
        try:
            _h = requests.get(f"{BACKEND_URL}/health/ping", timeout=2)
            _h_full = requests.get(f"{BACKEND_URL}/health", timeout=6).json()
            _overall = _h_full.get("status", "unknown")
            _summary = _h_full.get("summary", {})
            _services = _h_full.get("services", {})
            _color = {"healthy": "#22c55e", "degraded": "#f59e0b", "unhealthy": "#ef4444"}.get(_overall, "#94a3b8")
            _icon  = {"healthy": "🟢", "degraded": "🟡", "unhealthy": "🔴"}.get(_overall, "⚪")
            st.markdown(
                f'<div style="background:rgba(0,0,0,0.2);border:1px solid {_color}40;border-left:3px solid {_color};'
                f'border-radius:10px;padding:10px 14px;margin-bottom:8px;">'
                f'<div style="color:{_color};font-size:0.85rem;font-weight:700">{_icon} {_overall.capitalize()}</div>'
                f'<div style="color:#64748b;font-size:0.72rem;margin-top:3px">'
                f'DB: {_summary.get("critical_services","?")} &nbsp;|&nbsp; AI: {_summary.get("ai_providers","?")}'
                f'</div></div>',
                unsafe_allow_html=True
            )
            # Per-service dots
            _svc_icons = {
                "mongodb": "🗄 MongoDB", "chromadb": "💾 ChromaDB",
                "gemini": "💎 Gemini", "openrouter": "🔀 OpenRouter",
                "groq": "⚡ Groq", "huggingface": "🤗 HuggingFace",
                "together_ai": "🤝 Together AI", "email": "✉️ Email",
                "google_oauth": "🔑 Google OAuth",
            }
            lines_html = []
            for _svc, _label in _svc_icons.items():
                _st = _services.get(_svc, {}).get("status", "unknown")
                _dot = "🟢" if _st == "ok" else ("🟡" if _st in ("warning", "configured") else "🔴")
                lines_html.append(f'<span style="font-size:0.72rem;color:#94a3b8;">{_dot} {_label}</span>')
            st.markdown(
                '<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:6px;">' +
                "".join(f'<span>{l}</span>' for l in lines_html) + '</div>',
                unsafe_allow_html=True
            )
        except Exception:
            st.markdown(
                '<div style="background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.3);'
                'border-left:3px solid #ef4444;border-radius:10px;padding:8px 12px;'
                'color:#f87171;font-size:0.8rem">🔴 Backend unreachable</div>',
                unsafe_allow_html=True
            )

        st.markdown(
            f'<a href="{BACKEND_URL}/api-docs" target="_blank" style="display:block;text-align:center;'
            f'color:#38bdf8;font-size:0.78rem;margin-top:4px;text-decoration:none;">📖 API Documentation ↗</a>',
            unsafe_allow_html=True
        )

        st.markdown("---")
        if st.button("Logout"):

            try:
                hist = st.session_state.chat_history
                ts   = st.session_state.chat_timestamps
                if hist and st.session_state.get("current_session_id"):
                    first_user = next((m["content"] for m in hist if m["role"] == "user"), "Chat")
                    requests.post(f"{BACKEND_URL}/chat/save", json={
                        "user_id": st.session_state.email,
                        "session_id": st.session_state.current_session_id,
                        "messages": hist, "timestamps": ts,
                        "title": first_user[:48] + ("…" if len(first_user) > 48 else ""),
                    }, timeout=3)
            except Exception:
                pass
            st.session_state.logged_in = False
            st.rerun()

    import datetime as _dt_greet
    _hour = _dt_greet.datetime.now().hour
    if _hour < 5:
        _msg, _emo = "Hi", "👋"
    elif _hour < 12:
        _msg, _emo = "Good Morning", "🌅"
    elif _hour < 17:
        _msg, _emo = "Good Afternoon", "☀️"
    else:
        _msg, _emo = "Good Evening", "🌙"
    st.title(f"{_msg}, {st.session_state.name.split()[0]} {_emo}")




    # Use native st.tabs for state-preserving navigation, hidden by CSS
    tab_chat, tab_brain, tab_shadow, tab_mirror, tab_news, tab_analytics, tab_goals, tab_calendar, tab_feedback = st.tabs([
        "CONVERSATION", "THINK_SPACE", "CODE_ASSISTANT",
        "MY_STYLE", "MY_FEED", "ANALYTICS", "GOALS", "CALENDAR", "FEEDBACK"
    ])
    
    if _goto_shadow:
        st.info("👾 Head to the **CODE ASSISTANT** section to review your code!")

    # ── CONVERSATION ─────────────────────────────────────────────────────────
    with tab_chat:

        if st.session_state.get("show_chat_history", False):
            try:
                sess_res = requests.get(f"{BACKEND_URL}/chat/sessions",
                                        params={"user_id": st.session_state.email}, timeout=4).json()
                sessions = sess_res.get("sessions", [])
            except Exception:
                sessions = []
            st.markdown(f"""<div class="sess-panel"><div class="sess-header">
                <span class="sess-title">💬 Chat History</span>
                <span class="ch-count">{len(sessions)} conversation{"s" if len(sessions)!=1 else ""}</span>
            </div></div>""", unsafe_allow_html=True)
            if not sessions and not st.session_state.chat_history:
                st.markdown('<div style="color:#475569;font-size:0.88rem;padding:12px 4px">🌙 No saved conversations yet.</div>', unsafe_allow_html=True)
            else:
                for sess in sessions:
                    sid     = sess.get("session_id","")
                    s_title = sess.get("title","Chat")
                    s_date  = sess.get("updated_at","")[:10]
                    is_cur  = (sid == st.session_state.current_session_id)
                    c1, c2  = st.columns([0.82, 0.18])
                    with c1:
                        style = "sess-item sess-item-active" if is_cur else "sess-item"
                        st.markdown(f'<div class="{style}"><div class="sess-item-title">{"🟢 " if is_cur else "💬 "}{s_title}</div><div class="sess-item-meta">📅 {s_date}</div></div>', unsafe_allow_html=True)
                    with c2:
                        if st.button("Load" if not is_cur else "View", key=f"load_sess_{sid}"):
                            _save_session()
                            try:
                                loaded = requests.get(f"{BACKEND_URL}/chat/load",
                                                      params={"user_id": st.session_state.email, "session_id": sid}, timeout=4).json()
                                st.session_state.chat_history        = loaded.get("messages", [])
                                st.session_state.chat_timestamps    = loaded.get("timestamps", [])
                                st.session_state.current_session_id = sid
                                st.session_state.show_chat_history  = False
                            except Exception:
                                st.error("Could not load session.")
                            st.rerun()
                with st.expander("🗑️ Delete a conversation"):
                    del_opts = {s.get("title","Chat")[:40]: s.get("session_id") for s in sessions}
                    del_choice = st.selectbox("Select", list(del_opts.keys()), key="del_sess_select")
                    if st.button("🗑️ Confirm Delete", key="del_sess_btn"):
                        del_sid = del_opts[del_choice]
                        try: requests.delete(f"{BACKEND_URL}/chat/session/{del_sid}", params={"user_id": st.session_state.email}, timeout=4)
                        except Exception: pass
                        if del_sid == st.session_state.current_session_id:
                            st.session_state.chat_history    = []
                            st.session_state.chat_timestamps = []
                            st.session_state.current_session_id = str(_uuid.uuid4())
                        st.session_state.show_chat_history = False
                        st.rerun()
            st.markdown("---")

        first_name = st.session_state.name.split()[0]
        if not st.session_state.chat_history:
            st.markdown(f"""<div class="conv-welcome">
                <div style="color:#e2e8f0; font-size:2.4rem; font-weight:900; line-height:1.2; letter-spacing:-0.5px; width:100%;">
                    I know your style, your code, your people. Ask me anything.
                </div>
            </div>""", unsafe_allow_html=True)
            
            # Anchor to pull the following columns into the welcome box
            st.markdown('<div class="welcome-merge-anchor"></div>', unsafe_allow_html=True)
            cc1,cc2,cc3,cc4,cc5 = st.columns(5)
            chip_prompt = None
            with cc1:
                if st.button("👗 What to wear?", key="chip_wear", use_container_width=True):
                    chip_prompt = "Based on my personal style memories, what should I wear today?"
            with cc2:
                if st.button("🎁 Gift idea", key="chip_gift", use_container_width=True):
                    chip_prompt = "Suggest a thoughtful gift idea. Ask me who it's for."
            with cc3:
                if st.button("💻 Review code", key="chip_code", use_container_width=True):
                    st.session_state["goto_shadow"] = True
                    st.rerun()
            with cc4:
                if st.button("📰 Tech news", key="chip_news", use_container_width=True):
                    chip_prompt = "What are the most important tech and AI developments trending right now?"
            with cc5:
                if st.button("🧬 Life Advice", key="chip_know", use_container_width=True):
                    chip_prompt = "Tell me everything you know about me from your memories and remind me about my goals."
            if chip_prompt:
                st.session_state["chip_inject"] = chip_prompt
                st.rerun()

        chat_container = st.container()

        if st.session_state.get("chip_inject"):
            chip_prompt = st.session_state.pop("chip_inject")
            now_str = _dt.datetime.now().strftime("%d %b %Y • %I:%M %p")
            st.session_state.chat_history.append({"role": "user", "content": chip_prompt})
            st.session_state.chat_timestamps.append(now_str)
            with chat_container:
                with st.chat_message("user"): st.write(chip_prompt)
                with st.chat_message("assistant"):
                    try:
                        tm_chip = ThinkingManager()
                        tm_chip.start()
                        def _stream_chip():
                            with requests.get(
                                f"{BACKEND_URL}/ask_stream",
                                params={"user_id": st.session_state.email, "question": chip_prompt, "mood": twin_mood},
                                stream=True, timeout=60
                            ) as r:
                                for line in r.iter_lines():
                                    if line:
                                        tm_chip.stop()
                                        decoded = line.decode("utf-8")
                                        if decoded.startswith("data: "):
                                            token = decoded[6:]
                                            if token == "[DONE]": return
                                            yield token.replace("\\n", "\n")
                        answer = st.write_stream(_stream_chip())
                        tm_chip.stop()
                        st.session_state.chat_history.append({"role": "assistant", "content": answer})
                        st.session_state.chat_timestamps.append(_dt.datetime.now().strftime("%d %b %Y • %I:%M %p"))
                        st.session_state.last_answer = answer
                        _save_session()
                        if st.session_state.get("voice_enabled", True): speak_text(answer)
                    except Exception as ex: st.error(f"Error: {ex}")
            st.rerun()

        with chat_container:
            for message in st.session_state.chat_history:
                with st.chat_message(message["role"]): st.write(message["content"])

        st.markdown('<div class="switches-anchor"></div>', unsafe_allow_html=True)
        a1, a2, a3 = st.columns([0.13, 0.13, 0.74])
        with a1: img_on   = st.toggle("📎 Photo", key="show_img_upload",   value=st.session_state.get("show_img_upload", False))
        with a2: voice_on = st.toggle("🎤 Voice", key="show_voice_input",  value=st.session_state.get("show_voice_input", False))
        with a3:
            if img_on or voice_on:
                active = []
                if img_on: active.append("📎 image upload active")
                if voice_on: active.append("🎤 voice input active")
                st.markdown(f"<p style='color:#38bdf8;font-size:0.78rem;margin-top:9px;font-weight:600'>{'  ·  '.join(active)}</p>", unsafe_allow_html=True)

        uploaded_images = None
        voice_prompt    = None
        if img_on:
            st.markdown('<div class="conv-upload-slim"><span class="conv-upload-slim-label">📎 ATTACH IMAGES · JPG / PNG · UP TO 10</span>', unsafe_allow_html=True)
            uploaded_images = st.file_uploader("", type=["jpg","jpeg","png"], accept_multiple_files=True, label_visibility="collapsed")
            st.markdown('</div>', unsafe_allow_html=True)
        if voice_on:
            voice_prompt = speech_to_text(language="en", start_prompt="🎤  Tap & speak", stop_prompt="🛑  Stop", key=f"voice_input_{st.session_state.get('voice_input_key',0)}")

        text_prompt = st.chat_input("Don’t Google it. Ask Me")
        prompt = text_prompt or voice_prompt
        
        last_user_prompt = ""
        if st.session_state.get("chat_history"):
            for msg in reversed(st.session_state.chat_history):
                if msg["role"] == "user":
                    last_user_prompt = msg["content"]
                    break
        current_edit_prompt = prompt if prompt else last_user_prompt
        
        # Inject JavaScript to handle Stop button properly alongside the text box
        import json
        import streamlit.components.v1 as components
        components.html(f"""
        <script>
        const doc = window.parent.document;
        const win = window.parent;
        
        function injectStopButton() {{
            const chatInputArea = doc.querySelector('[data-testid="stChatInput"]');
            if (!chatInputArea) return;
            const sendBtn = chatInputArea.querySelector('button');
            if (!sendBtn) return;
            
            // Check for stored prompt from a previous Stop action
            const storedPrompt = win.localStorage.getItem('twin_last_stopped_prompt');
            if (storedPrompt) {{
               const textarea = doc.querySelector('[data-testid="stChatInputTextArea"]') || doc.querySelector('textarea');
               if (textarea) {{
                    textarea.value = storedPrompt;
                    textarea.dispatchEvent(new Event('input', {{bubbles: true}}));
                    textarea.dispatchEvent(new Event('change', {{bubbles: true}}));
                    textarea.dispatchEvent(new Event('blur', {{bubbles: true}}));
                    win.localStorage.removeItem('twin_last_stopped_prompt');
                    textarea.focus();
               }}
            }}

            let stopBtn = doc.getElementById('twin-stop-js-btn');
            if (stopBtn) {{
                stopBtn.dataset.lastPrompt = {json.dumps(current_edit_prompt)};
                return;
            }}
            
            stopBtn = doc.createElement('button');
            stopBtn.id = 'twin-stop-js-btn';
            stopBtn.dataset.lastPrompt = {json.dumps(current_edit_prompt)};
            stopBtn.innerHTML = '<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>';
            stopBtn.style.cssText = 'display:inline-flex; align-items:center; justify-content:center; background:transparent; border:none; color:#94a3b8; cursor:not-allowed; opacity:0.5; padding:0.5rem; margin-right:0.4rem; transition:all 0.2s; border-radius:0.5rem; box-shadow:none;';
            
            stopBtn.onmouseover = () => {{ if(!stopBtn.disabled) stopBtn.style.color = '#ef4444'; }};
            stopBtn.onmouseout = () => {{ if(!stopBtn.disabled) stopBtn.style.color = '#f43f5e'; }};

            sendBtn.parentNode.insertBefore(stopBtn, sendBtn);
            
            const findThinkingState = () => {{
                const nativeButtons = Array.from(doc.querySelectorAll('button'));
                const nativeStop = nativeButtons.find(b => 
                    (b.textContent && b.textContent.includes('Stop')) || 
                    (b.ariaLabel && b.ariaLabel.includes('Stop'))
                );
                const thinkingText = Array.from(doc.querySelectorAll('div, p, span')).find(el => 
                    el.textContent && el.textContent.includes('Twin is thinking')
                );
                return !!(nativeStop || thinkingText || doc.querySelector('[data-testid="stSpinner"]'));
            }};

            const observer = new MutationObserver(() => {{
                if (findThinkingState()) {{
                    stopBtn.style.color = '#f43f5e';
                    stopBtn.style.cursor = 'pointer';
                    stopBtn.style.opacity = '1';
                    stopBtn.disabled = false;
                }} else {{
                    stopBtn.style.color = '#94a3b8';
                    stopBtn.style.cursor = 'not-allowed';
                    stopBtn.style.opacity = '0.5';
                    stopBtn.disabled = true;
                }}
            }});
            observer.observe(doc.body, {{ childList: true, subtree: true, characterData: true }});
            
            stopBtn.addEventListener('click', (e) => {{
                e.preventDefault();
                if (stopBtn.disabled) return;
                
                const lastPromptToUse = stopBtn.dataset.lastPrompt;
                if (lastPromptToUse) {{
                    win.localStorage.setItem('twin_last_stopped_prompt', lastPromptToUse);
                }}

                # 1. Try clicking native stop button
                const allButtons = Array.from(doc.querySelectorAll('button'));
                const stopTarget = allButtons.find(btn => 
                    btn !== stopBtn && (
                        (btn.innerText && btn.innerText.includes('Stop')) ||
                        (btn.ariaLabel && btn.ariaLabel.includes('Stop'))
                    )
                );

                if (stopTarget) {{
                    stopTarget.click();
                    // Give Streamlit a moment, then force inject if reload didn't happen
                    setTimeout(() => {{
                        const textarea = doc.querySelector('[data-testid="stChatInputTextArea"]') || doc.querySelector('textarea');
                        if (textarea && win.localStorage.getItem('twin_last_stopped_prompt')) {{
                            textarea.value = win.localStorage.getItem('twin_last_stopped_prompt');
                            textarea.dispatchEvent(new Event('input', {{bubbles: true}}));
                            win.localStorage.removeItem('twin_last_stopped_prompt');
                            textarea.focus();
                        }}
                    }}, 600);
                }} else {{
                    // 2. Failsafe: Reloading the page in Streamlit ALWAYS stops the execution
                    win.location.reload();
                }}
            }});
            
            try {{
                const iframes = doc.querySelectorAll('iframe');
                iframes.forEach(ifr => {{
                    if (ifr.srcdoc && ifr.srcdoc.includes('twin-stop-js-btn')) {{
                        if (ifr.parentNode && ifr.style.height === '0px') ifr.parentNode.style.display = 'none';
                    }}
                }});
            }} catch(e) {{}}
        }}

        setInterval(injectStopButton, 1000);
        injectStopButton();
        </script>
        """, height=0, width=0)

        if st.session_state.get("suppress_next_prompt", False):
            st.session_state["suppress_next_prompt"] = False
            prompt = None

        if prompt:
            emotion       = st.session_state.get("detected_emotion", "neutral")
            webcam_active = st.session_state.get("webcam_mood_enabled", False)
            tone_desc, emotion_opener = EMOTION_TONE.get(emotion, EMOTION_TONE["neutral"])
            mood_instruction = ""
            if webcam_active and emotion != "neutral":
                mood_instruction = f"The user appears {emotion}. Adopt a {tone_desc} tone. Start with: '{emotion_opener}' then answer."
            now_str = _dt.datetime.now().strftime("%d %b %Y • %I:%M %p")
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            st.session_state.chat_timestamps.append(now_str)
            with chat_container:
                with st.chat_message("user"): st.write(prompt)
                with st.chat_message("assistant"):
                    try:
                        _lang = st.session_state.get("language", "English")
                        _lang_instr = f"\n\n[LANGUAGE: Always respond in {_lang}.]" if _lang != "English" else ""
                        augmented = (f"[MOOD CONTEXT: {mood_instruction}]\n\nUser question: {prompt}{_lang_instr}" if mood_instruction else f"{prompt}{_lang_instr}")
                        if uploaded_images:
                            # Image analysis — can't stream, use ThinkingManager
                            files = [("files", (img.name, img.getvalue(), img.type)) for img in uploaded_images[:10]]
                            with ThinkingManager():
                                res = requests.post(f"{BACKEND_URL}/analyze_image",
                                    params={"user_id": st.session_state.email, "question": augmented, "mood": twin_mood},
                                    files=files, timeout=60)
                                answer = res.json()["answer"]
                            st.write_stream(_typewriter_stream(answer))
                        else:
                            # Text — stream tokens in real-time ♕
                            tm_main = ThinkingManager()
                            tm_main.start()
                            def _stream_main():
                                with requests.get(
                                    f"{BACKEND_URL}/ask_stream",
                                    params={"user_id": st.session_state.email, "question": augmented, "mood": twin_mood},
                                    stream=True, timeout=60
                                ) as r:
                                    for line in r.iter_lines():
                                        if line:
                                            tm_main.stop()
                                            decoded = line.decode("utf-8")
                                            if decoded.startswith("data: "):
                                                token = decoded[6:]
                                                if token == "[DONE]":
                                                    return
                                                yield token.replace("\\n", "\n")
                            answer = st.write_stream(_stream_main())
                            tm_main.stop()
                        st.session_state.chat_history.append({"role": "assistant", "content": answer})
                        st.session_state.chat_timestamps.append(_dt.datetime.now().strftime("%d %b %Y • %I:%M %p"))
                        st.session_state.last_answer = answer
                        _save_session()
                        if st.session_state.get("voice_enabled", True): speak_text(answer)
                        st.session_state["voice_input_key"] = st.session_state.get("voice_input_key", 0) + 1
                    except Exception as ex: st.error(f"Error: {ex}")
            st.rerun()


    # ── THINK SPACE ──────────────────────────────────────────────────────────
    with tab_brain:
        col_left, col_right = st.columns([1, 1])
        with col_left:
            st.subheader("🧬 Training")
            fact = st.text_area(
                "Update Twin Memory:", 
                height=150,
                placeholder="e.g., I recently started learning more about advanced vector databases and I prefer using Python for data processing. I live in Mumbai and love drinking filter coffee."
            )
            if st.button("Integrate Memory"):
                requests.post(f"{BACKEND_URL}/train?user_id={st.session_state.email}&details={fact}", timeout=8)
                _invalidate_cache(f"memories_{st.session_state.email}")
                st.success("Trained!")
        with col_right:
            st.subheader("🧠 Memory List")
            try:
                import datetime
                m_res = _api_get(f"{BACKEND_URL}/memories",
                                  params={"user_id": st.session_state.email},
                                  timeout=5, cache_key=f"memories_{st.session_state.email}",
                                  cache_ttl=60)
                if m_res is None: raise Exception("fetch failed")
                memories = m_res.get("memories", [])
                ids      = m_res.get("ids", [])
                def detect_category(text):
                    t = text.lower()
                    if any(k in t for k in ["[coding style","code","python","javascript","def ","class ","import "]): return ("💻","Code Style")
                    if any(k in t for k in ["[personal style]","wear","outfit","fashion","hoodie","jeans","colour"]): return ("👗","Style")
                    if any(k in t for k in ["like","love","enjoy","play","hobby","sport","music","game"]): return ("❤️","Interest")
                    if any(k in t for k in ["work","job","company","project","team","office","client"]): return ("💼","Work")
                    if any(k in t for k in ["friend","family","sister","brother","mom","dad","colleague"]): return ("👥","People")
                    return ("🧠","General")
                if memories:
                    st.markdown(f'<span class="memory-count-badge">🗂️ {len(memories)} memories stored</span>', unsafe_allow_html=True)
                    now = datetime.datetime.now()
                    
                    @st.dialog("All Memories")
                    def show_all_memories_dialog():
                        for i, (text, mid) in enumerate(zip(memories, ids)):
                            ts = now - datetime.timedelta(minutes=i*7)
                            icon, cat = detect_category(text)
                            display_text = text.replace("[CODING STYLE EXAMPLE]","").replace("[PERSONAL STYLE]","").strip()
                            if len(display_text) > 180: display_text = display_text[:180] + "…"
                            c1, c2 = st.columns([0.88, 0.12])
                            with c1:
                                st.markdown(f'<div class="memory-card"><div class="memory-card-text">{display_text}</div><div class="memory-card-meta"><span class="memory-badge">🕐 {ts.strftime("%I:%M %p")}</span><span class="memory-badge">📅 {ts.strftime("%d %b %Y")}</span><span class="memory-badge-cat">{icon} {cat}</span></div></div>', unsafe_allow_html=True)
                            with c2:
                                if st.button("🗑️", key=f"del_dialog_{i}"):
                                    requests.delete(f"{BACKEND_URL}/memories/{mid}", timeout=4)
                                    _invalidate_cache(f"memories_{st.session_state.email}")
                                    st.rerun()
                                    
                    for i, (text, mid) in enumerate(zip(memories[:3], ids[:3])):
                        ts = now - datetime.timedelta(minutes=i*7)
                        icon, cat = detect_category(text)
                        display_text = text.replace("[CODING STYLE EXAMPLE]","").replace("[PERSONAL STYLE]","").strip()
                        if len(display_text) > 180: display_text = display_text[:180] + "…"
                        c1, c2 = st.columns([0.88, 0.12])
                        with c1:
                            st.markdown(f'<div class="memory-card"><div class="memory-card-text">{display_text}</div><div class="memory-card-meta"><span class="memory-badge">🕐 {ts.strftime("%I:%M %p")}</span><span class="memory-badge">📅 {ts.strftime("%d %b %Y")}</span><span class="memory-badge-cat">{icon} {cat}</span></div></div>', unsafe_allow_html=True)
                        with c2:
                            if st.button("🗑️", key=f"del_{i}"):
                                requests.delete(f"{BACKEND_URL}/memories/{mid}", timeout=4)
                                _invalidate_cache(f"memories_{st.session_state.email}")
                                st.rerun()

                    if len(memories) > 3:
                        if st.button("Show more"):
                            show_all_memories_dialog()
                else:
                    st.info("No memories yet. Add your first memory using the Training panel on the left!")
            except Exception: pass

    # ── CODE ASSISTANT ───────────────────────────────────────────────────────
    with tab_shadow:
        st.markdown('<div class="shadow-header"><h3>👾 Code Assistant Mode — Enhanced</h3><p>Train your twin with your coding style, then debug with syntax checking, code execution, diff view, and git repo context.</p></div>', unsafe_allow_html=True)
        shadow_col1, shadow_col2 = st.columns([1, 1])
        with shadow_col1:
            st.subheader("🧬 Teach Your Coding Style")
            style_snippet = st.text_area(
                "Paste a code snippet that represents your style:", 
                height=180, 
                key="style_snippet",
                placeholder="def fetch_data(url: str) -> dict:\n    # I always use type hints and clear comments\n    # response = requests.get(url)\n    # return response.json()"
            )
            style_note = st.text_input(
                "Describe this style (optional):", 
                key="style_note",
                placeholder="Clean, documented Python with type hinting and standard snake_case naming."
            )
            if st.button("🧠 Train Coding Style", key="train_style"):
                if style_snippet.strip():
                    note = style_note.strip() or "general coding style"
                    requests.post(f"{BACKEND_URL}/train", params={"user_id": st.session_state.email, "details": f"[CODING STYLE EXAMPLE] {note}:\n```\n{style_snippet}\n```"}, timeout=8)
                    _invalidate_cache(f"memories_{st.session_state.email}")
                    st.success("✅ Coding style learned!")
                else:
                    st.warning("Please paste a code snippet first.")
            st.markdown("---")
            st.caption("📚 Learned coding styles:")
            try:
                m_res2 = _api_get(f"{BACKEND_URL}/memories",
                                   params={"user_id": st.session_state.email},
                                   timeout=5, cache_key=f"memories_{st.session_state.email}",
                                   cache_ttl=60)
                if m_res2 is None: m_res2 = {"memories": [], "ids": []}
                style_mems = [(m, mid) for m, mid in zip(m_res2["memories"], m_res2["ids"]) if "[CODING STYLE EXAMPLE]" in m]
                for mem, mid in style_mems:
                    c1, c2 = st.columns([0.88, 0.12])
                    with c1: st.markdown(f'<div class="code-style-card">🔖 {mem.replace("[CODING STYLE EXAMPLE]","").strip()[:120]}...</div>', unsafe_allow_html=True)
                    with c2:
                        if st.button("🗑️", key=f"del_style_{mid}"):
                            requests.delete(f"{BACKEND_URL}/memories/{mid}", timeout=4)
                            _invalidate_cache(f"memories_{st.session_state.email}")
                            st.rerun()
                if not style_mems: st.caption("No coding styles trained yet.")
            except Exception: pass
            st.markdown("---")
            st.subheader("📁 Git Repo Explorer")
            repo_path_input = st.text_input("Local repo path:", placeholder="/home/user/my-project", key="repo_path_input")
            repo_ext_filter = st.text_input("File extensions (optional):", placeholder=".py,.js,.ts", key="repo_ext_filter")
            if st.button("🔍 Browse Repo", key="browse_repo"):
                if repo_path_input.strip():
                    with st.spinner("Reading repo files..."):
                        params = {"repo_path": repo_path_input.strip(), "max_files": 25}
                        if repo_ext_filter.strip(): params["extensions"] = repo_ext_filter.strip()
                        try:
                            repo_data = requests.get(f"{BACKEND_URL}/repo_files", params=params).json()
                            st.session_state["last_repo_data"] = repo_data
                            st.success(f'{"✅ Git repo" if repo_data.get("is_git_repo") else "📂 Folder"} — {repo_data["total_files"]} files found')
                        except Exception as ex: st.error(f"Repo browse error: {ex}")
                else: st.warning("Enter a repo path first.")
            if st.session_state.get("last_repo_data"):
                rd = st.session_state["last_repo_data"]
                with st.expander(f"📋 {rd['total_files']} files in repo"):
                    for fp, cp in rd.get("files",{}).items():
                        st.markdown(f'<div class="repo-card"><b>{fp}</b><br><code>{cp[:200]}{"..." if len(cp)>200 else ""}</code></div>', unsafe_allow_html=True)
        with shadow_col2:
            st.subheader("🐛 Debug With Your Twin")
            language   = st.selectbox("Language:", ["Python","JavaScript","TypeScript","Java","C++","C","Go","Rust","Bash","Other"], key="debug_language")
            debug_mode = st.radio("Life Advice", ["🐛 Find & Fix Bugs","🔍 Code Review","⚡ Optimize Code","💬 Explain This Code"], key="debug_mode", horizontal=True)
            buggy_code = st.text_area(
                "Paste your code here:", 
                height=220, 
                key="buggy_code",
                placeholder="def calculate_total(items):\n    total = 0\n    for i in items:\n        total += i\n    return total # How can I optimize this for large lists?"
            )
            extra_ctx = st.text_input(
                "What's the problem? (optional):", 
                key="extra_context",
                placeholder="e.g., The loop is too slow for 1 million items. Can we use numpy or list comprehension?"
            )
            ec1, ec2   = st.columns(2)
            with ec1: run_original = st.checkbox("▶️ Run original code", value=False, key="run_original")
            with ec2: run_fixed     = st.checkbox("▶️ Run fixed code",    value=False, key="run_fixed")
            use_repo = st.checkbox("📁 Include repo context", value=False, key="use_repo_ctx")
            repo_path_for_debug = repo_path_input if use_repo and repo_path_input.strip() else ""
            if st.button("👾 Activate Code Assistant", key="run_shadow", type="primary"):
                if buggy_code.strip():
                    mode_label = debug_mode.split(" ",1)[1]
                    with ThinkingManager():
                        try:
                            data = requests.post(f"{BACKEND_URL}/debug_code", json={
                                "user_id": st.session_state.email, "code": buggy_code,
                                "language": language, "mode": mode_label, "mood": twin_mood,
                                "extra_context": extra_ctx or "", "run_code": run_original,
                                "run_fixed": run_fixed, "repo_path": repo_path_for_debug,
                            }, timeout=60).json()
                            syntax = data.get("syntax_check", {})
                            if syntax.get("errors") or syntax.get("warnings"):
                                st.markdown("### 🔍 Pre-Analysis Syntax Check")
                                for e in syntax.get("errors",[]): st.markdown(f'<div class="syntax-error-card">❌ {e}</div>', unsafe_allow_html=True)
                                for w in syntax.get("warnings",[]): st.markdown(f'<div class="syntax-warn-card">⚠️ {w}</div>', unsafe_allow_html=True)
                            else:
                                st.success("✅ Pre-analysis syntax check passed.")
                            eo = data.get("execution_original",{})
                            if eo.get("ran"):
                                st.markdown("### ▶️ Original Code Execution")
                                st.markdown(f'<div class="exec-card">{"✅" if eo["exit_code"]==0 else "❌"} Exit: <b>{eo["exit_code"]}</b><br><br><b>STDOUT:</b><pre>{eo["stdout"] or "(empty)"}</pre><b>STDERR:</b><pre>{eo["stderr"] or "(none)"}</pre></div>', unsafe_allow_html=True)
                            if data.get("repo_context_used"): st.info(f'📁 Repo context: {data.get("repo_files_read",0)} files.')
                            st.markdown("### 🤖 AI Analysis")
                            st.write_stream(_typewriter_stream(data.get("ai_analysis","No response.")))
                            diff_text  = data.get("diff","")
                            fixed_code = data.get("fixed_code","")
                            if fixed_code and "No changes" not in diff_text:
                                st.markdown("### 📊 What Changed — Diff View")
                                st.markdown(f'<div class="diff-card">{render_diff_html(diff_text)}</div>', unsafe_allow_html=True)
                                with st.expander("📋 Copy Fixed Code"): st.code(fixed_code, language=language.lower())
                            ef = data.get("execution_fixed",{})
                            if ef.get("ran"):
                                st.markdown("### ▶️ Fixed Code Execution")
                                st.markdown(f'<div class="exec-card">{"✅" if ef["exit_code"]==0 else "❌"} Exit: <b>{ef["exit_code"]}</b><br><br><b>STDOUT:</b><pre>{ef["stdout"] or "(empty)"}</pre><b>STDERR:</b><pre>{ef["stderr"] or "(none)"}</pre></div>', unsafe_allow_html=True)
                            if st.session_state.get("voice_enabled",True): speak_text(data.get("ai_analysis",""))
                        except Exception as ex: st.error(f"Code Assistant Error: {ex}")
                else: st.warning("Please paste some code first.")

    # ── MY STYLE ─────────────────────────────────────────────────────────────
    with tab_mirror:
        st.markdown('<div class="mirror-header"><h3>🪞 My Style — Get your outfit rated by your AI Twin</h3><p>Upload your fit 👀 — your AI Twin will rate it, roast it (a little 😏), and upgrade your style game instantly.</p></div>', unsafe_allow_html=True)
        mc1, mc2 = st.columns([1, 1])
        with mc1:
            st.subheader("📸 Upload Your Outfit")
            uploader_css = """
            <style>
            [data-testid="stFileUploader"] > label {
                display: none !important;
            }
            [data-testid="stFileUploader"] section {
                border: 2px dashed rgba(255,255,255,0.15) !important;
                background: rgba(15,23,42,0.4) !important;
                border-radius: 16px !important;
                min-height: 200px !important;
                padding: 40px !important;
                display: flex !important;
                flex-direction: column !important;
                align-items: center !important;
                justify-content: center !important;
                transition: all 0.3s ease !important;
            }
            [data-testid="stFileUploader"] section:hover {
                border-color: #38bdf8 !important;
                background: rgba(56,189,248,0.05) !important;
                box-shadow: 0 8px 24px rgba(56,189,248,0.1) !important;
                transform: translateY(-2px);
            }
            [data-testid="stFileUploader"] section svg,
            [data-testid="stFileUploader"] section button {
                display: none !important;
            }
            [data-testid="stFileUploader"] section p {
                font-size: 0 !important;
                margin-bottom: 5px !important;
                display: flex !important;
                flex-direction: column !important;
                align-items: center !important;
            }
            [data-testid="stFileUploader"] section p::before {
                content: "📷";
                font-size: 3.5rem !important;
                display: block !important;
                margin-bottom: 20px !important;
                color: #e2e8f0 !important;
                
                line-height: 1 !important;
            }
            [data-testid="stFileUploader"] section p::after {
                content: "Use the uploader above to add photos";
                font-size: 1.1rem !important;
                color: #94a3b8 !important;
                font-weight: 500 !important;
                display: block !important;
            }
            [data-testid="stFileUploader"] section small {
                font-size: 0 !important;
                display: block !important;
            }
            [data-testid="stFileUploader"] section small::after {
                content: "JPG, PNG, WEBP · Up to 3 photos";
                font-size: 0.9rem !important;
                color: #475569 !important;
                font-weight: 500 !important;
                display: block !important;
            }
            [data-testid="stFileUploader"] section > div {
                display: flex !important;
                flex-direction: column !important;
                align-items: center !important;
            }
            </style>
            """
            st.markdown(uploader_css, unsafe_allow_html=True)
            outfit_images = st.file_uploader("Upload 1-3 outfit photos", type=["jpg","jpeg","png","webp"], accept_multiple_files=True, key="outfit_uploader")
            occasion_css = """
            <style>
            div[data-testid="stVerticalBlock"] > div:has(.occasion-anchor) + div { width: 100% !important; display: block !important; }
            div[data-testid="stVerticalBlock"] > div:has(.occasion-anchor) + div [data-testid="stRadio"], div[data-testid="stVerticalBlock"] > div:has(.occasion-anchor) + div [data-testid="stRadio"] > div { width: 100% !important; max-width: 100% !important; }
            div[data-testid="stVerticalBlock"] > div:has(.occasion-anchor) + div [data-testid="stRadio"] > div[role="radiogroup"] { display: grid !important; grid-template-columns: repeat(3, 1fr) !important; gap: 18px !important; margin-top: 12px !important; width: 100% !important; }
            div[data-testid="stVerticalBlock"] > div:has(.occasion-anchor) + div [data-testid="stRadio"] div[role="radiogroup"] > label { background: transparent !important; border: 1px solid rgba(255,255,255,0.15) !important; border-radius: 16px !important; padding: 18px 8px !important; cursor: pointer !important; transition: all 0.3s ease !important; margin: 0 !important; display: flex !important; justify-content: center !important; flex-direction: column !important; align-items: center !important; min-height: 115px !important; width: 100% !important; }
            div[data-testid="stVerticalBlock"] > div:has(.occasion-anchor) + div [data-testid="stRadio"] div[role="radiogroup"] > label:hover { background: rgba(56,189,248,0.1) !important; border-color: rgba(56,189,248,0.4) !important; transform: translateY(-4px); box-shadow: 0 6px 20px rgba(0,0,0,0.2) !important; }
            div[data-testid="stVerticalBlock"] > div:has(.occasion-anchor) + div [data-testid="stRadio"] div[role="radiogroup"] > label > div:first-child { display: none !important; }
            div[data-testid="stVerticalBlock"] > div:has(.occasion-anchor) + div [data-testid="stRadio"] div[role="radiogroup"] > label > div:last-child, div[data-testid="stVerticalBlock"] > div:has(.occasion-anchor) + div [data-testid="stRadio"] div[role="radiogroup"] > label > div:last-child p { margin: 0 !important; font-size: 1.6rem !important; font-weight: 700 !important; color: #94a3b8 !important; text-align: center !important; line-height: 1.4 !important; white-space: pre-line !important; padding: 0 !important; width: 100% !important; border: none !important; }
            div[data-testid="stVerticalBlock"] > div:has(.occasion-anchor) + div [data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked) { background: rgba(56,189,248,0.12) !important; border-color: #38bdf8 !important; box-shadow: 0 8px 24px rgba(56,189,248,0.25) !important; transform: translateY(-4px); }
            div[data-testid="stVerticalBlock"] > div:has(.occasion-anchor) + div [data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked) > div:last-child, div[data-testid="stVerticalBlock"] > div:has(.occasion-anchor) + div [data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked) > div:last-child p { color: #38bdf8 !important; font-weight: 800 !important; }
            div[data-testid="stVerticalBlock"] > div:has(.occasion-anchor) + div [data-testid="stRadio"] > label { font-size: 0.95rem !important; font-weight: 800 !important; color: #94a3b8 !important; letter-spacing: 1px !important; text-transform: uppercase !important; margin-bottom: 12px !important; display: block !important; }
            </style>
            """
            st.markdown(occasion_css + '<div class="occasion-anchor"></div>', unsafe_allow_html=True)
            occ_choice = st.radio("🎯 WHAT'S THE OCCASION?", ["👟\nCasual", "💼\nOffice", "🌹\nDate night", "🎉\nParty", "🎓\nCampus", "🥂\nFormal"], key="mirror_occasion_radio")
            occ_map = {"👟\nCasual": "casual", "💼\nOffice": "office / work", "🌹\nDate night": "date night", "🎉\nParty": "party / nightout", "🎓\nCampus": "college / campus", "🥂\nFormal": "formal / wedding"}
            occasion = occ_map.get(occ_choice, "casual")
            st.markdown("---")
            st.subheader("🧬 Teach Your Style")
            style_fact = st.text_area(
                "Add a style preference:", 
                height=100, 
                key="mirror_style_fact",
                placeholder="e.g., I prefer minimalist, modern outfits with neutral colors like obsidian, slate grey, and ivory. I avoid bright neon colors and prefer slim-fit silhouettes."
            )
            if st.button("💾 Save Style Preference", key="save_style_pref"):
                if style_fact.strip():
                    requests.post(f"{BACKEND_URL}/train", params={"user_id": st.session_state.email, "details": f"[PERSONAL STYLE] {style_fact.strip()}"}, timeout=8)
                    _invalidate_cache(f"memories_{st.session_state.email}")
                    st.success("✅ Style preference saved!")
                else: st.warning("Please enter a style preference first.")
            st.caption("📋 Your saved style profile:")
            try:
                m_res3 = _api_get(f"{BACKEND_URL}/memories",
                                   params={"user_id": st.session_state.email},
                                   timeout=5, cache_key=f"memories_{st.session_state.email}",
                                   cache_ttl=60)
                if m_res3 is None: m_res3 = {"memories": [], "ids": []}
                style_prefs = [(m,mid) for m,mid in zip(m_res3["memories"],m_res3["ids"]) if "[PERSONAL STYLE]" in m]
                for mem, mid in style_prefs:
                    c1, c2 = st.columns([0.88, 0.12])
                    with c1: st.markdown(f'<div class="style-tip-card">👗 {mem.replace("[PERSONAL STYLE]","").strip()[:130]}</div>', unsafe_allow_html=True)
                    with c2:
                        if st.button("🗑️", key=f"del_style_pref_{mid}"):
                            requests.delete(f"{BACKEND_URL}/memories/{mid}", timeout=4)
                            _invalidate_cache(f"memories_{st.session_state.email}")
                            st.rerun()
                if not style_prefs: st.caption("No style profile yet.")
            except Exception: pass
        with mc2:
            st.subheader("🎨 Fashion Grade")
            if outfit_images:
                pc = st.columns(min(len(outfit_images),3))
                for idx, img in enumerate(outfit_images[:3]):
                    with pc[idx]: st.image(img, use_container_width=True, caption=f"Photo {idx+1}")
            if st.button("🪞 Grade My Outfit", key="run_style_mirror", type="primary", disabled=not outfit_images):
                with ThinkingManager():
                    try:
                        files = [("files",(img.name,img.getvalue(),img.type)) for img in outfit_images[:3]]
                        answer = requests.post(f"{BACKEND_URL}/style_mirror",
                                                params={"user_id": st.session_state.email, "mood": twin_mood, "occasion": occasion},
                                                files=files).json().get("answer","No response.")
                        import re
                        score_match = re.search(r"(\d+(?:\.\d+)?)/10", answer)
                        if score_match: st.markdown(f'<div style="text-align:center"><span class="score-badge">⭐ {score_match.group(0)}</span></div>', unsafe_allow_html=True)
                        st.write_stream(_typewriter_stream(answer))
                        if "style_mirror_history" not in st.session_state: st.session_state.style_mirror_history = []
                        st.session_state.style_mirror_history.append({"occasion": occasion, "score": score_match.group(0) if score_match else "?/10"})
                        if st.session_state.get("voice_enabled",True): speak_text(answer)
                    except Exception as ex: st.error(f"My Style Error: {ex}")
            if not outfit_images:
                st.info("👆 Upload an outfit photo on the left to get started.")
                st.markdown("""
                <div style="margin-top: 16px; padding: 22px; background: linear-gradient(145deg, rgba(14,165,233,0.05), rgba(99,102,241,0.03)); border: 1px solid rgba(56,189,248,0.15); border-radius: 14px; box-shadow: 0 4px 20px rgba(0,0,0,0.1);">
                    <h4 style="color: #38bdf8; margin-top: 0; margin-bottom: 20px; font-size: 1.1rem; font-weight: 700;">✨ How Fashion Critic Works</h4>
                    <div style="display: flex; flex-direction: column; gap: 18px;">
                        <div style="display: flex; gap: 14px; align-items: center; transition: transform 0.2s ease;" onmouseover="this.style.transform='translateX(5px)'" onmouseout="this.style.transform='none'">
                            <div style="background: rgba(14, 165, 233, 0.12); width: 42px; height: 42px; border-radius: 10px; display: flex; align-items: center; justify-content: center; color: #38bdf8; font-size: 1.3rem; border: 1px solid rgba(14, 165, 233, 0.2); flex-shrink: 0;">📸</div>
                            <div>
                                <div style="color: #e2e8f0; font-weight: 600; font-size: 0.95rem;">1. Upload Your Look</div>
                                <div style="color: #94a3b8; font-size: 0.85rem; margin-top: 3px;">Share up to 3 photos of your outfit and tell us the occasion.</div>
                            </div>
                        </div>
                        <div style="display: flex; gap: 14px; align-items: center; transition: transform 0.2s ease;" onmouseover="this.style.transform='translateX(5px)'" onmouseout="this.style.transform='none'">
                            <div style="background: rgba(168, 85, 247, 0.12); width: 42px; height: 42px; border-radius: 10px; display: flex; align-items: center; justify-content: center; color: #c4b5fd; font-size: 1.3rem; border: 1px solid rgba(168, 85, 247, 0.2); flex-shrink: 0;">🧬</div>
                            <div>
                                <div style="color: #e2e8f0; font-weight: 600; font-size: 0.95rem;">2. Style Analysis</div>
                                <div style="color: #94a3b8; font-size: 0.85rem; margin-top: 3px;">Your AI Twin references your saved personal style profile.</div>
                            </div>
                        </div>
                        <div style="display: flex; gap: 14px; align-items: center; transition: transform 0.2s ease;" onmouseover="this.style.transform='translateX(5px)'" onmouseout="this.style.transform='none'">
                            <div style="background: rgba(236, 72, 153, 0.12); width: 42px; height: 42px; border-radius: 10px; display: flex; align-items: center; justify-content: center; color: #f472b6; font-size: 1.3rem; border: 1px solid rgba(236, 72, 153, 0.2); flex-shrink: 0;">📊</div>
                            <div>
                                <div style="color: #e2e8f0; font-weight: 600; font-size: 0.95rem;">3. Get Graded</div>
                                <div style="color: #94a3b8; font-size: 0.85rem; margin-top: 3px;">Receive a detailed fashion critique, score, and personalized tips.</div>
                            </div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                history = st.session_state.get("style_mirror_history", [])
                if history:
                    st.markdown('<h4 style="color: #94a3b8; margin-top: 24px; margin-bottom: 12px; font-size: 0.95rem; font-weight: 600;">🕒 Recent Grades</h4>', unsafe_allow_html=True)
                    for h in reversed(history[-3:]):
                        st.markdown(f'''
                        <div style="background: rgba(15, 23, 42, 0.5); border: 1px solid rgba(56,189,248,0.1); border-left: 3px solid #38bdf8; border-radius: 8px; padding: 12px 16px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; transition: all 0.2s ease;" onmouseover="this.style.borderColor='rgba(56,189,248,0.4)'; this.style.transform='translateX(4px)'" onmouseout="this.style.borderColor='rgba(56,189,248,0.1)'; this.style.transform='none'">
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <span style="font-size: 1.2rem;">👔</span>
                                <span style="color: #e2e8f0; font-size: 0.95rem; font-weight: 500; text-transform: capitalize;">{h["occasion"]}</span>
                            </div>
                            <span style="background: rgba(56,189,248,0.1); color: #38bdf8; font-weight: 700; font-size: 0.9rem; padding: 4px 12px; border-radius: 20px; border: 1px solid rgba(56,189,248,0.2);">{h["score"]}</span>
                        </div>
                        ''', unsafe_allow_html=True)

    # ── MY FEED ──────────────────────────────────────────────────────────────
    with tab_news:
        st.markdown('<div class="newsroom-header"><h3>📰 My Feed — Your Personalised Morning Briefing</h3><p>Your Twin scans live news about your tech stack, location, and interests.</p></div>', unsafe_allow_html=True)
        nc1, nc2 = st.columns([1, 1])
        with nc1:
            st.subheader("⚙️ Briefing Settings")
            location_input = st.text_input(
                "Cities / Regions (comma-separated):", 
                value=st.session_state.get("newsroom_locations","Delhi, India"), 
                key="newsroom_loc_input",
                placeholder="e.g., San Francisco, London, Tokyo, Bangalore"
            )
            st.session_state["newsroom_locations"] = location_input
            topics_input = st.text_input(
                "Topics (comma-separated):", 
                value=st.session_state.get("newsroom_topics",""), 
                key="newsroom_topics_input",
                placeholder="e.g., AI Research, Web Development, Climate Change, Digital Twin Technology"
            )
            st.session_state["newsroom_topics"] = topics_input
            st.markdown("---")
            news_mood = st.radio("📣 Briefing Tone", ["Professional","Natural","Sarcastic"],
                                  index=["Professional","Natural","Sarcastic"].index(st.session_state.get("newsroom_mood","Natural")),
                                  key="newsroom_mood_radio", horizontal=True)
            st.session_state["newsroom_mood"] = news_mood
            st.markdown("---")
            if st.session_state.get("last_briefing_stack"):
                st.caption("Last detected stack:")
                st.markdown("".join(f'<span class="tech-tag">{t}</span>' for t in st.session_state["last_briefing_stack"]), unsafe_allow_html=True)
            run_briefing = st.button("📡 Get My Briefing", key="run_morning_briefing", type="primary", use_container_width=True)
            st.markdown("<br>", unsafe_allow_html=True)
        with nc2:
            st.subheader("🗞️ Your Briefing")
            if st.session_state.get("last_briefing_text") and not run_briefing:
                st.markdown(f'<div class="briefing-card">{st.session_state["last_briefing_text"]}</div>', unsafe_allow_html=True)
                meta = f'<span class="news-meta-badge">📡 {st.session_state.get("last_briefing_articles",0)} articles scanned</span>'
                meta += f'<span class="news-meta-badge">🎭 {st.session_state.get("last_briefing_mood","Natural")} tone</span>'
                st.markdown(meta, unsafe_allow_html=True)
                if st.session_state.get("voice_enabled",True):
                    if st.button("🔊 Read Briefing Aloud", key="read_briefing"): speak_text(st.session_state["last_briefing_text"])
            elif not run_briefing:
                st.info("👈 Configure your settings and hit ☀️ Get My Morning Report to start.")
            if run_briefing:
                locations = [l.strip() for l in location_input.split(",") if l.strip()] or ["India"]
                topics    = [t.strip() for t in topics_input.split(",") if t.strip()]
                with st.spinner("📡 Scanning live news..."):
                    try:
                        data = requests.post(f"{BACKEND_URL}/morning_briefing", json={"user_id": st.session_state.email, "mood": news_mood, "locations": locations, "extra_topics": topics}, timeout=60).json()
                        briefing_text = data.get("briefing","No briefing returned.")
                        st.session_state["last_briefing_text"]     = briefing_text
                        st.session_state["last_briefing_articles"] = data.get("articles_found",0)
                        st.session_state["last_briefing_mood"]     = news_mood
                        st.session_state["last_briefing_stack"]    = data.get("tech_stack_detected",[])
                        meta = f'<span class="news-meta-badge">📡 {data.get("articles_found",0)} articles scanned</span>'
                        meta += f'<span class="news-meta-badge">🎭 {news_mood} tone</span>'
                        meta += "".join(f'<span class="tech-tag">{t}</span>' for t in data.get("tech_stack_detected",[]))
                        st.markdown(meta, unsafe_allow_html=True)
                        st.markdown(f'<div class="briefing-card">{briefing_text}</div>', unsafe_allow_html=True)
                        if st.session_state.get("voice_enabled",True): speak_text(briefing_text)
                    except requests.exceptions.Timeout: st.error("⏰ Timed out. Try again.")
                    except Exception as ex: st.error(f"My Feed Error: {ex}")

    # ── ANALYTICS ─────────────────────────────────────────────────────────────
    with tab_analytics:
        import plotly.express as px
        import plotly.graph_objects as go
        st.markdown('<div style="padding:18px 0 10px 0;margin-bottom:20px;margin-left:10px"><h3 style="color:#34d399;margin:0 0 4px 0">📊 Twin Analytics</h3><p style="color:#64748b;margin:0;font-size:0.88rem">Insights about your memories, chat patterns and knowledge base.</p></div>', unsafe_allow_html=True)
        
        # ── Export Control (Moved from Sidebar) ───────────────────────────────────
        st.markdown('<div class="export-report-anchor"></div>', unsafe_allow_html=True)
        if st.button("💾 Generate CSV Export Report", key="export_report_btn", use_container_width=True):
            csv_res = requests.get(f"{BACKEND_URL}/export?user_id={st.session_state.email}")
            if csv_res.status_code == 200:
                st.download_button("Download Memories", data=csv_res.content, file_name="twin_data.csv", mime="text/csv")
        st.markdown("<br>", unsafe_allow_html=True)
        try:
            counts   = (_api_get(f"{BACKEND_URL}/analytics",
                                  params={"user_id": st.session_state.email},
                                  timeout=5, cache_key=f"analytics_{st.session_state.email}",
                                  cache_ttl=120) or {}).get("counts", {})
            sessions = (_api_get(f"{BACKEND_URL}/chat/sessions",
                                  params={"user_id": st.session_state.email},
                                  timeout=5, cache_key=f"sessions_{st.session_state.email}",
                                  cache_ttl=60) or {}).get("sessions", [])
            # message_count is stored on the session doc; fall back to 0 if missing
            total_user = sum(s.get("message_count", 0) // 2 for s in sessions)
            kpi = "background:rgba(56,189,248,0.08);border:1px solid rgba(56,189,248,0.2);border-radius:12px;padding:16px;text-align:center"
            k1,k2,k3,k4 = st.columns(4)
            with k1: st.markdown(f"<div style='{kpi}'><div style='font-size:2rem;font-weight:900;color:#38bdf8'>{sum(counts.values())}</div><div style='color:#64748b;font-size:0.8rem'>Total Memories</div></div>", unsafe_allow_html=True)
            with k2: st.markdown(f"<div style='{kpi}'><div style='font-size:2rem;font-weight:900;color:#a78bfa'>{len(sessions)}</div><div style='color:#64748b;font-size:0.8rem'>Conversations</div></div>", unsafe_allow_html=True)
            with k3: st.markdown(f"<div style='{kpi}'><div style='font-size:2rem;font-weight:900;color:#34d399'>{total_user}</div><div style='color:#64748b;font-size:0.8rem'>Questions Asked</div></div>", unsafe_allow_html=True)
            with k4: st.markdown(f"<div style='{kpi}'><div style='font-size:2rem;font-weight:900;color:#fb923c'>{len(counts)}</div><div style='color:#64748b;font-size:0.8rem'>Memory Categories</div></div>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            cl, cr = st.columns(2)
            with cl:
                if counts:
                    fig = px.pie(names=list(counts.keys()), values=list(counts.values()), title="🧠 Memory by Category", color_discrete_sequence=px.colors.sequential.Plasma_r, hole=0.45)
                    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#e2e8f0", title_font_size=14, margin=dict(t=40,b=10,l=10,r=10), legend=dict(font=dict(color="#94a3b8")))
                    st.plotly_chart(fig, use_container_width=True)
                else: st.info("No memories yet.")
            with cr:
                if sessions:
                    msg_counts = [s.get("message_count", 0) for s in sessions[:10]]
                    titles     = [s.get("title","")[:20]+"…" for s in sessions[:10]]
                    fig2 = go.Figure(go.Bar(x=msg_counts, y=titles, orientation="h", marker_color="#38bdf8", text=msg_counts, textposition="outside"))
                    fig2.update_layout(title="💬 Messages per Conversation", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#e2e8f0", title_font_size=14, margin=dict(t=40,b=10,l=10,r=10), xaxis=dict(showgrid=False,color="#475569"), yaxis=dict(color="#94a3b8"), height=300)
                    st.plotly_chart(fig2, use_container_width=True)
                else: st.info("No conversations yet.")
        except Exception as ex: st.error(f"Analytics error: {ex}")

    # ── GOALS ─────────────────────────────────────────────────────────────────
    with tab_goals:
        st.markdown('<div style="padding:18px 0 10px 0;margin-bottom:20px;margin-left:10px"><h3 style="color:#38bdf8;margin:0 0 4px 0"> 🎯 Goals & Habits Tracker </h3><p style="color:#64748b;margin:0;font-size:0.88rem">set goals, track progress, and let your Twin keep you accountable..</p></div>', unsafe_allow_html=True)
        gl, gr = st.columns([1, 1])
        with gl:
            st.markdown("#### ➕ Add New Goal")
            new_goal = st.text_area("Goal description", placeholder="e.g. Run 5km every day", height=90, key="new_goal_text")
            goal_cat = st.selectbox("Category", ["Health & Fitness","Learning","Career","Personal","Finance","Relationships","Other"], key="goal_cat")
            if st.button("🎯 Add Goal", key="add_goal_btn", use_container_width=True):
                if new_goal.strip():
                    requests.post(f"{BACKEND_URL}/goals/add", json={"user_id": st.session_state.email, "goal": new_goal.strip(), "category": goal_cat})
                    st.success("✅ Goal added!"); st.rerun()
                else: st.warning("Please enter a goal first.")
        with gr:
            st.markdown("#### 📋 Your Goals")
            try:
                goals_list = requests.get(f"{BACKEND_URL}/goals?user_id={st.session_state.email}", timeout=4).json().get("goals",[])
                cat_icons  = {"Health & Fitness":"💪","Learning":"📚","Career":"💼","Personal":"🌱","Finance":"💰","Relationships":"❤️","Other":"🎯"}
                if not goals_list: st.info("No goals yet.")
                for goal in goals_list:
                    gid=goal["_id"]; gtitle=goal.get("goal",""); gcat=goal.get("category","Other")
                    gprog=goal.get("progress",0); gdone=goal.get("completed",False)
                    icon=cat_icons.get(gcat,"🎯"); bar_col="#34d399" if gdone else "#38bdf8"
                    done_badge='<span style="background:#34d399;color:#0f172a;padding:2px 8px;border-radius:12px;font-size:0.7rem;font-weight:700">✓ DONE</span>' if gdone else ""
                    st.markdown(f'<div style="background:rgba(52,211,153,0.06);border:1px solid rgba(52,211,153,0.18);border-left:4px solid {bar_col};border-radius:12px;padding:14px 16px;margin-bottom:10px"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px"><span style="color:#e2e8f0;font-weight:600">{icon} {gtitle}</span>{done_badge}</div><div style="background:rgba(255,255,255,0.08);border-radius:6px;height:8px;overflow:hidden"><div style="background:linear-gradient(90deg,{bar_col},{bar_col}99);height:100%;width:{min(gprog,100)}%;border-radius:6px"></div></div><div style="display:flex;justify-content:space-between;margin-top:4px"><span style="color:#64748b;font-size:0.72rem">{gcat}</span><span style="color:{bar_col};font-size:0.72rem;font-weight:700">{gprog}%</span></div></div>', unsafe_allow_html=True)
                    with st.expander(f"Update · {gtitle[:30]}"):
                        new_prog = st.slider("Progress %", 0, 100, gprog, key=f"prog_{gid}")
                        note_txt = st.text_input("Add a note (optional)", key=f"note_{gid}")
                        uc1, uc2 = st.columns(2)
                        with uc1:
                            if st.button("💾 Save", key=f"save_goal_{gid}", use_container_width=True):
                                requests.post(f"{BACKEND_URL}/goals/update", json={"goal_id": gid, "progress": new_prog, "note": note_txt}); st.rerun()
                        with uc2:
                            if st.button("🗑️ Delete", key=f"del_goal_{gid}", use_container_width=True):
                                requests.delete(f"{BACKEND_URL}/goals/{gid}", params={"user_id": st.session_state.email}); st.rerun()
            except Exception as ex: st.error(f"Error loading goals: {ex}")

    # ── CALENDAR ──────────────────────────────────────────────────────────────
    with tab_calendar:
        import datetime as _cal_dt
        st.markdown('<div style="padding:18px 0 10px 0;margin-bottom:20px"><h3 style="color:#fbbf24;margin:0 0 4px 0">📅 Smart Calendar</h3><p style="color:#64748b;margin:0;font-size:0.88rem">Add events, get reminders, and let your Twin manage your schedule.</p></div>', unsafe_allow_html=True)
        cal_l, cal_r = st.columns([1, 1])
        with cal_l:
            st.markdown("#### ➕ Add Event")
            ev_title = st.text_input("Event title", placeholder="Team meeting", key="ev_title")
            ev_date  = st.date_input("Date", value=_cal_dt.date.today(), key="ev_date")
            ev_time  = st.time_input("Time", value=_cal_dt.time(9,0), key="ev_time")
            ev_desc  = st.text_area("Description (optional)", height=70, key="ev_desc")
            ev_color = st.color_picker("Color tag", value="#38bdf8", key="ev_color")
            if st.button("📅 Add Event", key="add_ev_btn", use_container_width=True):
                if ev_title.strip():
                    requests.post(f"{BACKEND_URL}/calendar/add", json={"user_id": st.session_state.email, "title": ev_title.strip(), "date": str(ev_date), "time": str(ev_time), "description": ev_desc, "color": ev_color})
                    st.success("✅ Event added!"); st.rerun()
                else: st.warning("Please enter an event title.")
        with cal_r:
            st.markdown("#### 🗓️ Upcoming Events")
            try:
                ev_list   = requests.get(f"{BACKEND_URL}/calendar/events", params={"user_id": st.session_state.email}, timeout=4).json().get("events",[])
                today_str = str(_cal_dt.date.today())
                upcoming  = [e for e in ev_list if e.get("date","") >= today_str]
                past      = [e for e in ev_list if e.get("date","") <  today_str]
                if not ev_list: st.info("No events yet.")
                else:
                    today_evs = [e for e in upcoming if e.get("date","") == today_str]
                    if today_evs:
                        st.markdown(f'<div style="background:rgba(251,191,36,0.12);border:1px solid rgba(251,191,36,0.3);border-radius:10px;padding:10px 14px;margin-bottom:12px"><span style="color:#fbbf24;font-weight:700">📌 Today — {_cal_dt.date.today().strftime("%d %b %Y")}</span></div>', unsafe_allow_html=True)
                        for ev in today_evs:
                            st.markdown(f'<div style="border-left:4px solid {ev.get("color","#38bdf8")};padding:8px 14px;margin-bottom:6px;background:rgba(255,255,255,0.04);border-radius:0 8px 8px 0"><span style="color:#e2e8f0;font-weight:600">{ev["title"]}</span><span style="color:#64748b;font-size:0.78rem;margin-left:8px">🕐 {ev.get("time","")}</span></div>', unsafe_allow_html=True)
                    if upcoming:
                        st.markdown("**⏭ Upcoming**")
                        for ev in upcoming[:15]:
                            ev_id = ev["_id"]
                            ev_date_fmt = _cal_dt.datetime.strptime(ev["date"],"%Y-%m-%d").strftime("%d %b %Y")
                            ec, dc = st.columns([0.85, 0.15])
                            with ec: st.markdown(f'<div style="border-left:4px solid {ev.get("color","#38bdf8")};padding:10px 14px;margin-bottom:6px;background:rgba(255,255,255,0.04);border-radius:0 10px 10px 0"><div style="color:#e2e8f0;font-weight:600">{ev["title"]}</div><div style="color:#64748b;font-size:0.75rem">📅 {ev_date_fmt}{" at "+ev.get("time","") if ev.get("time") else ""}</div>{"<div style=color:#94a3b8;font-size:0.78rem;margin-top:4px>"+ev["description"]+"</div>" if ev.get("description") else ""}</div>', unsafe_allow_html=True)
                            with dc:
                                if st.button("🗑️", key=f"del_ev_{ev_id}"):
                                    requests.delete(f"{BACKEND_URL}/calendar/event/{ev_id}", params={"user_id": st.session_state.email}); st.rerun()
                    if past:
                        with st.expander(f"📁 Past events ({len(past)})"):
                            for ev in past[-10:]:
                                ev_date_fmt = _cal_dt.datetime.strptime(ev["date"],"%Y-%m-%d").strftime("%d %b %Y")
                                st.markdown(f'<div style="border-left:3px solid rgba(100,116,139,0.5);padding:8px 12px;margin-bottom:4px;opacity:0.6"><span style="color:#94a3b8;font-size:0.85rem">{ev["title"]} — {ev_date_fmt}</span></div>', unsafe_allow_html=True)
            except Exception as ex: st.error(f"Error loading events: {ex}")

    # ── FEEDBACK PAGE REVAMPED ─────────────────────────────────────────────
    with tab_feedback:
        st.markdown(
"""<style>
.feedback-container-animate {
padding: 20px;
animation: fbFadeUp 0.6s ease-out;
font-family: 'DM Sans', sans-serif;
background: #0f172a;
min-height: 80vh;
}
@keyframes fbFadeUp {
from { opacity: 0; transform: translateY(20px); }
to { opacity: 1; transform: translateY(0); }
}
.feedback-layout {
display: flex;
gap: 40px;
max-width: 1250px;
margin: 0 auto;
align-items: stretch;
}
.testimonials-side { flex: 1.1; display: flex; flex-direction: column; }
.form-side { flex: 0.9; }
.feedback-heading {
font-size: 2.22rem;
font-weight: 800;
color: #f8fafc;
margin-bottom: 4px;
letter-spacing: -0.5px;
}
.feedback-subheading {
font-size: 0.96rem;
color: #94a3b8;
margin-bottom: 30px;
}
.testimonial-list {
display: flex;
flex-direction: column;
gap: 16px;
flex-grow: 1;
justify-content: space-between;
}
.testimonial-card {
background: rgba(13, 24, 41, 0.6);
border: 1px solid rgba(56, 189, 248, 0.15);
border-radius: 18px;
padding: 22px;
transition: all 0.3s ease;
}
.testimonial-card:hover {
border-color: rgba(56, 189, 248, 0.4);
box-shadow: 0 10px 30px rgba(0,0,0,0.3);
}
.testimonial-header {
display: flex;
align-items: center;
gap: 14px;
margin-bottom: 12px;
}
.avatar {
width: 44px;
height: 44px;
border-radius: 50%;
display: flex;
align-items: center;
justify-content: center;
font-weight: 700;
font-size: 1rem;
color: white;
}
.av-blue { background: #0284c7; }
.av-purple { background: #7c3aed; }
.av-teal { background: #0d9488; }
.av-orange { background: #d97706; }
.user-meta { display: flex; flex-direction: column; }
.user-name { color: #f1f5f9; font-weight: 700; font-size: 1rem; }
.user-title { color: #64748b; font-size: 0.82rem; }
.testimonial-stars {
color: #fbbf24;
font-size: 0.9rem;
margin-bottom: 10px;
letter-spacing: 2px;
}
.testimonial-stars {
color: #fbbf24;
font-size: 0.9rem;
margin-bottom: 10px;
letter-spacing: 2px;
}
.testimonial-txt {
color: #cbd5e1;
font-size: 0.92rem;
line-height: 1.5;
}
.feedback-form-card {
background: rgba(13, 24, 41, 0.8);
border: 1px solid rgba(56, 189, 248, 0.2);
border-radius: 20px;
padding: 35px;
box-shadow: 0 10px 40px rgba(0,0,0,0.4);
}
.form-title {
font-size: 1.5rem;
font-weight: 700;
color: #f8fafc;
margin-bottom: 6px;
}
.form-subtitle {
font-size: 0.88rem;
color: #94a3b8;
margin-bottom: 25px;
}
.group-fb {
margin-bottom: 20px;
}
.group-fb label {
display: block;
font-size: 0.7rem;
font-weight: 700;
color: #38bdf8;
margin-bottom: 8px;
text-transform: uppercase;
letter-spacing: 1px;
}
.group-fb input, .group-fb select, .group-fb textarea {
width: 100%;
background: #0f172a;
border: 1px solid rgba(56, 189, 248, 0.2);
border-radius: 10px;
padding: 12px 16px;
color: #f1f5f9;
font-size: 0.95rem;
box-sizing: border-box;
}
.group-fb input:focus, .group-fb select:focus, .group-fb textarea:focus {
outline: none;
border-color: #38bdf8;
}
.group-fb input::placeholder, .group-fb textarea::placeholder {
color: #334155;
}
.star-container {
display: flex;
gap: 8px;
}
.star-fb {
font-size: 1.5rem;
color: #1e293b;
cursor: pointer;
transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
user-select: none;
}
.star-fb:hover { transform: scale(1.3); }
.star-fb.active, .star-fb.hover-active { color: #fbbf24; text-shadow: 0 0 10px rgba(251, 191, 36, 0.3); }
.star-fb.active { color: #fbbf24; }
.submit-fb-btn {
width: 100%;
background: #0ea5e9;
color: white;
border: none;
border-radius: 10px;
padding: 14px;
font-size: 1rem;
font-weight: 700;
cursor: pointer;
margin-top: 10px;
transition: all 0.3s;
}
.submit-fb-btn:hover:not(:disabled) { background: #38bdf8; transform: translateY(-2px); }
.submit-fb-btn:disabled {
background: #1e293b;
color: #475569;
cursor: not-allowed;
opacity: 0.6;
}
#success-fb-overlay {
position: fixed; inset: 0; background: rgba(13, 24, 41, 0.95);
z-index: 10000; display: none; flex-direction: column; 
align-items: center; justify-content: center;
}
#success-fb-overlay.show { display: flex; }
.success-icon {
font-size: 4rem; color: #38bdf8; margin-bottom: 20px;
}
.success-title { font-size: 2rem; color: #f8fafc; margin-bottom: 10px; }
.success-msg { color: #94a3b8; text-align: center; max-width: 400px; margin-bottom: 30px;}
@media (max-width: 1000px) {
.feedback-layout { flex-direction: column; }
.form-side { position: static; width: 100%; }
}
</style>
<div class="feedback-container-animate">
<div class="feedback-layout">
<div class="testimonials-side">
<h1 class="feedback-heading">What Users Say About TwinX</h1>
<p class="feedback-subheading">Real feedback from people who've made it their personal AI twin.</p>
<div class="testimonial-list">
<div class="testimonial-card">
<div class="testimonial-header">
<div class="avatar av-blue">AR</div>
<div class="user-meta">
<span class="user-name">Aarav Rathore</span>
<span class="user-title">Full-Stack Developer · Bangalore</span>
</div>
</div>
<div class="testimonial-stars">★★★★★</div>
<div class="testimonial-txt">
"TwinX's Shadow Developer mode has saved me hours every week. It reviews my code in my own style, catches bugs I'd normally miss, and explains fixes clearly. It genuinely feels like pair programming with myself."
</div>
</div>
<div class="testimonial-card">
<div class="testimonial-header">
<div class="avatar av-purple">PS</div>
<div class="user-meta">
<span class="user-name">Priya Sharma</span>
<span class="user-title">Product Designer · Mumbai</span>
</div>
</div>
<div class="testimonial-stars">★★★★★</div>
<div class="testimonial-txt">
"The Style Mirror feature is actually brilliant. I uploaded my outfit before a client presentation and got detailed, personalized feedback based on my own taste profile. Nothing else does this."
</div>
</div>
<div class="testimonial-card">
<div class="testimonial-header">
<div class="avatar av-teal">MK</div>
<div class="user-meta">
<span class="user-name">Mohammed K.</span>
<span class="user-title">Startup Founder · Dubai</span>
</div>
</div>
<div class="testimonial-stars">★★★★★</div>
<div class="testimonial-txt">
"My Feed gives me a morning briefing tuned exactly to my tech stack and city. I stopped doom-scrolling Twitter. TwinX just tells me what matters — nothing more, nothing less."
</div>
</div>
<div class="testimonial-card">
<div class="testimonial-header">
<div class="avatar av-orange">SL</div>
<div class="user-meta">
<span class="user-name">Samantha Liu</span>
<span class="user-title">Data Scientist · Singapore</span>
</div>
</div>
<div class="testimonial-stars">★★★★★</div>
<div class="testimonial-txt">
"The Analytics section is a game-changer. It shows me exactly where I'm spending my time and how my Twin is learning from me. It's like having a mirror for my digital life."
</div>
</div>
</div>
</div>
<div class="form-side">
<div class="feedback-form-card">
<h2 class="form-title">Share Your Experience</h2>
<p class="form-subtitle">Your feedback helps make TwinX smarter for everyone.</p>
<form id="revamped-fb-form">
<div class="group-fb">
<label>YOUR NAME</label>
<input type="text" id="fb-in-name" placeholder="Alex Sharma" required>
</div>
<div class="group-fb">
<label>EMAIL</label>
<input type="email" id="fb-in-email" placeholder="you@example.com" required>
</div>

<div class="group-fb">
<label>DESIGNATION <span style="color:#334155; font-weight:400; text-transform:none; letter-spacing:0; margin-left:4px;">(optional)</span></label>
<select id="fb-in-designation">
<option value="" disabled selected>Select your role...</option>
<option value="Student">Student</option>
<option value="Working Professional">Working Professional</option>
<option value="Freelancer">Freelancer</option>
<option value="Startup Founder">Startup Founder</option>
<option value="Entrepreneur">Entrepreneur</option>
<option value="Hobbyist">Hobbyist</option>
<option value="Others">Others</option>
</select>
</div>

<div class="group-fb">
<label>YOUR LOCATION <span style="color:#334155; font-weight:400; text-transform:none; letter-spacing:0; margin-left:4px;">(optional)</span></label>
<select id="fb-in-location">
<option value="" disabled selected>Select your city...</option>
<option value="Bangalore">Bangalore</option>
<option value="Mumbai">Mumbai</option>
<option value="Delhi NCR">Delhi NCR</option>
<option value="Hyderabad">Hyderabad</option>
<option value="Pune">Pune</option>
<option value="New York">New York</option>
<option value="London">London</option>
<option value="Singapore">Singapore</option>
<option value="Dubai">Dubai</option>
<option value="Others">Others</option>
</select>
</div>
<div class="group-fb">
<label>FEATURE YOU'RE REVIEWING</label>
<select id="fb-in-feature" required>
<option value="" disabled selected>Select a feature...</option>
<option value="Conversation">Conversation (Chat)</option>
<option value="Think Space">Think Space (Brain)</option>
<option value="Shadow Developer">Shadow Developer (Code)</option>
<option value="Style Mirror">Style Mirror (Fashion)</option>
<option value="My Feed">My Feed (Newsroom)</option>
<option value="Analytics">Analytics & Insights</option>
<option value="Goals">Goals & Habits</option>
<option value="Calendar">Smart Calendar</option>
</select>
</div>
<div class="group-fb">
<label>YOUR RATING</label>
<div class="star-container" id="star-box">
<span class="star-fb" data-v="1">★</span>
<span class="star-fb" data-v="2">★</span>
<span class="star-fb" data-v="3">★</span>
<span class="star-fb" data-v="4">★</span>
<span class="star-fb" data-v="5">★</span>
</div>
<input type="hidden" id="fb-in-rating" value="0">
</div>
<div class="group-fb">
<label>YOUR FEEDBACK</label>
<textarea id="fb-in-msg" rows="4" placeholder="Tell us what you think — what's working, what could be better..." required></textarea>
</div>
<button type="submit" class="submit-fb-btn" id="fb-in-submit" disabled>Submit Feedback</button>
<div id="fb-success-inline" style="display:none; color:#10b981; font-weight:700; font-size:0.95rem; text-align:center; padding:15px; border:1px solid rgba(16,185,129,0.3); background:rgba(16,185,129,0.08); border-radius:12px; margin-top:20px; animation: fbFadeUp 0.4s ease;">
Thank you! Your feedback has been successfully submitted to the TwinX team. ✅
</div>
</form>
</div>
</div>
</div>
</div>
""", unsafe_allow_html=True)

        components.html(
"""<script>
(function() {
const doc = window.parent.document;
setTimeout(() => {
const stars = doc.querySelectorAll('.star-fb');
const rInput = doc.getElementById('fb-in-rating');
const form = doc.getElementById('revamped-fb-form');
const submit = doc.getElementById('fb-in-submit');
const overlay = doc.getElementById('success-fb-overlay');
if (!form) return;
stars.forEach(s => {
s.addEventListener('click', () => {
const v = s.getAttribute('data-v');
rInput.value = v;
stars.forEach(st => {
if(parseInt(st.getAttribute('data-v')) <= parseInt(v)) st.classList.add('active');
else st.classList.remove('active');
});
checkForm();
});
s.addEventListener('mouseover', () => {
const v = s.getAttribute('data-v');
stars.forEach(st => {
if(parseInt(st.getAttribute('data-v')) <= parseInt(v)) st.classList.add('hover-active');
else st.classList.remove('hover-active');
});
});
s.addEventListener('mouseout', () => {
stars.forEach(st => st.classList.remove('hover-active'));
});
});

function checkForm() {
const valName = doc.getElementById('fb-in-name').value.trim();
const valEmail = doc.getElementById('fb-in-email').value.trim();
const valFeature = doc.getElementById('fb-in-feature').value;
const valRating = rInput.value;
const isReady = (valName !== "" && valEmail !== "" && valFeature !== "" && parseInt(valRating) > 0);
submit.disabled = !isReady;
}

['fb-in-name', 'fb-in-email', 'fb-in-feature'].forEach(id => {
doc.getElementById(id).addEventListener('input', checkForm);
doc.getElementById(id).addEventListener('change', checkForm);
});
checkForm();
form.addEventListener('submit', async (e) => {
e.preventDefault();
const name = doc.getElementById('fb-in-name').value;
const email = doc.getElementById('fb-in-email').value;
const feature = doc.getElementById('fb-in-feature').value;
const rating = rInput.value;
const msg = doc.getElementById('fb-in-msg').value;
const designation = doc.getElementById('fb-in-designation').value;
const location = doc.getElementById('fb-in-location').value;

submit.disabled = true;
submit.innerText = 'Sending...';
try {
await fetch("https://formsubmit.co/ajax/twinx.techai@gmail.com", {
method: 'POST',
headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
body: JSON.stringify({
_subject: `Feedback: ${feature} (${rating} stars) from ${name}`,
Name: name, Email: email, Designation: designation, Location: location, Feature: feature, Rating: rating, Message: msg
})
});
form.reset();
stars.forEach(st => st.classList.remove('active'));
const sm = doc.getElementById('fb-success-inline');
if(sm) {
sm.style.display = 'block';
setTimeout(() => { sm.style.display = 'none'; }, 6000);
}
} catch(err) {
alert("Error sending feedback.");
} finally {
submit.disabled = false;
submit.innerText = 'Submit Feedback';
}
});
}, 500);
})();
</script>""", height=0)