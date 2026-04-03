import re

file = r"c:\Users\Nirmit\Desktop\AI Digital Twin\frontend\app.py"
with open(file, "r", encoding="utf-8") as f:
    content = f.read()

print(f"Original size: {len(content)}")

# ── 1. Replace _inject_nav_menu function ─────────────────────────────────────
old_nav_start = "# ── RIGHT-SIDE FLOATING NAV MENU ─────────────────────────────────────────────\ndef _inject_nav_menu():"
new_nav_start = "# ── RIGHT-SIDE FLOATING NAV MENU ─────────────────────────────────────────────\ndef _inject_nav_menu(active_tab=\"chat\"):"

if old_nav_start in content:
    content = content.replace(old_nav_start, new_nav_start, 1)
    print("✓ Replaced _inject_nav_menu signature")
else:
    print("✗ Could not find _inject_nav_menu signature")

# Replace the navGoTo JS function with navTo URL-param approach
old_js = '''  function navGoTo(idx){{
    closeNav();
    try{{
      var tabs=document.querySelectorAll('[data-testid="stTabs"] [role="tab"]');
      if(tabs&&tabs[idx]){{
        tabs[idx].click();
        document.querySelectorAll('#twin-nav-panel .nav-item').forEach(function(b,i){{
          b.classList.toggle('active',i===idx);
        }});
      }}
    }}catch(e){{console.error('navGoTo:',e);}}
  }}
  window.toggleNav=toggleNav;
  window.closeNav=closeNav;
  window.navGoTo=navGoTo;
  // Auto-sync active highlight when user clicks tabs directly
  var obs=new MutationObserver(function(){{
    try{{
      document.querySelectorAll('[data-testid="stTabs"] [role="tab"]').forEach(function(tab,i){{
        if(tab.getAttribute('aria-selected')==='true'){{
          document.querySelectorAll('#twin-nav-panel .nav-item').forEach(function(b,j){{
            b.classList.toggle('active',i===j);
          }});
        }}
      }});
    }}catch(e){{}}
  }});
  var tryObs=setInterval(function(){{
    var tl=document.querySelector('[data-testid="stTabs"]');
    if(tl){{obs.observe(tl,{{attributes:true,subtree:true}});clearInterval(tryObs);}}
  }},500);'''

new_js = '''  function navTo(key){{
    closeNav();
    try{{
      var params=new URLSearchParams();
      params.set('_nav', key);
      var url='?'+params.toString();
      var p=window.parent.document;
      var s=p.createElement('script');
      s.textContent='location.assign('+JSON.stringify(url)+');';
      p.head.appendChild(s);
      p.head.removeChild(s);
    }}catch(e){{console.error('navTo:',e);}}
  }}
  window.toggleNav=toggleNav;
  window.closeNav=closeNav;
  window.navTo=navTo;'''

if old_js in content:
    content = content.replace(old_js, new_js, 1)
    print("✓ Replaced navGoTo JS with navTo URL-param approach")
else:
    print("✗ Could not find navGoTo JS block")

# Replace nav_items list and btns generation
old_nav_items = '''    nav_items = [
        ("💬", "Conversation",     0),
        ("🧠", "Brain Explorer",   1),
        ("👾", "Shadow Developer", 2),
        ("🪞", "Style Mirror",     3),
        ("📰", "Twin Newsroom",    4),
        ("📊", "Analytics",        5),
        ("🎯", "Goals",            6),
        ("📅", "Calendar",         7),
    ]
    btns = "".join(
        f\'<button class="nav-item" onclick="navGoTo({idx})" data-idx="{idx}">\'
        f\'<span class="nav-icon">{icon}</span>{label}</button>\'
        for icon, label, idx in nav_items
    )'''

new_nav_items = '''    nav_items = [
        ("chat",      "💬", "Conversation"),
        ("brain",     "🧠", "Brain Explorer"),
        ("shadow",    "👾", "Shadow Developer"),
        ("mirror",    "🪞", "Style Mirror"),
        ("news",      "📰", "Twin Newsroom"),
        ("analytics", "📊", "Analytics"),
        ("goals",     "🎯", "Goals"),
        ("calendar",  "📅", "Calendar"),
    ]
    btns = "".join(
        f\'<button class="nav-item{" active" if key == active_tab else ""}" onclick="navTo(\\'{key}\\')">\'
        f\'<span class="nav-icon">{icon}</span>{label}</button>\'
        for key, icon, label in nav_items
    )'''

if old_nav_items in content:
    content = content.replace(old_nav_items, new_nav_items, 1)
    print("✓ Replaced nav_items list")
else:
    print("✗ Could not find nav_items list")

