#!/usr/bin/env python3
"""
SkillScope Unified Backend Launcher
Starts 5 backends simultaneously:
- Login Backend (8182)
- Agent Runtime (8003)
- Skill Backend (8000)
- Interview Backend (8188)
- Recommendation Engine (8001)
"""
import subprocess
import sys
import time
import os
from pathlib import Path
import signal

project_root = Path(__file__).parent
login_path = project_root / "login"
agent_path = project_root / "Agent-Runtime"
nipuni_path = project_root / "Nipuni_backend"
nilmani_path = project_root / "Nilmani-backend"
recommendation_path = project_root / "Advanced-Recommendation-System"
thisaravi_path = project_root / "Thisaravi-Backend"

processes = []


def start_uvicorn_service(
    name,
    module,
    cwd,
    port,
    extra_args=None,
    env=None,
    reload=True,
    reload_excludes=None,
):
    print(f"Launching {name} (port {port})...")
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        module,
        "--host",
        "0.0.0.0",
        "--port",
        str(port),
    ]
    if reload:
        cmd.append("--reload")
        for pattern in reload_excludes or []:
            cmd.extend(["--reload-exclude", pattern])
    if extra_args:
        cmd.extend(extra_args)
    proc = subprocess.Popen(cmd, cwd=str(cwd), env=env)
    processes.append((name, proc))
    time.sleep(3)
    return proc

def signal_handler(sig, frame):
    print("\n\nShutting down backends...")
    for _, proc in processes:
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
    print("All services stopped")
    sys.exit(0)

def start_backends():
    print(""" 
==============================================================================
                SKILLSCOPE UNIFIED BACKEND LAUNCHER
              Starting 6 services simultaneously

 * Config Server (Dynamic Config)    ->  http://localhost:8099
 * Login Backend (OAuth, JWT)        ->  http://localhost:8182
 * Agent Runtime (CV Processing)     ->  http://localhost:8003
 * Skill Backend (Transcripts)       ->  http://localhost:8000
 * Interview Backend (Nilmani)       ->  http://localhost:8188
 * Recommendation Engine (Advanced)  ->  http://localhost:8001

 Ctrl+C to stop all services
==============================================================================
    """)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    print("\nStarting services...\n")
    
    # Start Config Server without reload so OneDrive / .venv events do not
    # tear down the whole launcher.
    start_uvicorn_service("Config Server", "config_server:app", project_root, 8099, reload=False)
    
    # Start Login Backend (port 8182)
    start_uvicorn_service(
        "Login Backend",
        "app.main:app",
        login_path,
        8182,
        reload_excludes=[".venv", ".venv/**", "**/.venv/**"],
    )
    
    # Start Agent Runtime (port 8003)
    start_uvicorn_service(
        "Agent Runtime",
        "main:app",
        agent_path,
        8003,
        reload_excludes=[".venv", ".venv/**", "**/.venv/**"],
    )
    
    # Start Nipuni Backend (port 8000)
    start_uvicorn_service(
        "Skill Backend",
        "src.app.main:app",
        nipuni_path,
        8000,
        reload_excludes=[".venv", ".venv/**", "**/.venv/**"],
    )
    
    # Start Nilmani Backend (port 8188)
    start_uvicorn_service(
        "Interview Backend - Nilmani",
        "app.main:app",
        nilmani_path,
        8188,
        reload_excludes=[".venv", ".venv/**", "**/.venv/**"],
    )
    
    # Start Recommendation Engine (port 8001)
    start_uvicorn_service(
        "Recommendation Engine",
        "main:app",
        recommendation_path,
        8001,
        reload_excludes=[".venv", ".venv/**", "**/.venv/**"],
    )
    
    # Thisaravi is intentionally disabled until its import issue is fixed.
    # Set ENABLE_THISARAVI=1 to opt in when the backend is ready.
    if os.getenv("ENABLE_THISARAVI") == "1":
        start_uvicorn_service(
            "Thisaravi Backend - Skill Gap AI",
            "main:app",
            thisaravi_path,
            8010,
            env={**os.environ, "PORT": "8010"},
            reload_excludes=[".venv", ".venv/**", "**/.venv/**"],
        )
    
    print("\n" + "="*80)
    print("OK - ALL 6 SERVICES RUNNING")
    print("="*80)
    print("""
CONFIG SERVER (port 8099) - Dynamic Configuration
   Config: http://localhost:8099/config
   Health: http://localhost:8099/health

LOGIN BACKEND (port 8182)
   Docs: http://localhost:8182/docs
   Health: http://localhost:8182/auth/health

AGENT RUNTIME (port 8003)
    Docs: http://localhost:8003/docs
    Health: http://localhost:8003/health

SKILL BACKEND (port 8000)
   Docs: http://localhost:8000/docs
   Health: http://localhost:8000/health

INTERVIEW BACKEND - Nilmani (port 8188)
   Docs: http://localhost:8188/docs
   Health: http://localhost:8188/health

RECOMMENDATION ENGINE - Advanced (port 8001)
   Docs: http://localhost:8001/docs
   Health: http://localhost:8001/health

THISARAVI BACKEND - Skill Gap AI (port 8010)
   Docs: http://localhost:8010/docs
   Health: http://localhost:8010/health

Stop: Ctrl+C
""")
    print("="*80 + "\n")
    
    try:
        while True:
            for name, proc in processes:
                if proc and proc.poll() is not None:
                    print(f"⚠️ Service exited: {name}")
                    signal_handler(None, None)
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == "__main__":
    if not login_path.exists() or not agent_path.exists() or not nipuni_path.exists() or not nilmani_path.exists() or not recommendation_path.exists() or not thisaravi_path.exists():
        print("ERROR - Backend paths not found")
        sys.exit(1)
    start_backends()
