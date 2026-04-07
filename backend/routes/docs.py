"""
routes/docs.py — Custom, branded API Documentation page.
Provides a premium, visual overview of all TwinX API endpoints.
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TwinX API Documentation</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=JetBrains+Mono&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #030712;
            --glass: rgba(17, 24, 39, 0.7);
            --accent: #38bdf8;
            --accent-glow: rgba(56, 189, 248, 0.3);
            --text: #f8fafc;
            --text-dim: #94a3b8;
            --border: rgba(255, 255, 255, 0.1);
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background-color: var(--bg);
            color: var(--text);
            font-family: 'Outfit', sans-serif;
            line-height: 1.6;
            overflow-x: hidden;
        }

        /* Animated Background Gradient */
        .bg-glow {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: -1;
            background: radial-gradient(circle at 20% 20%, rgba(56, 189, 248, 0.15) 0%, transparent 40%),
                        radial-gradient(circle at 80% 80%, rgba(139, 92, 246, 0.15) 0%, transparent 40%);
        }

        .container { max-width: 1100px; margin: 0 auto; padding: 40px 20px; }

        header { text-align: center; margin-bottom: 60px; }
        header h1 { font-size: 3.5rem; font-weight: 800; letter-spacing: -1px; margin-bottom: 10px; background: linear-gradient(to right, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        header p { color: var(--text-dim); font-size: 1.2rem; max-width: 600px; margin: 0 auto; }

        .section { margin-bottom: 50px; }
        .section-title { font-size: 1.8rem; font-weight: 600; margin-bottom: 25px; border-left: 4px solid var(--accent); padding-left: 15px; color: var(--accent); }

        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px; }

        .card {
            background: var(--glass);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 24px;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        .card:hover { transform: translateY(-5px); border-color: rgba(56, 189, 248, 0.4); box-shadow: 0 10px 30px -10px var(--accent-glow); }

        .method { font-family: 'JetBrains+Mono', monospace; font-size: 0.8rem; font-weight: 800; padding: 4px 10px; border-radius: 6px; margin-right: 8px; text-transform: uppercase; }
        .get { background: rgba(52, 211, 153, 0.2); color: #34d399; }
        .post { background: rgba(56, 189, 248, 0.2); color: #38bdf8; }
        .delete { background: rgba(248, 113, 113, 0.2); color: #f87171; }

        .endpoint { font-family: 'JetBrains+Mono', monospace; font-size: 0.95rem; font-weight: 600; color: #e2e8f0; word-break: break-all; }
        .desc { margin-top: 12px; color: var(--text-dim); font-size: 0.9rem; }

        .params { margin-top: 15px; background: rgba(0, 0, 0, 0.2); border-radius: 10px; padding: 12px; font-family: 'JetBrains+Mono', monospace; font-size: 0.8rem; }
        .params-title { color: var(--text-dim); font-weight: 600; margin-bottom: 5px; font-size: 0.75rem; text-transform: uppercase; }

        footer { text-align: center; margin-top: 40px; color: var(--text-dim); font-size: 0.9rem; border-top: 1px solid var(--border); padding-top: 30px; }

        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .card { animation: fadeIn 0.5s ease backwards; }
        .card:nth-child(1) { animation-delay: 0.1s; }
        .card:nth-child(2) { animation-delay: 0.15s; }
        .card:nth-child(3) { animation-delay: 0.2s; }
    </style>
</head>
<body>
    <div class="bg-glow"></div>
    <div class="container">
        <header>
            <h1>TwinX API Docs</h1>
            <p>A premium gateway to your AI Digital Twin. Explore the neural network endpoints.</p>
        </header>

        <!-- Authentication -->
        <div class="section">
            <h2 class="section-title">Authentication</h2>
            <div class="grid">
                <div class="card">
                    <span class="method post">POST</span><span class="endpoint">/register</span>
                    <p class="desc">Create a new user account.</p>
                    <div class="params"><div class="params-title">Payload</div>{ "name", "email", "password" }</div>
                </div>
                <div class="card">
                    <span class="method get">GET</span><span class="endpoint">/login</span>
                    <p class="desc">Authenticate existing user.</p>
                    <div class="params"><div class="params-title">Params</div>email, password</div>
                </div>
                <div class="card">
                    <span class="method post">POST</span><span class="endpoint">/forgot_password/send_otp</span>
                    <p class="desc">Request password reset OTP.</p>
                </div>
            </div>
        </div>

        <!-- Digital Twin Core -->
        <div class="section">
            <h2 class="section-title">Digital Twin Core</h2>
            <div class="grid">
                <div class="card">
                    <span class="method get">GET</span><span class="endpoint">/ask</span>
                    <p class="desc">Query your digital twin (standard response).</p>
                    <div class="params"><div class="params-title">Params</div>user_id, question, mood</div>
                </div>
                <div class="card">
                    <span class="method get">GET</span><span class="endpoint">/ask_stream</span>
                    <p class="desc">Query digital twin with streaming SSE.</p>
                </div>
                <div class="card">
                    <span class="method post">POST</span><span class="endpoint">/style_mirror</span>
                    <p class="desc">Visual fashion grading via Gemini Vision.</p>
                </div>
            </div>
        </div>

        <!-- Shadow Developer -->
        <div class="section">
            <h2 class="section-title">Shadow Developer</h2>
            <div class="grid">
                <div class="card">
                    <span class="method post">POST</span><span class="endpoint">/debug_code</span>
                    <p class="desc">Advanced AI debugging with syntax checks & diffs.</p>
                </div>
                <div class="card">
                    <span class="method get">GET</span><span class="endpoint">/repo_files</span>
                    <p class="desc">Browse local repos or clone GitHub via URL.</p>
                </div>
            </div>
        </div>

        <!-- System & Health -->
        <div class="section">
            <h2 class="section-title">System & Health</h2>
            <div class="grid">
                <div class="card">
                    <span class="method get">GET</span><span class="endpoint">/health</span>
                    <p class="desc">Comprehensive service status (DB, AI, Email).</p>
                </div>
                <div class="card">
                    <span class="method get">GET</span><span class="endpoint">/status</span>
                    <p class="desc">Simplified system liveness check.</p>
                </div>
            </div>
        </div>

        <footer>
            <p>&copy; 2026 AI Digital Twin Project &bull; Built with FastAPI & Sonnet</p>
        </footer>
    </div>
</body>
</html>
"""

@router.get("/api-docs", response_class=HTMLResponse)
async def api_docs():
    """Serves the custom TwinX API documentation page."""
    return HTML_CONTENT
