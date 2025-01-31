#!/usr/bin/env python3
"""Development server script for Parallama."""

import os
import sys
import uvicorn

# Add src directory to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_path = os.path.join(project_root, "src")
sys.path.insert(0, src_path)

# Set development config path
os.environ["PARALLAMA_CONFIG"] = os.path.join(
    project_root, "config", "config.dev.yaml"
)

if __name__ == "__main__":
    uvicorn.run(
        "parallama.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="debug"
    )
