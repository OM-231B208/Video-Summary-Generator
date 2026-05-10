# Video Summary Generator (VSG) — Complete Panel Evaluation Document
**Last Updated:** 2026-05-08 | **Team:** SOT | **Environment:** Conda `om_pro_vsg` | **Python:** 3.10

---

## Q1. What Tools Have We Been Using So Far and Why?

**Tools & Why Each Was Chosen:**

| Tool | Purpose | Why This Tool? |
|---|---|---|
| **Python 3.10** | Core programming language for both backend and frontend | Industry-standard for AI/ML projects; rich ecosystem of libraries |
| **FastAPI** | Backend REST API framework | Async-first design allows heavy AI tasks to run in background without blocking; auto-generates API documentation |
| **Uvicorn** | ASGI server to run FastAPI | Lightweight, production-grade; pairs perfectly with FastAPI |
| **Streamlit** | Frontend web UI framework | Allows rapid, Pythonic UI development with support for custom HTML/CSS/JS injection |
| **FFmpeg** | Audio extraction and frame sampling from video | Industry-standard, free, supports every video format (mp4, mkv, avi, webm, mov) |
| **OpenAI Whisper (base)** | Speech-to-text transcription | Trained on 680,000 hours of multilingual audio; robust to noise and accents |
| **BART-large-cnn** | Long-form text summarization | Fine-tuned on CNN/DailyMail news articles; excellent for structured narrative summaries |
| **PEGASUS-xsum** | Extreme/short summarization | Designed specifically for extremely condensed summaries; ideal for short transcripts |
| **BLIP (Salesforce)** | Image/frame captioning for muted videos | Vision-Language model; can describe what is happening visually even without audio |
| **Google Gemini 2.5 Flash** | Cloud-based multimodal LLM | Can directly "watch" a video and describe it; used for muted video in Gemini mode |
| **yt-dlp** | Download videos from 1000+ websites | More powerful, actively maintained fork of youtube-dl; supports cookies and client emulation |
| **youtube-transcript-api** | Fetch YouTube subtitles without downloading | Instant transcript retrieval (< 1 second) when YouTube provides official captions |
| **SQLite** | User database | Zero-setup, serverless, file-based; perfect for local/portable projects |
| **SQLAlchemy** | ORM to interface with SQLite | Clean, Pythonic way to write database queries without raw SQL |
| **bcrypt** | Password hashing | Industry-standard one-way encryption; even if DB is leaked, passwords stay safe |
| **PyTorch** | Deep learning runtime for models | Required by Whisper, BART, PEGASUS, and BLIP |
| **Transformers (HuggingFace)** | Load and run BART, PEGASUS, BLIP models | Unified API for loading pre-trained transformer models |
| **Pydantic** | Data validation in FastAPI | Automatically validates incoming JSON request bodies |
| **Google Generative AI SDK** | Interface to Gemini API | Official Python SDK for uploading files and calling Gemini multimodal endpoints |

---

## Q2. What Has Been Done in the Frontend? What Tools, Functions, and Logic Are Used?

**The frontend is a single file: `Frontend/app.py` (~2195 lines, ~90KB).**

### Tools Used in Frontend:
- **Streamlit** — core UI framework
- **Custom CSS** — Glassmorphism cards, neon glow effects, 3D glossy buttons
- **Google Fonts** — `Syne` (headings) + `Inter` (body text)
- **JavaScript (injected via `st.components.v1.html`)** — progress ring animation, TTS (text-to-speech), download buttons, typewriter effect
- **Web Speech API** — browser-native TTS for the "Recite Summary" feature
- **jsPDF (CDN)** — PDF generation entirely in the browser
- **Python `requests` library** — HTTP calls from frontend to backend API

