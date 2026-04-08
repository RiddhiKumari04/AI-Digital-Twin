# server.py — Explicit root entry point
import os
import sys
from dotenv import load_dotenv
                                                                                                                                                                                                                                                                                                                                                                                    
# 1. Load environment variables from ROOT .env
load_dotenv()

# 2. Map 'app/backend' to the Python path so internal imports work
_app_backend = os.path.join(os.path.dirname(__file__), "app", "backend")
if os.path.isdir(_app_backend):
    sys.path.insert(0, _app_backend)

# 3. Import the actual FastAPI app object from the modularized backend
import main
app = main.app

if __name__ == "__main__":
    import uvicorn
    # Test locally with: python server.py
    uvicorn.run(app, host="0.0.0.0", port=8000)
