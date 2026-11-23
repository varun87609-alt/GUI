"""Convenience runner script for starting the FastAPI backend server."""

import sys
import uvicorn
from pathlib import Path

# Ensure root directory is on sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app.config import settings

def main():
    print(f"Starting OpenFOAM Meshing Backend on http://{settings.app_host}:{settings.app_port}")
    uvicorn.run(
        "backend.app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=False,
        log_level="info",
    )

if __name__ == "__main__":
    main()