### Basic Functions Implemented:
1. **User Registration / Login** — form with username, email, password fields; calls `/register` or `/login` API
2. **File Upload** — drag-and-drop video uploader (`st.file_uploader`)
3. **URL Input** — text field for pasting video links
4. **Video Preview Toggle** — "View Video / Hide Preview" button
5. **Start Processing** — sends file or URL to backend, receives a Job ID
6. **Real-Time Progress Display** — circular animated progress ring showing 0–100%
7. **Summary Display** — rendered in Paragraph or Bullet Points format
8. **Recite Summary (TTS)** — Play / Pause / Resume / Stop buttons
9. **Download Summary** — as `.txt` or `.pdf`
10. **Process Another Video** — full session reset
11. **Logout** — clears session state and URL params

### Logic (Polling System):
The frontend uses a **polling loop**. After submitting a job:
1. Frontend sends POST to `/start` → gets a `job_id`
2. Every **0.8 seconds**, frontend calls GET `/status/{job_id}`
3. Backend returns `{progress: 65, status: "Transcribing..."}`
4. Frontend updates the progress ring and status label
5. When `progress == 100`, the result is displayed
6. If the backend crashes (job not found 3+ times), it shows a graceful error

### Design System:
- **Background:** `#060818` (deep space black)
- **Primary Color:** `#7C3AED` (violet)
- **Accent:** `#06B6D4` (cyan)
- **Fonts:** Syne (display) + Inter (body) from Google Fonts
- **Animations:** Logo descent, vortex orbit rings, wavy neon progress canvas, summary card glow pulse, confetti/sparkle on completion

---

## Q3. Where Is the Frontend Deployed? Why Here Only?

**Deployed on: `http://localhost:8501` (local machine only)**

**Why local deployment only?**

1. **Model Size:** BART, PEGASUS, BLIP, and Whisper are large models (hundreds of MB to GBs). Cloud hosting would require expensive GPU instances.
2. **No Latency for File Transfers:** When uploading a 500MB video, transferring it to a cloud server would take minutes. Locally, it's instant.
3. **GPU Access:** Local deployment uses the user's own CUDA GPU (if available) for faster inference.
4. **Development Phase:** This is a minor project/prototype. Cloud deployment (AWS, GCP, Heroku) is the logical next step but is outside the current project scope.
5. **Privacy:** Videos never leave the user's own machine — no cloud storage or privacy concerns.

**Run command:**
```bash
conda activate om_pro_vsg
uvicorn Backend.api:app --reload --port 8000   # Backend
streamlit run Frontend/app.py                   # Frontend (new terminal)
```

---

## Q4. Which Database Has Been Used? Why? How Does It Work? Is There a Cache? Does It Remember User Work?

### Database Used: **SQLite** (file: `vsg_users.db`)

**Why SQLite?**
- **Serverless** — no separate database server process needed
- **Portable** — the entire database is a single `.db` file in the project folder
- **Zero Configuration** — no installation, no credentials, no network setup
- **Sufficient for scale** — handles dozens of concurrent users perfectly for a local/demo project

### How It Works:
The database is managed by **SQLAlchemy ORM** (`Backend/auth.py`). There is one table:

```
Table: users
┌────┬──────────────┬──────────────────────┬──────────────────────────────────┐
│ id │ username     │ email                │ hashed_password                  │
├────┼──────────────┼──────────────────────┼──────────────────────────────────┤
│ 1  │ om_admin     │ om@college.edu       │ $2b$04$xyz...bcrypt_hash...       │
└────┴──────────────┴──────────────────────┴──────────────────────────────────┘
```

- When a user **registers**, `bcrypt.hashpw()` encrypts the password before storage. The original password is never saved.
- When a user **logs in**, `bcrypt.checkpw()` compares the entered password against the stored hash.
- Sessions are maintained using **Streamlit's `st.session_state`** (in-memory, per browser tab).

### Is There a Cache System?
**There is NO persistent cache** for AI results. However:
- **Model Cache:** Whisper, BART, PEGASUS, and BLIP models are loaded **once** at backend startup and kept in RAM/GPU memory for the entire session. This avoids reloading models (which takes 30–60 seconds) on every request.
- **Job Status Cache:** `JOB_STATUS` is a Python dictionary in `core_worker.py` that stores the progress and result of every job in memory during the backend's uptime.

