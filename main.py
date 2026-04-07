# Root entry point shim for deployment compatibility (e.g. Render)
import os
import sys

# Ensure app/backend directory is in Python path for modular imports
_app_backend = os.path.join(os.path.dirname(__file__), "app", "backend")
_backend_fallback = os.path.join(os.path.dirname(__file__), "backend")

# Prefer app/backend, fall back to backend/ for compatibility
if os.path.isdir(_app_backend):
    sys.path.insert(0, _app_backend)
else:
    sys.path.insert(0, _backend_fallback)

# Import the actual FastAPI app object
from main import app  # noqa: E402

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
