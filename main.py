# Root entry point shim for deployment compatibility (e.g. Render)
import os
import sys

# Ensure backend directory is in Python path for modular imports
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

# Import the actual FastAPI app object from the backend submodule
from main import app

if __name__ == "__main__":
    import uvicorn
    # When running from root, uvicorn needs to find the module relative to sys.path
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