### Does It Remember User Work (Past Summaries)?
**No** — the current version does not store past summaries to the database. Each session is independent. When the user logs out or refreshes, the result is gone. *(This is a planned future feature: adding a `summaries` table to SQLite to store history.)*

---

## Q5. What Processes Are Used During Summarization? (Both: Upload & URL)

### Process A: Video File Upload

```
User uploads .mp4 file
       ↓
Frontend sends multipart/form-data POST to /start
       ↓
Backend saves file → temp_uploads/{job_id}_filename.mp4
       ↓
FFmpeg extracts audio → temp_audio_{job_id}.wav (mono, 16kHz)
       ↓
Audio file exists AND size > 1KB?
  ├── YES → Whisper.transcribe() → raw text transcript
  │         ├── Transcript has real speech? → optimal_summarize(text)
  │         └── Only noise/silence? → is_silent = True → Visual Pipeline
  └── NO  → is_silent = True → Visual Pipeline
       ↓
Visual Pipeline (BLIP local / Gemini cloud)
       ↓
JOB_STATUS updated with progress=100, result={summary, model, language...}
       ↓
Temp files (audio + video) deleted
       ↓
Frontend poll detects progress=100 → displays result
```

### Process B: Paste Video URL

```
User pastes URL
       ↓
Is it a YouTube URL?
  ├── YES → Try youtube-transcript-api first (< 1 second, no download needed!)
  │         ├── SUCCESS → skip download, go straight to summarization
  │         └── FAIL → fall through to yt-dlp download
  └── NO → skip to yt-dlp download
       ↓
yt-dlp downloads video → saved to temp directory
       ↓
[Same pipeline as File Upload from this point onward]
       ↓
Audio extract → Whisper → Summarize / Visual Pipeline → Cleanup
```

**Key Difference:** For YouTube URLs, the app first tries the **official transcript API** (instant, no AI needed). Only if that fails does it download and process the video.

---

## Q6. What Files Are There in Backend and Frontend? Names, Uses, and Tasks.

### Backend Files (`Backend/`)

| File | Size | Role & Tasks |
|---|---|---|
| `api.py` | 7.6 KB | **FastAPI entry point.** Defines all HTTP routes: `POST /register`, `POST /login`, `POST /start`, `GET /status/{job_id}`, `POST /cancel/{job_id}`, `GET /mode`, `GET /jobs`. Handles file saving, job queuing via `BackgroundTasks`, port detection (8000=local, 8001=Gemini mode). |
| `core_worker.py` | 27 KB | **The AI processing engine.** Contains: `process_job()` (main pipeline), `optimal_summarize()` (smart model routing), `hierarchical_summarize()` (chunking for long text), `summarize_with_bart()`, `blip_visual_summarize_pipeline()`, `visual_summarize_pipeline()` (Gemini), `gemini_text_summarize()`, `download_video_from_link()` (yt-dlp with YouTube fix). Also manages `JOB_STATUS` and `CANCEL_FLAGS` dictionaries. |
| `models.py` | 5.5 KB | **Model loader.** Runs at backend startup. Loads Whisper (`base`), PEGASUS-xsum, BART-large-cnn, and BLIP into RAM/GPU. Sets `PEGASUS_AVAILABLE`, `BART_AVAILABLE`, `BLIP_AVAILABLE` flags. Contains `simple_summary()` extractive fallback. |
| `auth.py` | 1.3 KB | **Authentication & database.** Defines SQLAlchemy `User` model, creates `vsg_users.db`, provides `create_user()`, `get_user_by_username()`, `verify_password()` using native `bcrypt`. |
| `video_loader.py` | 0.6 KB | **Legacy helper.** Originally contained URL download logic; now superseded by `download_video_from_link()` in `core_worker.py`. |
| `__init__.py` | — | Makes `Backend/` a Python package so modules can import from each other with `from .models import ...` |

