with open(r"c:\Users\Nirmit\Desktop\ADT Backup\frontend\app.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

new_block = r"""        chip_prompt = None
        if st.session_state.get("chip_inject"):
            chip_prompt = st.session_state.pop("chip_inject")
            
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

        # ── STOP BUTTON: hidden Streamlit trigger (invisible) + floating overlay via JS/CSS ──
        _stop_clicked = st.button("■ Stop", key="_stop_twin_btn", help="Stop the twin's response")
        if _stop_clicked:
            st.session_state["twin_stop_requested"] = True
            st.rerun()
        st.markdown('''
        <button id="twin-stop-btn" title="Stop response" aria-label="Stop response">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                <rect x="5" y="5" width="14" height="14" rx="2"/>
            </svg>
        </button>
        <style>
        /* Hide the real Streamlit stop button — we use the floating overlay */
        [data-testid="stButton"]:has(button p) button p { font-size: 0; }
        </style>
        <script>
        (function() {
            const stopBtn = document.getElementById('twin-stop-btn');
            if (!stopBtn) return;
            const observer = new MutationObserver(function() {
                const spinner = document.querySelector('[data-testid="stSpinner"]');
                if (spinner) {
                    stopBtn.classList.add('active');
                } else {
                    stopBtn.classList.remove('active');
                }
            });
            observer.observe(document.body, { childList: true, subtree: true });
            stopBtn.addEventListener('click', function() {
                if (!stopBtn.classList.contains('active')) return;
                const allBtns = document.querySelectorAll('button');
                for (const btn of allBtns) {
                    if (btn.innerText && btn.innerText.trim() === '\\u25a0 Stop') {
                        btn.click();
                        break;
                    }
                }
                stopBtn.classList.remove('active');
            });
        })();
        </script>
        ''', unsafe_allow_html=True)

        text_prompt = st.chat_input("Don't Google it. Ask Me")
        prompt = chip_prompt if chip_prompt else (text_prompt or voice_prompt)
        if st.session_state.get("suppress_next_prompt", False):
            st.session_state["suppress_next_prompt"] = False
            prompt = None
        if st.session_state.pop("twin_stop_requested", False):
            prompt = None
"""

lines = lines[:1603] + [new_block + "\n"] + lines[1698:]

with open(r"c:\Users\Nirmit\Desktop\ADT Backup\frontend\app.py", "w", encoding="utf-8") as f:
    f.writelines(lines)
