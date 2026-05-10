import os
import subprocess
import torch
import tempfile

from .models import (
    whisper_model,
    short_summarizer,
    long_summarizer,
    DEVICE,
    simple_summary,
    PEGASUS_AVAILABLE,
    BART_AVAILABLE,
    BLIP_AVAILABLE,
    blip_processor,
    blip_model,
)

import re

def format_summary(summary: str, summary_format: str) -> str:
    if summary_format == "bullet":
        sentences = re.split(r'(?<=[.!?])\s+', summary)
        return "\n".join(f"- {s.strip()}" for s in sentences if len(s.strip()) > 5)
    return summary


JOB_STATUS   = {}
CANCEL_FLAGS = {}


def update_status(job_id: str, progress: int, status: str, result=None, error=None):
    if job_id not in JOB_STATUS:
        JOB_STATUS[job_id] = {}
    JOB_STATUS[job_id].update({
        "job_id": job_id, "progress": progress,
        "status": status, "result": result, "error": error
    })
    print(f"[WORKER] {job_id}: {progress}% - {status}", flush=True)


# -------------------------------------------------------
# BART helper — returns plain text
# -------------------------------------------------------
def summarize_with_bart(text: str, max_len: int, min_len: int) -> str:
    try:
        result = long_summarizer(
            text, max_length=max_len, min_length=min_len,
            num_beams=2, truncation=True
        )
        return result[0]["summary_text"]
    except Exception as e:
        print(f"[WORKER] ⚠️ BART failed: {e}")
        return simple_summary(text, 5)


# -------------------------------------------------------
# Hierarchical summarize (long videos) — returns (text, model_label)
# -------------------------------------------------------
def hierarchical_summarize(text: str) -> tuple[str, str]:
    words  = text.split()
    chunks = [" ".join(words[i:i + 300]) for i in range(0, len(words), 300)]

    chunk_summaries = [summarize_with_bart(chunk, 100, 30) for chunk in chunks]
    combined        = " ".join(chunk_summaries)

    # Final pass: use PEGASUS if combined is short enough, else BART
    if PEGASUS_AVAILABLE and len(combined.split()) < 500:
        try:
            result = short_summarizer(
                combined, max_length=128, min_length=64,
                num_beams=4, truncation=True, early_stopping=True
            )
            return (
                result[0]["summary_text"],
                "BART-large-cnn + PEGASUS-xsum  (Hierarchical)"
            )
        except Exception as e:
            print(f"[WORKER] ⚠️ PEGASUS final-pass failed: {e}")

    return (
        summarize_with_bart(combined, 200, 80),
        "BART-large-cnn  (Hierarchical, facebook/bart-large-cnn)"
    )


# -------------------------------------------------------
# Smart model selection — returns (summary, model_label)
# -------------------------------------------------------
def optimal_summarize(text: str) -> tuple[str, str]:
    word_count = len(text.split())
    print(f"[WORKER] 📊 Text: {word_count} words")

    # Very short → just return the text itself
    if word_count < 30:
        return text.strip(), "Extractive  (text too short for neural model)"

    # Short (30–300 words) → PEGASUS
    if word_count <= 300:
        if PEGASUS_AVAILABLE:
            try:
                # ── Threshold: 500 chars ──
                # PEGASUS-xsum is better for extremely short texts.
                # BART-large-cnn is better for narrative summaries.
                if len(text) < 500:
                    result = short_summarizer(
                        text, max_length=150, min_length=60,
                        num_beams=4, no_repeat_ngram_size=3, truncation=True
                    )
                    return result[0]["summary_text"], "PEGASUS-xsum  (google/pegasus-xsum)"
                else:
                    return summarize_with_bart(text, 180, 80), "BART-large-cnn  (facebook/bart-large-cnn)"
            except Exception as e:
                print(f"[WORKER] ⚠️ PEGASUS failed: {e}")

        if BART_AVAILABLE:
            return summarize_with_bart(text, 180, 80), "BART-large-cnn  (facebook/bart-large-cnn)"

        return text.strip(), "Extractive  (no neural model available)"

    # Medium (300–800 words) → BART
    if BART_AVAILABLE:
        if word_count > 800:
            return hierarchical_summarize(text)
        return summarize_with_bart(text, 280, 120), "BART-large-cnn  (facebook/bart-large-cnn)"

    return simple_summary(text, 6), "Extractive  (no neural model available)"