### Frontend Files (`Frontend/`)

| File | Size | Role & Tasks |
|---|---|---|
| `app.py` | 91.6 KB | **Entire frontend.** Contains: CSS design system, hero header HTML, auth UI (login/register forms), backend detection, input mode selector, file uploader, URL input, circular progress ring (HTML/JS), result display (stat cards, summary card), TTS component (JS), download buttons (jsPDF), all button logic, polling loop, session state management. |
| `logo.png` | 448 KB | **Application logo.** Loaded as base64 and embedded directly in the hero header HTML. |

### Root Directory (Utility Files)

| File | Status & Purpose |
|---|---|
| `vsg_users.db` | **Live database** — SQLite file storing all registered users |
| `.env` | **API Key storage** — contains `GEMINI_API_KEY=...` |
| `main.py` | Legacy standalone pipeline (superseded) |
| `summarizer.py` | Legacy standalone summarizer (superseded) |
| `transcriber.py` | Legacy standalone transcriber (superseded) |
| `temp_audio_*.wav` | Temporary audio files auto-created and auto-deleted per job |
| `temp_uploads/` | Staging directory for uploaded video files |

---

## Q7. How Is the API Integrated? How Does It Work?

**Architecture:** The frontend and backend are **separate processes** communicating via HTTP REST API.

```
[Streamlit Frontend - Port 8501]  ←HTTP→  [FastAPI Backend - Port 8000/8001]
```

### API Endpoints & Their Integration:

| Endpoint | Method | Called By | What It Does |
|---|---|---|---|
| `/register` | POST | Login form | Creates new user in SQLite |
| `/login` | POST | Login form | Verifies credentials, returns username |
| `/start` | POST | "Start Processing" button | Accepts file/URL, creates job, returns `job_id` |
| `/status/{job_id}` | GET | Polling loop (every 0.8s) | Returns `{progress, status, result, error}` |
| `/cancel/{job_id}` | POST | (future use) | Sets `CANCEL_FLAGS[job_id] = True` |
| `/mode` | GET | App startup | Returns which engine is active (local/gemini) |

### Step-by-Step Flow Example:
```
1. User clicks "Start Processing"
   → Frontend: requests.post("http://127.0.0.1:8000/start", files={"file": video}, data={"mode": "local"})
   → Backend: saves file, creates job_id = "abc-123", starts background task
   → Response: {"job_id": "abc-123", "status": "started"}

2. Frontend stores job_id in st.session_state.job_id

3. Every 0.8 seconds:
   → Frontend: requests.get("http://127.0.0.1:8000/status/abc-123")
   → Backend: returns {"progress": 40, "status": "Transcribing..."}
   → Frontend: updates progress ring to 40%

4. When progress = 100:
   → Backend: returns {"progress": 100, "result": {"summary": "...", "model_used": "BART"}}
   → Frontend: displays the summary card
```

### Backend Auto-Detection:
At startup, the frontend tries ports `8001` then `8000`. Whichever responds first is used. This allows seamless switching between Gemini and Local modes.

---

## Q8. What AI Models Have Been Used? Their Task, Internal Working, and Encoders.

---

### Model 1: OpenAI Whisper (base)
**Task:** Convert speech audio into text (Speech-to-Text / ASR)

**How It Works Internally:**
1. Takes a `.wav` audio file as input
2. Converts the audio waveform into a **Mel Spectrogram** — a 2D image-like representation of sound frequencies over time
3. A **Conv1D (Convolutional) encoder** processes this spectrogram to extract audio features
4. A **Transformer Encoder** (like BERT) learns patterns in those features
5. A **Transformer Decoder** generates the text transcript token by token
6. Output: plain text string of everything spoken

**Encoder Used:** Conv1D → Transformer Encoder (self-attention)