# ── 2. Replace LOGGED-IN APP block ──────────────────────────────────────────
old_logged_in = """    _goto_shadow = st.session_state.pop(\"goto_shadow\", False)
    st.title(f\"🧠 {st.session_state.name}'s Twin\")
    _inject_nav_menu()  # ── floating right-side nav menu
    tab_chat, tab_brain, tab_shadow, tab_mirror, tab_news, tab_analytics, tab_goals, tab_calendar = st.tabs([
        \"💬 CONVERSATION\", \"🧠 BRAIN EXPLORER\", \"👾 SHADOW DEVELOPER\",
        \"🪞 STYLE MIRROR\", \"📰 TWIN NEWSROOM\", \"📊 ANALYTICS\", \"🎯 GOALS\", \"📅 CALENDAR\"
    ])
    if _goto_shadow:
        st.info(\"👾 Head to the **SHADOW DEVELOPER** tab to review your code!\")

    # ── CONVERSATION ─────────────────────────────────────────────────────────
    with tab_chat:"""

new_logged_in = """    # Handle goto_shadow flag
    _goto_shadow = st.session_state.pop(\"goto_shadow\", False)
    if _goto_shadow:
        st.session_state[\"active_tab\"] = \"shadow\"

    # Init active tab
    if \"active_tab\" not in st.session_state:
        st.session_state[\"active_tab\"] = \"chat\"

    # Handle _nav query param set by floating menu
    _valid_tabs = [\"chat\",\"brain\",\"shadow\",\"mirror\",\"news\",\"analytics\",\"goals\",\"calendar\"]
    _nav_qp = st.query_params.get(\"_nav\", \"\")
    if _nav_qp and _nav_qp in _valid_tabs:
        st.session_state[\"active_tab\"] = _nav_qp
        st.query_params.clear()
        st.rerun()

    _active = st.session_state[\"active_tab\"]

    st.title(f\"🧠 {st.session_state.name}'s Twin\")
    _inject_nav_menu(active_tab=_active)  # ── floating right-side nav menu

    # ── CONVERSATION ─────────────────────────────────────────────────────────
    if _active == \"chat\":"""

if old_logged_in in content:
    content = content.replace(old_logged_in, new_logged_in, 1)
    print("✓ Replaced LOGGED-IN APP block header")
else:
    print("✗ Could not find LOGGED-IN APP block header")
    # Try to find partial
    snippet = '    tab_chat, tab_brain, tab_shadow'
    if snippet in content:
        print(f"  Found partial: '{snippet}'")

# ── 3. Replace remaining with tab_X: blocks ─────────────────────────────────
replacements = [
    ("    # ── BRAIN EXPLORER ────────────────────────────────────────────────────────\r\n    with tab_brain:",
     "    # ── BRAIN EXPLORER ────────────────────────────────────────────────────────\r\n    if _active == \"brain\":"),
    ("    # ── SHADOW DEVELOPER ─────────────────────────────────────────────────────\r\n    with tab_shadow:",
     "    # ── SHADOW DEVELOPER ─────────────────────────────────────────────────────\r\n    if _active == \"shadow\":"),
    ("    # ── STYLE MIRROR ─────────────────────────────────────────────────────────\r\n    with tab_mirror:",
     "    # ── STYLE MIRROR ─────────────────────────────────────────────────────────\r\n    if _active == \"mirror\":"),
    ("    # ── TWIN NEWSROOM ─────────────────────────────────────────────────────────\r\n    with tab_news:",
     "    # ── TWIN NEWSROOM ─────────────────────────────────────────────────────────\r\n    if _active == \"news\":"),
    ("    # ── ANALYTICS ─────────────────────────────────────────────────────────────\r\n    with tab_analytics:",
     "    # ── ANALYTICS ─────────────────────────────────────────────────────────────\r\n    if _active == \"analytics\":"),
    ("    # ── GOALS ─────────────────────────────────────────────────────────────────\r\n    with tab_goals:",
     "    # ── GOALS ─────────────────────────────────────────────────────────────────\r\n    if _active == \"goals\":"),
    ("    # ── CALENDAR ──────────────────────────────────────────────────────────────\r\n    with tab_calendar:",
     "    # ── CALENDAR ──────────────────────────────────────────────────────────────\r\n    if _active == \"calendar\":"),
]

for old, new in replacements:
    if old in content:
        content = content.replace(old, new, 1)
        tab_name = old.split("with tab_")[1].split(":")[0] if "with tab_" in old else "brain/shadow/etc"
        print(f"✓ Replaced 'with tab_{tab_name}'")
    else:
        # Try LF-only line endings
        old_lf = old.replace("\r\n", "\n")
        if old_lf in content:
            content = content.replace(old_lf, new.replace("\r\n", "\n"), 1)
            tab_name = old.split("with tab_")[1].split(":")[0] if "with tab_" in old else "?"
            print(f"✓ Replaced 'with tab_{tab_name}' (LF)")
        else:
            print(f"✗ Could not find: {old[:60]!r}")

with open(file, "w", encoding="utf-8") as f:
    f.write(content)

print(f"\nDone. New file size: {len(content)}")
