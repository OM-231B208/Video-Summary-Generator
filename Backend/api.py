from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uuid
import shutil
import os
import sys
import io
import tempfile

if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from pydantic import BaseModel
from fastapi import Depends, HTTPException
from .auth import SessionLocal, create_user, get_user_by_username, verify_password

from .core_worker import process_job, JOB_STATUS, CANCEL_FLAGS

# -------------------------------------------------
# Detect running port → choose summarizer mode
# Port 8000 → Local models (BART / PEGASUS) + Gemini (multimodal LLM)
# -------------------------------------------------
def _detect_port() -> int:
    for i, arg in enumerate(sys.argv):
        if arg == "--port" and i + 1 < len(sys.argv):
            try:
                return int(sys.argv[i + 1])
            except ValueError:
                pass
        if arg.startswith("--port="):
            try:
                return int(arg.split("=", 1)[1])
            except ValueError:
                pass
    return 8000  # default fallback

BACKEND_PORT = _detect_port()
BACKEND_MODE = "gemini" if BACKEND_PORT == 8001 else "local"

print(f"[API] ✅ Running on port {BACKEND_PORT} → Mode: {'🤖 Gemini LLM' if BACKEND_MODE == 'gemini' else '🧠 Local Models (BART/PEGASUS)'}")

# DB Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class UserAuth(BaseModel):
    username: str
    password: str

class UserRegister(BaseModel):
    username: str
    email: str
    password: str


# -------------------------------------------------
# App init
# -------------------------------------------------
app = FastAPI(title="Video Summary Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "vsg_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# -------------------------------------------------
# Auth Routes
# -------------------------------------------------
@app.post("/register")
def register_user(user: UserRegister, db = Depends(get_db)):
    if get_user_by_username(db, user.username):
        raise HTTPException(status_code=400, detail="Username already registered")
    create_user(db, user.username, user.email, user.password)
    return {"message": "User created successfully"}

@app.post("/login")
def login_user(user: UserAuth, db = Depends(get_db)):
    db_user = get_user_by_username(db, user.username)
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid username or password")
    return {"message": "Login successful", "username": user.username}

# -------------------------------------------------
# Home
# -------------------------------------------------
@app.get("/")
def home():
    return {
        "service": "Video Summary Backend",
        "status": "running",
        "message": "Backend is alive and ready to process videos.",
        "endpoints": {
            "start_job":  "POST /start",
            "job_status": "GET /status/{job_id}",
            "cancel_job": "POST /cancel/{job_id}",
            "all_jobs":   "GET /jobs"
        }
    }

# -------------------------------------------------
# All jobs (debug)
# -------------------------------------------------
@app.get("/jobs")
def jobs_status():
    return {
        "all_jobs":    {k: v for k, v in JOB_STATUS.items()},
        "cancel_flags": CANCEL_FLAGS
    }

@app.get("/debug")
def debug_info():
    import Backend.core_worker as cw
    return {"core_worker_file": cw.__file__}

# -------------------------------------------------
# Mode endpoint — tells frontend which engine is active
# -------------------------------------------------
@app.get("/mode")
def get_mode():
    return {
        "mode":  BACKEND_MODE,
        "port":  BACKEND_PORT,
        "label": "Unified Engine (Gemini + Local)",
        "emoji": "🚀",
        "is_unified": True
    }

# -------------------------------------------------
# Job status — polling endpoint
# -------------------------------------------------
@app.get("/status/{job_id}")
def get_job_status(job_id: str):
    if job_id not in JOB_STATUS:
        return JSONResponse(status_code=404, content={
            "job_id":   job_id,
            "status":   "not_found",
            "progress": 0,
            "error":    "Job ID not found"
        })
    job_data = JOB_STATUS[job_id]
    print(f"[API] Status check for {job_id}: {job_data}")
    return job_data

# -------------------------------------------------
# Start job
# -------------------------------------------------
@app.post("/start")
async def start_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(None),
    url:  str        = Form(None),
    summary_format: str = Form("paragraph"),
    mode: str = Form(None)  # New: Allow mode override
):
    # Use provided mode or fall back to port default
    effective_mode = mode if mode else BACKEND_MODE
    print(f"[API] Received start request - File: {file.filename if file else None}, URL: {url}, Mode: {effective_mode}")

    # BUG FIX 1: FastAPI ignores the tuple return ({"error": ...}, 400)
    # Must use JSONResponse for proper HTTP error codes
    if not file and not url:
        return JSONResponse(status_code=400, content={"error": "No input provided"})

    job_id = str(uuid.uuid4())

    JOB_STATUS[job_id] = {
        "job_id":   job_id,
        "status":   "initializing",
        "progress": 0,
        "result":   None,
        "error":    None
    }
    CANCEL_FLAGS[job_id] = False

    if file:
        source_type = "file"
        video_path  = os.path.join(UPLOAD_DIR, f"{job_id}_{file.filename}")

        print(f"[API] Saving uploaded file to: {video_path}")
        with open(video_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        source = video_path
    else:
        source_type = "url"
        source      = url

    print(f"[API] 🟢 Queuing background task for job {job_id}...", flush=True)
    background_tasks.add_task(
        process_job,
        job_id,
        source,
        source_type,
        summary_format,
        effective_mode
    )
    print(f"[API] ✅ Task queued for job {job_id}", flush=True)

    print(f"[API] Job {job_id} started - Source: {source}, Type: {source_type}, Mode: {BACKEND_MODE}")

    return {
        "job_id":      job_id,
        "source":      source,
        "source_type": source_type,
        "mode":        BACKEND_MODE,
        "status":      "started"
    }

# -------------------------------------------------
# Cancel job
# -------------------------------------------------
@app.post("/cancel/{job_id}")
def cancel_job(job_id: str):
    print(f"[API] Cancel requested for job: {job_id}")

    if job_id not in JOB_STATUS:
        return JSONResponse(status_code=404, content={"error": "Job not found"})

    CANCEL_FLAGS[job_id] = True
    JOB_STATUS[job_id]["status"] = "Cancelled"
    JOB_STATUS[job_id]["error"]  = "Job cancelled by user"

    return {"status": "cancelled", "job_id": job_id}