# -------------------------------------------------------
# Video download
# -------------------------------------------------------
UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "vsg_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Keywords in yt-dlp stderr that indicate YouTube is actively blocking
_YT_BLOCK_PHRASES = [
    "sign in to confirm",
    "confirm you're not a bot",
    "this video is unavailable",
    "video unavailable",
    "http error 403",
    "403 forbidden",
    "precondition check failed",
    "private video",
    "age-restricted",
    "members only",
    "sign in to confirm your age",
    "not available in your country",
]

def _is_youtube_block(stderr_text: str) -> bool:
    low = stderr_text.lower()
    return any(phrase in low for phrase in _YT_BLOCK_PHRASES)

def _is_youtube_url(url: str) -> bool:
    return "youtube.com" in url or "youtu.be" in url


def download_video_from_link(url: str) -> str:
    import uuid
    import sys
    out_name = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}.%(ext)s")

    # ── Strategy 1: Use mobile clients (less blocked than web) ──
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--no-playlist",
        "-f", "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480]/best",
        "--merge-output-format", "mp4",
        "-o", out_name,
    ]
    
    if _is_youtube_url(url):
        # mweb and ios are currently the most resilient clients
        cmd += [
            "--extractor-args", "youtube:player_client=mweb,ios,android,web",
            "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        ]
    
    cmd.append(url)

    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=300)
        
        # ── Strategy 2: If blocked, retry with browser cookies ──
        if result.returncode != 0 and _is_youtube_url(url) and _is_youtube_block(result.stderr):
            print(f"[WORKER] ⚠️ YouTube blocked basic request. Retrying with browser cookies...", flush=True)
            # Try Chrome first, then Edge as fallback for Windows users
            for browser in ["chrome", "edge"]:
                retry_cmd = cmd + ["--cookies-from-browser", browser]
                try:
                    result = subprocess.run(retry_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=300)
                    if result.returncode == 0:
                        print(f"[WORKER] ✅ Success using {browser} cookies!", flush=True)
                        break
                except:
                    continue

        if result.returncode != 0:
            err_text = result.stderr.strip() if result.stderr else "Unknown yt-dlp error"
            # Detect YouTube actively blocking the download
            if _is_youtube_url(url) and _is_youtube_block(err_text):
                raise RuntimeError(
                    "YOUTUBE_BLOCKED: YouTube has blocked this download request. "
                    "YouTube actively prevents automated access. "
                    "Please try uploading the video file directly, or use a different platform "
                    "(Vimeo, Dailymotion, Twitter/X, Instagram, TikTok, etc.)."
                )
            err_summary = err_text[-600:] if err_text else "Unknown yt-dlp error"
            raise RuntimeError(f"Download failed (yt-dlp error): {err_summary}")
    except subprocess.TimeoutExpired:
        raise RuntimeError("Video download timed out after 5 minutes.")

    # Find the actual downloaded file (extension may vary)
    downloaded = None
    for f in os.listdir(UPLOAD_DIR):
        if f.endswith((".mp4", ".webm", ".mkv", ".avi", ".mov")):
            candidate = os.path.join(UPLOAD_DIR, f)
            if downloaded is None or os.path.getmtime(candidate) > os.path.getmtime(downloaded):
                downloaded = candidate

    if not downloaded or not os.path.exists(downloaded):
        raise RuntimeError("Download failed: output file not found after yt-dlp ran.")
    return downloaded


