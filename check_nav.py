file = r"c:\Users\Nirmit\Desktop\AI Digital Twin\frontend\app.py"
with open(file, "r", encoding="utf-8") as f:
    content = f.read()

checks = {
    "with tab_chat": "with tab_chat:" in content,
    "with tab_brain": "with tab_brain:" in content,
    "with tab_shadow": "with tab_shadow:" in content,
    "with tab_mirror": "with tab_mirror:" in content,
    "with tab_news": "with tab_news:" in content,
    "with tab_analytics": "with tab_analytics:" in content,
    "with tab_goals": "with tab_goals:" in content,
    "with tab_calendar": "with tab_calendar:" in content,
    "if _active chat": 'if _active == "chat":' in content,
    "if _active brain": 'if _active == "brain":' in content,
    "if _active shadow": 'if _active == "shadow":' in content,
    "if _active mirror": 'if _active == "mirror":' in content,
    "if _active news": 'if _active == "news":' in content,
    "if _active analytics": 'if _active == "analytics":' in content,
    "if _active goals": 'if _active == "goals":' in content,
    "if _active calendar": 'if _active == "calendar":' in content,
    "st.tabs found": "st.tabs(" in content,
    "navGoTo found": "navGoTo" in content,
    "navTo found": "navTo(" in content,
    "active_tab init": 'if "active_tab" not in st.session_state' in content,
    "_inject_nav_menu(active_tab": "_inject_nav_menu(active_tab=" in content,
}

for k, v in checks.items():
    print(f"  {k}: {v}")
