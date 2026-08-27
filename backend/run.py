"""
Single-command launcher for magicpin Vera AI backend.
"""

import os
import uvicorn

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "false").lower() == "true"

    print(f"Starting magicpin Vera AI service on http://{host}:{port}")
    uvicorn.run("app.main:app", host=host, port=port, reload=reload)