**Example:**
- Input: 30 seconds of audio saying "Artificial intelligence is transforming industries"
- Output: `"Artificial intelligence is transforming industries."`

**Limitation:** Struggles with heavy background music, multiple overlapping speakers, or extremely soft speech.

---

### Model 2: BART-large-cnn (facebook/bart-large-cnn)
**Task:** Abstractive text summarization for medium-to-long transcripts (300–800+ words)

**How It Works Internally:**
1. The text transcript is tokenized into sub-word tokens
2. A **Bidirectional Transformer Encoder** reads ALL tokens simultaneously (forward AND backward), so it understands full context
3. The encoder builds a rich representation of the text's meaning
4. A **Transformer Decoder** generates the summary word-by-word using **beam search** (explores multiple possible next words and picks the best path)
5. `num_beams=2` means it explores 2 parallel word paths at each step and picks the best

**Encoder Used:** Bidirectional Transformer (similar to BERT)

**Example:**
- Input: 400-word lecture transcript about climate change
- Output: "Climate change poses significant risks to global ecosystems, driven primarily by carbon emissions from fossil fuels."

**Limitation:** Max input is ~1024 tokens (~750 words). Longer text must be chunked first.

---

### Model 3: PEGASUS-xsum (google/pegasus-xsum)
**Task:** Extreme/short summarization for brief transcripts (30–300 words)

**How It Works Internally:**
1. PEGASUS was pre-trained using a unique technique called **Gap Sentence Generation (GSG)**
2. During training, the most important sentence in a document was REMOVED, and the model had to PREDICT what that sentence was
3. This made the encoder exceptionally skilled at identifying the single most critical idea
4. The encoder processes the input text; the decoder generates an extremely condensed summary
5. Uses `num_beams=4` for higher quality but slower generation

**Encoder Used:** Transformer Encoder with Gap-Sentence pre-training

**Example:**
- Input: "The meeting discussed quarterly sales figures, team performance, and upcoming product launches. Sales were up 12%. The team performed exceptionally."
- Output: "Quarterly sales rose 12% as the team performed well ahead of new product launches."

**Limitation:** Not ideal for very long text; better suited for extracting the single most important idea.

---

### Model 4: BLIP (Salesforce/blip-image-captioning-base)
**Task:** Generate text captions from video frames (Visual Understanding)

**How It Works Internally:**
1. A video frame (image) is loaded and converted to RGB
2. The image is split into **16×16 pixel patches** (like breaking a photo into small squares)
3. Each patch is treated as a "word" — a **Vision Transformer (ViT) encoder** processes all patches and learns relationships between them
4. The **text decoder** (cross-attention to image features) generates a caption
5. We use **conditional prompting** — we prepend "a scene showing" to coax richer, more action-specific descriptions
6. After all 8 frames are captioned, **BART** synthesizes them into a coherent motion-aware narrative

**Encoder Used:** Vision Transformer (ViT) — image patches as tokens

**Example:**
- Frame 1 caption: "two people running on a street"
- Frame 4 caption: "a car speeding around a corner"
- Frame 8 caption: "police chasing a vehicle at night"
- BART synthesis: "The video depicts a high-speed chase through city streets at night, culminating in a police pursuit."

**Limitation:** Understands individual frames but cannot truly track motion between frames (no temporal understanding).

---

### Model 5: Google Gemini 2.5 Flash (Cloud)
**Task:** Multimodal analysis (watching video directly) + text summarization

**How It Works:**
1. The full video file is uploaded to Google's servers via the Gemini Files API
2. Gemini processes the entire video natively — it "watches" it just as a human would
3. A structured prompt instructs it to return a "Visual Summary" and "Detailed Scene Description"
4. For audio videos in Gemini mode, the Whisper transcript is sent as text, and Gemini summarizes it
5. The API key is loaded from the `.env` file

**Used For:** Muted video summarization (Gemini mode) and transcript summarization (Gemini mode)