# -------------------------------------------------------
# BLIP Visual Summarization (LOCAL — port 8000)
# ffprobe duration → evenly-spaced frames → BLIP conditional captions → narrative
# -------------------------------------------------------
def blip_visual_summarize_pipeline(job_id: str, video_path: str) -> tuple[str, str]:
    """
    Extracts exactly NUM_FRAMES evenly-spaced frames from ANY video length,
    runs BLIP conditional captioning, detects motion between frames,
    then synthesizes a motion-aware narrative using BART.
    """
    import tempfile
    import glob
    from PIL import Image

    if not BLIP_AVAILABLE:
        return (
            "⚠️ BLIP model is not available. Please restart the backend so it can download the model.",
            "en"
        )

    NUM_FRAMES = 8
    update_status(job_id, 46, "Measuring video duration...")

    # ── Step 1: Get duration via ffprobe ──
    duration_sec = None
    try:
        probe = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path
            ],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15
        )
        duration_sec = float(probe.stdout.strip())
        print(f"[WORKER] BLIP: video duration = {duration_sec:.2f}s")
    except Exception as e:
        print(f"[WORKER] BLIP: ffprobe failed ({e}), falling back to fps=1")

    update_status(job_id, 48, f"Extracting {NUM_FRAMES} evenly-spaced frames...")

    # ── Step 2: Extract NUM_FRAMES evenly-spaced frames ──
    frame_dir = tempfile.mkdtemp(prefix="blip_frames_")
    frame_pattern = os.path.join(frame_dir, "frame_%04d.jpg")
    frames = []

    if duration_sec and duration_sec > 0:
        # Dynamically set FPS to get the exact number of frames
        fps = min(30.0, max(0.5, NUM_FRAMES / duration_sec))
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", video_path,
                "-vf", f"fps={fps}",
                "-frames:v", str(NUM_FRAMES),
                "-q:v", "2",
                frame_pattern
            ],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        frames = sorted(glob.glob(os.path.join(frame_dir, "*.jpg")))

    if len(frames) < NUM_FRAMES // 2:
        # Aggressive fallback if the first try failed
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", video_path,
                "-vf", "fps=4", "-frames:v", str(NUM_FRAMES),
                "-q:v", "2", frame_pattern
            ],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        frames = sorted(glob.glob(os.path.join(frame_dir, "*.jpg")))

    if not frames:
        # Last resort: single thumbnail
        subprocess.run(
            ["ffmpeg", "-y", "-i", video_path, "-vframes", "1", "-q:v", "2", frame_pattern],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        frames = sorted(glob.glob(os.path.join(frame_dir, "*.jpg")))

    if not frames:
        return "Could not extract frames from the video for BLIP analysis.", "en"

    print(f"[WORKER] BLIP: extracted {len(frames)} frames")

    # ── Step 3: BLIP conditional captioning ──
    update_status(job_id, 56, f"BLIP is analyzing {len(frames)} frames...")
    captions = []
    try:
        with torch.no_grad():
            for i, frame_path in enumerate(frames):
                img = Image.open(frame_path).convert("RGB")
                # Conditional prompt coaxes richer, action-aware output
                inputs = blip_processor(
                    images=img,
                    text="a scene showing",
                    return_tensors="pt"
                )
                inputs = {k: v.to(DEVICE) for k, v in inputs.items()}
                if DEVICE == "cuda":
                    inputs = {
                        k: v.half() if v.dtype == torch.float32 else v
                        for k, v in inputs.items()
                    }
                out = blip_model.generate(
                    **inputs,
                    max_new_tokens=60,
                    num_beams=5,
                    min_length=8,
                    repetition_penalty=1.3
                )
                caption = blip_processor.decode(out[0], skip_special_tokens=True)
                # Strip echoed prompt prefix if present
                if caption.lower().startswith("a scene showing"):
                    caption = caption[len("a scene showing"):].strip()
                captions.append(caption.strip())
                print(f"[WORKER] BLIP frame {i+1}: {caption}")
    except Exception as e:
        print(f"[WORKER] BLIP captioning error: {e}")
        return f"BLIP captioning error: {e}", "en"
    finally:
        for f in frames:
            try:
                os.remove(f)
            except Exception:
                pass
        try:
            os.rmdir(frame_dir)
        except Exception:
            pass

    if not captions:
        return "No frame captions could be generated by BLIP.", "en"

    # ── Step 4: Deduplicate & detect motion across frames ──
    unique_captions = []
    seen = set()
    for c in captions:
        c_clean = c.lower().strip()
        if c_clean and c_clean not in seen:
            unique_captions.append(c)
            seen.add(c_clean)

    has_motion = len(unique_captions) > 1
    print(f"[WORKER] BLIP: {len(unique_captions)} unique captions, motion={has_motion}")

    # ── Step 5: Narrative synthesis with BART (scene-context prompt) ──
    update_status(job_id, 74, "Synthesizing action narrative from frame captions...")

    # BART is not an instruction-following LLM, it's a standard summarizer.
    # Feed it the raw descriptions directly to summarize into a cohesive narrative.
    synthesis_input = " ".join(unique_captions)

    narrative = None
    if BART_AVAILABLE and long_summarizer:
        try:
            result = long_summarizer(
                synthesis_input,
                max_length=150, min_length=15,
                num_beams=4, truncation=True,
                no_repeat_ngram_size=3
            )
            narrative = result[0]["summary_text"]
        except Exception as e:
            print(f"[WORKER] BART narrative synthesis failed: {e}")

    if not narrative:
        narrative = " → ".join(unique_captions) if has_motion else unique_captions[0]

    # ── Format output ──
    motion_text = f"Motion/change detected across {len(unique_captions)} scene descriptions" if has_motion else "Static scene detected"
    
    output = (
        f"### 🖼️ Visual Summary (BLIP + BART)\n\n"
        f"{narrative}\n\n"
        f"### 🎬 Motion Analysis\n\n"
        f"*{motion_text}*\n\n"
        f"### 👁️ Key Scene Transitions\n\n"
        + "\n".join(f"- {c.capitalize()}" for c in unique_captions)
    )
    return output, "en"



# -------------------------------------------------------
# Visual Summarization (Gemini Multimodal API)
# -------------------------------------------------------
def visual_summarize_pipeline(job_id: str, video_path: str) -> tuple[str, str]:
    import os
    import time
    from dotenv import load_dotenv
    
    load_dotenv()
    gemini_key = os.environ.get("GEMINI_API_KEY")
    
    if not gemini_key:
        return "⚠️ **GEMINI API KEY MISSING**<br><br>To summarize non-audio videos perfectly, this app now uses the Google Gemini Multimodal AI. It is infinitely smarter and faster than the old local AI.<br><br>Please open the `.env` file in your project folder, add `GEMINI_API_KEY=your_api_key_here`, and restart the backend.", "en"
        
    try:
        import google.generativeai as genai
        genai.configure(api_key=gemini_key)
        
        update_status(job_id, 50, "Uploading video to Gemini API...")
        video_file = genai.upload_file(path=video_path)
        
        while video_file.state.name == "PROCESSING":
            update_status(job_id, 60, "Gemini is processing the video...")
            time.sleep(2)
            video_file = genai.get_file(video_file.name)
            
        if video_file.state.name == "FAILED":
            raise ValueError("Gemini failed to process the video on their servers.")
            
        update_status(job_id, 70, "Gemini is writing the summary...")
        model = genai.GenerativeModel(model_name="gemini-2.5-flash-lite")
        
        prompt = "You are a professional AI analyzing a silent screencast or video. Please provide your analysis formatted EXACTLY like this with Markdown:\n\n🎬 **Visual Summary:**\n[Write a professional, comprehensive summary of the overall purpose, context, and events of the video here.]\n\n👁️ **Detailed Scene Description:**\n[Write a chronological, smoothly flowing narrative detailing exactly what actions occurred on the screen, including reading any prominent text you see.]"
        
        response = model.generate_content([video_file, prompt])
        
        try:
            genai.delete_file(video_file.name)
        except:
            pass
            
        return response.text, "en"
    except Exception as e:
        print(f"[WORKER] Gemini failed: {e}")
        return f"Gemini API Error: {str(e)}", "en"


# -------------------------------------------------------
# Gemini Text Summarization (for audio-transcribed videos in Gemini mode)
# -------------------------------------------------------
def gemini_text_summarize(job_id: str, transcript: str) -> tuple[str, str]:
    """Send Whisper transcript to Gemini for fast, high-quality summarization."""
    import os
    from dotenv import load_dotenv
    load_dotenv()
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_key:
        # Fallback to local if key is missing
        print("[WORKER] No GEMINI_API_KEY, falling back to local summarizer.")
        return optimal_summarize(transcript)
    try:
        import google.generativeai as genai
        genai.configure(api_key=gemini_key)
        update_status(job_id, 75, "Gemini is summarizing the transcript...")
        model = genai.GenerativeModel(model_name="gemini-2.5-flash-lite")
        prompt = (
            "You are a professional content analyst. The following text is a speech transcript from a video.\n"
            "Write a clear, concise, well-structured summary in plain English paragraphs.\n"
            "Capture the key points, main arguments, and any important conclusions.\n"
            "Do NOT include headers, bullet points, or markdown. Just clean paragraph prose.\n\n"
            f"TRANSCRIPT:\n{transcript[:12000]}"  # limit to avoid token overflow
        )
        response = model.generate_content(prompt)
        return response.text.strip(), "Gemini 2.5 Flash (Text Summarization)"
    except Exception as e:
        print(f"[WORKER] Gemini text summarize failed: {e}. Falling back to local.")
        return optimal_summarize(transcript)


# -------------------------------------------------------
# Main worker
# -------------------------------------------------------
def process_job(job_id: str, source: str, source_type: str, summary_format: str = "paragraph", mode: str = "local"):
    print(f"[WORKER] 🚀 Job {job_id} started | mode={mode}")
    audio_path       = f"temp_audio_{job_id}.wav"
    downloaded_video = None

    try:
        update_status(job_id, 10, "Preparing video...")
        if CANCEL_FLAGS.get(job_id):
            return

        transcript = ""
        language = "unknown"
        is_silent = False
        transcript_fetched_via_api = False

        if source_type == "url":
            # ── Step 1: Try to fetch YouTube transcript via API (fast, no download needed) ──
            is_youtube = "youtube.com" in source or "youtu.be" in source
            if is_youtube:
                try:
                    from youtube_transcript_api import YouTubeTranscriptApi
                    from urllib.parse import urlparse, parse_qs

                    video_id = None
                    if "youtu.be" in source:
                        video_id = source.split("/")[-1].split("?")[0]
                    else:
                        parsed_url = urlparse(source)
                        video_id = parse_qs(parsed_url.query).get("v", [None])[0]

                    if video_id:
                        update_status(job_id, 15, "Fetching YouTube transcript...")
                        # Try English first, then any available language
                        try:
                            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=["en", "en-US", "en-GB"])
                        except Exception:
                            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
                        transcript = " ".join([t["text"] for t in transcript_list])
                        language = "en"
                        transcript_fetched_via_api = True
                        print(f"[WORKER] ✅ Transcript fetched via YouTube API for {video_id}")
                except Exception as e:
                    print(f"[WORKER] ⚠️ YouTube Transcript API failed ({type(e).__name__}: {e}). Will download video instead.")

            # ── Step 2: If transcript wasn't fetched, download the video ──
            if not transcript_fetched_via_api:
                update_status(job_id, 15, "Downloading video from URL...")
                downloaded_video = download_video_from_link(source)
                source = downloaded_video

        if not transcript_fetched_via_api:
            try:
                update_status(job_id, 25, "Extracting audio...")
                subprocess.run(
                    ["ffmpeg", "-y", "-i", source, "-q:a", "0", "-map", "a", "-ac", "1", audio_path],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
                )
                
                if os.path.exists(audio_path) and os.path.getsize(audio_path) > 1000:
                    update_status(job_id, 40, "Transcribing...")
                    with torch.no_grad():
                        result = whisper_model.transcribe(audio_path, fp16=(DEVICE == "cuda"))
                    
                    transcript = result["text"].strip()
                    language   = result.get("language", "unknown")
                    
                    # Check for empty or just noise like "(music)", "(silence)", "[music playing]"
                    clean_transcript = re.sub(r'\[.*?\]|\(.*?\)', '', transcript).strip()
                    
                    if not clean_transcript or len(clean_transcript) < 5:
                        print(f"[WORKER] No meaningful speech detected in audio stream. Clean transcript: '{clean_transcript}'")
                        is_silent = True
                else:
                    print(f"[WORKER] Audio file too small, treating as silent.")
                    is_silent = True
                    
            except subprocess.CalledProcessError:
                print(f"[WORKER] No audio stream found, switching to visual summarization.")
                is_silent = True

        if is_silent:
            if mode == "gemini":
                update_status(job_id, 45, "Muted video — Analyzing with Gemini Multimodal...")
                transcript, language = visual_summarize_pipeline(job_id, source)
                model_used = "Gemini 2.5 Flash Multimodal"
            else:
                update_status(job_id, 45, "Muted video — Analyzing frames with BLIP (local)...")
                transcript, language = blip_visual_summarize_pipeline(job_id, source)
                model_used = "BLIP (Salesforce/blip-image-captioning-base) + BART"
            formatted_summary = transcript
        else:
            if not transcript:
                raise RuntimeError("Could not extract speech or visual information from the video.")
            if mode == "gemini":
                update_status(job_id, 70, "Summarizing with Gemini LLM...")
                summary, model_used = gemini_text_summarize(job_id, transcript)
            else:
                update_status(job_id, 70, "Summarizing with local models (BART/PEGASUS)...")
                summary, model_used = optimal_summarize(transcript)
            
            # Format audio summary similarly to visual summary
            formatted_summary = (
                f"### 🎙️ Audio Transcription Summary ({model_used})\n\n"
                f"{summary}"
            )

        print(f"[WORKER] 🤖 Summarizer used: {model_used}")

        update_status(job_id, 100, "Complete", result={
            "summary":           formatted_summary,
            "language":          language,
            "device":            DEVICE,
            "word_count":        len(transcript.split()),
            "transcript_length": len(transcript),
            "model_used":        model_used,
            "backend_mode":      mode,
            "is_silent":         is_silent,
        })
        print(f"[WORKER] ✓ Job {job_id} completed (mode={mode})")

    except Exception as e:
        update_status(job_id, 0, "Failed", error=str(e))
        print(f"[WORKER] ❌ {e}")

    finally:
        for f in [audio_path, downloaded_video]:
            if f and os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass
        CANCEL_FLAGS.pop(job_id, None)
        print(f"[WORKER] 🧹 Cleanup complete")