import streamlit as st
import requests
import time
import base64
from datetime import datetime
import json
from .assets import LOGO_BASE64  # Import the text-based logo

# -------------------------------------------------
# Config
# -------------------------------------------------
st.set_page_config(
    page_title="Video Summary Generator",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

MAX_PROCESSING_TIME = 300

# -------------------------------------------------
# Fast Backend Auto-Detect (Runs only once per session to avoid lag)
# -------------------------------------------------
def detect_backend():
    """Try port 8001 first (Gemini), then 8000 (Local)."""
    import requests
    for port in [8001, 8000]:
        for host in ["127.0.0.1", "localhost"]:
            try:
                r = requests.get(f"http://{host}:{port}/mode", timeout=0.6)
                if r.status_code == 200:
                    return f"http://{host}:{port}", r.json()
            except Exception:
                pass
    return "http://127.0.0.1:8000", {"mode": "unknown", "port": 8000, "label": "Offline", "emoji": "⚠️"}

if "backend_http" not in st.session_state or st.session_state.get("force_redetect"):
    url, info = detect_backend()
    st.session_state.backend_http = url
    st.session_state.backend_info = info
    st.session_state.force_redetect = False

BACKEND_HTTP = st.session_state.backend_http
_backend_info = st.session_state.backend_info

# -------------------------------------------------
# Session State & Persistence
# -------------------------------------------------
if not st.session_state.get("logged_in"):
    if "user" in st.query_params:
        st.session_state.logged_in = True
        st.session_state.username = st.query_params["user"]

defaults = {
    "job_id":        None,
    "running":       False,
    "progress":      0,
    "status_msg":    "",
    "result":        None,
    "error":         None,
    "start_time":    None,
    "poll_count":    0,
    "just_finished": False,
    "logged_in":     False,
    "username":      None,
    "show_video":    False,
    "last_url":      None,
    "last_file_name": None,
    "not_found_count": 0,
    "widget_key":    0,
    "just_logged_in": False,
    "backend_mode":  "unknown",
    "selected_mode": "local",  # Default to local
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Update session with detected backend mode
st.session_state.backend_mode = _backend_info.get("mode", "unknown")

# -------------------------------------------------
# Custom CSS for Premium UI
# -------------------------------------------------
def local_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&family=Inter:wght@400;500;600&display=swap');
    :root {
        --primary: #7C3AED;
        --accent:  #06B6D4;
        --secondary: #10B981;
        --bg-color: #060818;
        --text-color: #CBD5E1;
        --card-bg: rgba(255,255,255,0.03);
        --border-color: rgba(255,255,255,0.07);
        color-scheme: dark;
        --font-display: 'Syne', sans-serif;
        --font-body:    'Inter', sans-serif;
    }

    /* ── Global font ── */
    html, body, [class*="css"] {
        font-family: var(--font-body) !important;
        color: var(--text-color);
    }
    
    /* ── App background ── */
    .stApp {
        background-color: var(--bg-color);
        color: var(--text-color);
        font-family: 'Inter', sans-serif;
        overflow-x: hidden;
    }

    /* ── Hero header ── */
    .hero-header {
        text-align: center;
        padding: 40px 0 20px;
        position: relative;
    }

    /* ── Starry Network Background ── */
    .stars-bg {
        position: absolute;
        top: -50px; left: -100px; right: -100px; bottom: 0;
        background-image: 
            radial-gradient(1px 1px at 15% 20%, rgba(255,255,255,0.8) 100%, transparent),
            radial-gradient(2px 2px at 25% 75%, rgba(6,182,212,0.8) 100%, transparent),
            radial-gradient(1.5px 1.5px at 85% 35%, rgba(124,58,237,0.8) 100%, transparent),
            radial-gradient(1px 1px at 90% 70%, rgba(255,255,255,0.6) 100%, transparent),
            radial-gradient(2.5px 2.5px at 30% 40%, rgba(167,139,250,0.5) 100%, transparent),
            radial-gradient(1px 1px at 75% 65%, rgba(6,182,212,0.7) 100%, transparent);
        background-size: 250px 250px;
        opacity: 0.5;
        z-index: 0;
        pointer-events: none;
    }

    /* ── Logo wrapper — ALL animations live here ── */
    .hero-logo-wrap {
        position: relative;
        display: inline-flex;
        justify-content: center;
        align-items: center;
        padding: 50px;
        z-index: 10;
        perspective: 1200px;
    }

    /* ── The solid logo background & clean neon ring ── */
    .hero-logo-bg {
        position: absolute;
        top: 50%; left: 50%;
        transform: translate(-50%, -50%);
        width: 175px; height: 175px;
        background: #060818;
        border-radius: 50%;
        z-index: 3;
        box-shadow: 0 0 50px #060818;
    }
    .clean-neon-ring {
        position: absolute;
        top: 50%; left: 50%;
        transform: translate(-50%, -50%);
        border-radius: 50%;
        z-index: 4;
        pointer-events: none;
    }
    .clean-neon-ring.outer {
        width: 220px; height: 220px;
        border: 2px solid rgba(6,182,212, 0.8);
        box-shadow: 0 0 25px rgba(6,182,212,0.6), inset 0 0 20px rgba(6,182,212,0.4);
    }
    .clean-neon-ring.inner {
        width: 200px; height: 200px;
        border: 1.5px solid rgba(124,58,237, 0.9);
        box-shadow: 0 0 18px rgba(124,58,237,0.7);
    }

    /* ── Vortex Rings (3D accretion disk) ── */
    .vortex-container {
        position: absolute;
        top: 50%; left: 50%;
        transform: translate(-50%, -50%) rotateX(72deg);
        transform-style: preserve-3d;
        z-index: 1;
        pointer-events: none;
    }
    .v-ring {
        position: absolute;
        top: 50%; left: 50%;
        border-radius: 50%;
    }
    .v1 {
        width: 550px; height: 550px;
        border: 2px dashed rgba(6, 182, 212, 0.4);
        animation: spin-z 30s linear infinite;
        box-shadow: inset 0 0 20px rgba(6,182,212,0.2), 0 0 20px rgba(6,182,212,0.2);
    }
    .v2 {
        width: 450px; height: 450px;
        border: 3px dotted rgba(124, 58, 237, 0.6);
        animation: spin-z-rev 20s linear infinite;
        /* offset the rotation slightly in 3d */
        transform: translate(-50%, -50%) rotateY(15deg);
    }
    .v3 {
        width: 350px; height: 350px;
        border: 1.5px dashed rgba(167, 139, 250, 0.5);
        animation: spin-z 15s linear infinite;
        transform: translate(-50%, -50%) rotateY(-10deg);
    }
    .v4 {
        width: 700px; height: 700px;
        border: 1px dotted rgba(255, 255, 255, 0.2);
        animation: spin-z-rev 45s linear infinite;
    }
    @keyframes spin-z {
        0%   { transform: translate(-50%, -50%) rotateZ(0deg); }
        100% { transform: translate(-50%, -50%) rotateZ(360deg); }
    }
    @keyframes spin-z-rev {
        0%   { transform: translate(-50%, -50%) rotateZ(360deg); }
        100% { transform: translate(-50%, -50%) rotateZ(0deg); }
    }

    /* Logo image itself */
    .hero-logo {
        display: block;
        position: relative;
        z-index: 15 !important;
        animation:
            descend-logo 0.9s cubic-bezier(0.22,1,0.36,1) both,
            logo-bounce  2.8s ease-in-out 1s infinite,
            logo-glow    3.5s ease-in-out 1s infinite;
    }
    @keyframes descend-logo {
        0%   { opacity: 0; transform: translateY(-60px) scale(0.8); }
        60%  { opacity: 1; transform: translateY(8px) scale(1.04); }
        100% { opacity: 1; transform: translateY(0) scale(1); }
    }
    @keyframes logo-bounce {
        0%,100% { transform: translateY(0)    scale(1); }
        30%     { transform: translateY(-10px) scale(1.04); }
        50%     { transform: translateY(-14px) scale(1.06); }
        70%     { transform: translateY(-6px)  scale(1.02); }
    }
    @keyframes logo-glow {
        0%,100% { filter: drop-shadow(0 0 12px rgba(108,99,255,0.55)); }
        50%     { filter: drop-shadow(0 0 28px rgba(108,99,255,1)) drop-shadow(0 0 50px rgba(6,182,212,0.45)); }
    }
    /* Title / sub descent — untouched, no overflow hidden */
    .hero-title {
        animation: descend-title 1.0s cubic-bezier(0.22,1,0.36,1) 0.15s both;
    }
    @keyframes descend-title {
        0%   { opacity: 0; transform: translateY(-40px); }
        70%  { opacity: 1; transform: translateY(5px); }
        100% { opacity: 1; transform: translateY(0); }
    }
    .hero-sub {
        animation: descend-sub 1.0s cubic-bezier(0.22,1,0.36,1) 0.30s both;
    }
    @keyframes descend-sub {
        0%   { opacity: 0; transform: translateY(-20px); }
        100% { opacity: 1; transform: translateY(0); }
    }
    .main .block-container { position: relative; z-index: 1; }

    /* ── Login card ── */
    [data-testid="stForm"] {
        background: rgba(108,99,255,0.07);
        backdrop-filter: blur(18px);
        padding: 2.5rem;
        border-radius: 18px;
        border: 1px solid rgba(108,99,255,0.25);
        box-shadow: 0 0 40px rgba(108,99,255,0.12);
        animation: float-in 0.8s ease-out forwards;
        transform: translateY(30px);
        opacity: 0;
    }
    @keyframes float-in {
        to { transform: translateY(0); opacity: 1; }
    }

    /* ── Inputs ── */
    [data-baseweb="input"], [data-baseweb="input"] > div, [data-baseweb="base-input"] {
        background-color: rgba(255,255,255,0.05) !important;
        color: #E2E8F0 !important;
        border-radius: 8px !important;
    }
    input { color: #E2E8F0 !important; -webkit-text-fill-color: #E2E8F0 !important; }

    /* ── Hover-glow logo ── */
    .logo-btn {
        display: inline-block;
        border-radius: 50%;
        cursor: pointer;
        transition: box-shadow 0.3s ease, transform 0.3s ease;
        box-shadow: 0 0 25px rgba(108,99,255,0.4);
        animation: logo-pulse 4s ease-in-out infinite;
    }
    .logo-btn:hover {
        box-shadow: 0 0 60px rgba(108,99,255,1), 0 0 100px rgba(108,99,255,0.6);
        transform: scale(1.08);
    }
    @keyframes logo-pulse {
        0%,100% { box-shadow: 0 0 25px rgba(108,99,255,0.4); }
        50%      { box-shadow: 0 0 50px rgba(108,99,255,0.8); }
    }

    /* ── Title font ── */
    .main-header h1, h1 {
        background: linear-gradient(135deg, #a78bfa, #7C3AED, #06B6D4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-family: var(--font-display) !important;
        font-weight: 800;
        font-size: 3.5rem;
        margin: 8px 0 4px;
        letter-spacing: -1px;
    }
    .main-header p { color: #64748b; font-size: 1.1rem; margin: 0; font-family: var(--font-body); }

    /* ── Hide "Press Enter to submit" form helper text ── */
    .stTextInput [data-testid="InputInstructions"],
    small.st-emotion-cache-16idsys,
    [data-testid="stTextInput"] small,
    .st-emotion-cache-16idsys { display: none !important; }

    /* Fix eye icon position in password fields */
    [data-testid="stTextInput"] [data-baseweb="input"] {
        position: relative;
    }
    [data-testid="stTextInput"] button[aria-label="Show password text"],
    [data-testid="stTextInput"] button[aria-label="Hide password text"] {
        position: absolute !important;
        right: 10px !important;
        top: 50% !important;
        transform: translateY(-50%) !important;
        background: transparent !important;
        border: none !important;
        color: #64748b !important;
        z-index: 5;
    }

    /* ── SUPERCHARGED Premium drag-and-drop file uploader ── */
    [data-testid="stFileUploader"] {
        position: relative;
        background: linear-gradient(145deg, rgba(108,99,255,0.05) 0%, rgba(6,182,212,0.03) 100%) !important;
        border: 2px dashed rgba(124,58,237,0.40) !important;
        border-radius: 20px !important;
        padding: 25px 20px !important;
        overflow: hidden;
        transition: all 0.4s cubic-bezier(0.22,1,0.36,1) !important;
        box-shadow: inset 0 0 30px rgba(0,0,0,0.5), 0 0 20px rgba(108,99,255,0.05) !important;
    }
    /* Animated breathing glow background */
    [data-testid="stFileUploader"]::before {
        content: '';
        position: absolute;
        top: -50%; left: -50%;
        width: 200%; height: 200%;
        background: radial-gradient(circle at center, rgba(124,58,237,0.08) 0%, transparent 60%);
        animation: rotate-bg 15s linear infinite;
        pointer-events: none;
        z-index: 0;
    }
    @keyframes rotate-bg {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

    [data-testid="stFileUploader"]:hover {
        border-color: rgba(6,182,212,0.8) !important;
        background: linear-gradient(145deg, rgba(108,99,255,0.08) 0%, rgba(6,182,212,0.08) 100%) !important;
        box-shadow: 0 0 40px rgba(6,182,212,0.25), inset 0 0 30px rgba(6,182,212,0.1) !important;
        transform: translateY(-2px);
    }

    /* Bring dropzone content above background */
    [data-testid="stFileUploaderDropzone"] {
        position: relative;
        z-index: 1;
        background: transparent !important;
        border: none !important;
    }
    
    /* Target the text container */
    [data-testid="stFileUploaderDropzone"] > div {
        color: #e2e8f0 !important;
        font-family: var(--font-body);
    }
    
    /* The small limit text */
    [data-testid="stFileUploaderDropzone"] small,
    [data-testid="stFileUploaderDropzone"] > div > div {
        color: #94a3b8 !important;
        font-size: 0.85rem !important;
        letter-spacing: 0.5px;
    }

    /* Floating glowing cloud icon */
    [data-testid="stFileUploaderDropzone"] svg {
        color: #a78bfa !important;
        width: 42px !important;
        height: 42px !important;
        margin-right: 15px !important;
        filter: drop-shadow(0 0 12px rgba(124,58,237,0.6));
        animation: float-icon 3s ease-in-out infinite;
    }
    @keyframes float-icon {
        0%, 100% { transform: translateY(0); filter: drop-shadow(0 0 12px rgba(124,58,237,0.6)); }
        50% { transform: translateY(-6px); filter: drop-shadow(0 0 25px rgba(6,182,212,0.8)); color: #06B6D4 !important; }
    }

    /* "Browse files" button supercharged */
    [data-testid="stFileUploaderDropzone"] button {
        position: relative;
        overflow: hidden;
        border-radius: 50px !important;
        background:
            linear-gradient(180deg, rgba(255,255,255,0.2) 0%, rgba(255,255,255,0.05) 50%, rgba(0,0,0,0) 51%, rgba(0,0,0,0.1) 100%),
            linear-gradient(160deg, #8B5CF6 0%, #6C3FD6 40%, #4F1FB5 100%) !important;
        color: #ffffff !important;
        font-family: var(--font-body) !important;
        font-size: 0.95rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.8px !important;
        text-transform: uppercase !important;
        border: none !important;
        padding: 0.6rem 1.8rem !important;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.3),
            inset 0 -2px 4px rgba(0,0,0,0.25),
            0 4px 15px rgba(108,63,214,0.5),
            0 0 20px rgba(108,63,214,0.2) !important;
        transition: transform 0.25s ease, box-shadow 0.25s ease !important;
        text-shadow: 0 1px 2px rgba(0,0,0,0.4) !important;
    }
    
    [data-testid="stFileUploaderDropzone"] button::before {
        content: '';
        position: absolute;
        top: -50%; left: -75%;
        width: 50%; height: 200%;
        background: linear-gradient(105deg, transparent 40%, rgba(255,255,255,0.15) 50%, transparent 60%);
        transform: skewX(-15deg);
        animation: glow-sweep-btn 3s ease-in-out infinite;
    }
    @keyframes glow-sweep-btn {
        0% { left: -75%; opacity: 0; }
        20% { opacity: 1; }
        60% { left: 130%; opacity: 1; }
        61% { opacity: 0; }
        100% { left: 130%; opacity: 0; }
    }
    
    [data-testid="stFileUploaderDropzone"] button:hover {
        transform: translateY(-2px) scale(1.03) !important;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.4),
            inset 0 -2px 4px rgba(0,0,0,0.2),
            0 8px 25px rgba(108,63,214,0.7),
            0 0 40px rgba(139,92,246,0.5) !important;
    }
    [data-testid="stFileUploaderDropzone"] button:active {
        transform: scale(0.97) translateY(1px) !important;
        box-shadow: inset 0 2px 6px rgba(0,0,0,0.3), 0 2px 10px rgba(108,63,214,0.4) !important;
    }

    /* ── Top-right login panel ── */
    .login-topbar {
        display: flex;
        justify-content: flex-end;
        align-items: center;
        padding: 8px 0 20px;
    }
    .login-card {
        background: rgba(108,99,255,0.07);
        backdrop-filter: blur(18px);
        border: 1px solid rgba(108,99,255,0.25);
        border-radius: 18px;
        padding: 2rem 2.2rem;
        width: 380px;
        box-shadow: 0 0 40px rgba(108,99,255,0.12);
        animation: float-in 0.7s ease-out both;
    }
    @keyframes float-in {
        from { opacity:0; transform: translateY(-20px); }
        to   { opacity:1; transform: translateY(0); }
    }

    /* ── Team footer ── */
    .team-footer {
        text-align: center;
        margin-top: 48px;
        padding: 20px 0 30px;
        font-family: var(--font-display);
        font-size: 0.9rem;
        font-weight: 700;
        letter-spacing: 4px;
        text-transform: uppercase;
        color: rgba(167,139,250,0.22);
        user-select: none;
        animation: footer-fade 2s ease 0.5s both;
    }
    @keyframes footer-fade {
        from { opacity:0; }
        to   { opacity:1; }
    }


    /* ── Stat cards — staggered entrance + hover ── */
    .stats-row { display:flex; gap:16px; margin-bottom:22px; flex-wrap:wrap; }
    .stat-card {
        position: relative;
        overflow: hidden;
        background: linear-gradient(145deg, rgba(108,99,255,0.13) 0%, rgba(6,182,212,0.06) 100%);
        border: 1px solid rgba(108,99,255,0.28);
        border-radius: 16px;
        flex: 1; min-width: 140px;
        text-align: center;
        padding: 22px 14px 18px;
        transition: transform 0.28s ease, box-shadow 0.28s ease;
        animation: card-rise 0.6s cubic-bezier(0.22,1,0.36,1) both;
        box-shadow: 0 4px 18px rgba(108,63,214,0.10), inset 0 0 20px rgba(108,99,255,0.03);
    }
    /* per-card colored top accent line */
    .stat-card:nth-child(1) { animation-delay:0.05s; border-top:3px solid #7C3AED; }
    .stat-card:nth-child(2) { animation-delay:0.15s; border-top:3px solid #06B6D4; }
    .stat-card:nth-child(3) { animation-delay:0.25s; border-top:3px solid #10B981; }
    .stat-card:nth-child(4) { animation-delay:0.35s; border-top:3px solid #F59E0B; }
    /* ambient orb in card corner */
    .stat-card::before {
        content:'';
        position:absolute; top:-20px; right:-20px;
        width:70px; height:70px;
        background: radial-gradient(circle, rgba(124,58,237,0.12) 0%, transparent 70%);
        pointer-events:none;
    }
    @keyframes card-rise {
        0%   { opacity:0; transform: translateY(24px) scale(0.96); }
        100% { opacity:1; transform: translateY(0) scale(1); }
    }
    .stat-card:hover {
        transform: translateY(-7px) scale(1.03);
        box-shadow: 0 14px 40px rgba(108,63,214,0.40), 0 0 25px rgba(6,182,212,0.15);
    }
    .stat-title {
        font-size: .7rem; color: #94a3b8;
        text-transform: uppercase; letter-spacing: 2.5px;
        margin-bottom: 10px; font-family: var(--font-body); font-weight:600;
    }
    .stat-value {
        font-size: 1.55rem; font-weight: 800;
        background: linear-gradient(90deg, #a78bfa, #06B6D4);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-family: var(--font-display);
    }

    /* ── Summary card — entrance + glow pulse ── */
    .summary-card {
        background: rgba(108,99,255,0.06);
        border: 1px solid rgba(108,99,255,0.2);
        padding: 26px;
        border-radius: 16px;
        font-size: 1.1rem;
        line-height: 1.8;
        border-left: 5px solid #6C63FF;
        box-shadow: 0 0 30px rgba(108,99,255,0.1);
        animation: summary-enter 0.7s cubic-bezier(0.22,1,0.36,1) both, summary-glow 4s ease-in-out 1s infinite;
        transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275), border-left 0.3s ease;
    }
    .summary-card:hover {
        transform: translateY(-4px) scale(1.015);
        border-left: 5px solid #06B6D4;
    }
    @keyframes summary-enter {
        0%   { opacity:0; transform: translateY(18px); }
        100% { opacity:1; transform: translateY(0); }
    }
    @keyframes summary-glow {
        0%,100% { box-shadow: 0 0 30px rgba(108,99,255,0.10); }
        50%     { box-shadow: 0 0 50px rgba(108,99,255,0.25), 0 0 20px rgba(6,182,212,0.08); }
    }

    /* ── Video preview card ── */
    .video-preview-card {
        background: rgba(6,182,212,0.05);
        border: 1px solid rgba(6,182,212,0.25);
        border-radius: 16px;
        padding: 20px;
        margin: 16px 0;
        box-shadow: 0 0 30px rgba(6,182,212,0.10);
        animation: fade-slide-up 0.5s cubic-bezier(0.22,1,0.36,1) both;
    }
    @keyframes fade-slide-up {
        0%   { opacity: 0; transform: translateY(20px); }
        100% { opacity: 1; transform: translateY(0); }
    }
    .video-preview-card iframe {
        border-radius: 10px;
        width: 100%;
        border: none;
    }
    .video-label {
        font-family: var(--font-display);
        font-size: 0.8rem;
        letter-spacing: 2px;
        text-transform: uppercase;
        color: #06B6D4;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .video-label::before {
        content: '';
        display: inline-block;
        width: 8px; height: 8px;
        background: #06B6D4;
        border-radius: 50%;
        box-shadow: 0 0 8px #06B6D4;
        animation: blink-dot 1.4s ease-in-out infinite;
    }
    @keyframes blink-dot {
        0%,100% { opacity: 1; }
        50%      { opacity: 0.3; }
    }

    /* ── Neon input focus ring ── */
    [data-baseweb="input"]:focus-within,
    [data-baseweb="base-input"]:focus-within {
        border-color: rgba(124,58,237,0.70) !important;
        box-shadow: 0 0 0 2px rgba(124,58,237,0.25), 0 0 18px rgba(124,58,237,0.20) !important;
        transition: box-shadow 0.2s ease, border-color 0.2s ease;
    }

    /* ── Neon divider ── */
    hr, .stMarkdown hr {
        border: none !important;
        height: 1px !important;
        background: linear-gradient(90deg, transparent, rgba(124,58,237,0.6), rgba(6,182,212,0.6), transparent) !important;
        margin: 24px 0 !important;
        animation: hr-glow 3s ease-in-out infinite;
    }
    @keyframes hr-glow {
        0%,100% { opacity: 0.6; }
        50%     { opacity: 1; filter: drop-shadow(0 0 6px rgba(124,58,237,0.8)); }
    }

    /* ── Sidebar neon accent ── */
    [data-testid="stSidebar"] {
        background: rgba(6,8,24,0.92) !important;
        border-right: 1px solid rgba(108,99,255,0.18) !important;
        backdrop-filter: blur(20px);
    }
    [data-testid="stSidebar"]::before {
        content: '';
        position: absolute;
        top: 0; left: 0;
        width: 3px; height: 100%;
        background: linear-gradient(180deg, #7C3AED, #06B6D4, #7C3AED);
        animation: sidebar-beam 4s ease-in-out infinite;
    }
    @keyframes sidebar-beam {
        0%,100% { opacity: 0.5; }
        50%     { opacity: 1; box-shadow: 0 0 12px rgba(124,58,237,0.8); }
    }

    /* ── Section markdown headers glow ── */
    h3, .stMarkdown h3 {
        background: linear-gradient(135deg, #c4b5fd, #a78bfa, #818cf8) !important;
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
        font-family: var(--font-display) !important;
        animation: h3-shimmer 6s linear infinite;
        background-size: 200% auto !important;
    }
    @keyframes h3-shimmer {
        0%   { background-position: 0% center; }
        100% { background-position: 200% center; }
    }

    /* ── Radio buttons — premium pill toggle ── */

    /* Container row */
    [data-testid="stRadio"] > div {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: wrap;
        gap: 10px !important;
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(108,99,255,0.15);
        border-radius: 50px;
        padding: 5px 8px;
        width: fit-content;
    }

    /* Hide the native radio dot */
    [data-testid="stRadio"] input[type="radio"] {
        display: none !important;
    }

    /* Each label = pill */
    [data-testid="stRadio"] label {
        position: relative;
        display: flex !important;
        align-items: center;
        gap: 7px;
        cursor: pointer;
        padding: 0.45rem 1.3rem !important;
        border-radius: 50px !important;
        font-family: var(--font-body) !important;
        font-size: 0.88rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.5px;
        color: #94a3b8 !important;
        background: transparent !important;
        border: 1px solid transparent !important;
        transition: color 0.25s ease, background 0.25s ease, box-shadow 0.25s ease, transform 0.2s ease !important;
        user-select: none;
    }

    /* Hover — subtle glow */
    [data-testid="stRadio"] label:hover {
        color: #c4b5fd !important;
        background: rgba(139,92,246,0.10) !important;
        border-color: rgba(139,92,246,0.25) !important;
        transform: scale(1.03);
    }

    /* SELECTED pill container — Original Purple Gloss Glow */
    [data-testid="stRadio"] label[data-selected="true"],
    [data-testid="stRadio"] label:has(input:checked) {
        color: #ffffff !important;
        background:
            linear-gradient(
                180deg,
                rgba(255,255,255,0.28) 0%,
                rgba(255,255,255,0.08) 48%,
                rgba(0,0,0,0.0)        50%,
                rgba(0,0,0,0.15)      100%
            ),
            linear-gradient(160deg, #8B5CF6 0%, #6C3FD6 45%, #4F1FB5 100%) !important;
        border-color: rgba(167,139,250,0.30) !important;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.30),
            inset 0 -2px 4px rgba(0,0,0,0.20),
            0 4px 18px rgba(108,63,214,0.65),
            0 0 30px rgba(108,63,214,0.30) !important;
        text-shadow: 0 1px 3px rgba(0,0,0,0.5);
        transform: scale(1.04);
    }

    /* Target the Streamlit native radio circle (first child of label) */
    [data-testid="stRadio"] label > div:first-child {
        transition: all 0.2s ease;
    }

    /* Small selected circle dot inside the pill — Orange Color */
    [data-testid="stRadio"] label[data-selected="true"] > div:first-child,
    [data-testid="stRadio"] label:has(input:checked) > div:first-child {
        background-color: #F97316 !important;
        border-color: #EA580C !important;
        box-shadow: 0 0 12px #F97316 !important;
    }

    /* Selected pill top gloss arc */
    [data-testid="stRadio"] label[data-selected="true"]::after,
    [data-testid="stRadio"] label:has(input:checked)::after {
        content: '';
        position: absolute;
        top: 0; left: 0;
        width: 100%; height: 50%;
        background: linear-gradient(180deg, rgba(255,255,255,0.18) 0%, transparent 100%);
        border-radius: 50px 50px 0 0;
        pointer-events: none;
    }

    /* Radio group label (question text above) */
    [data-testid="stRadio"] > label {
        color: #64748b !important;
        font-size: 0.8rem !important;
        font-weight: 500 !important;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        margin-bottom: 8px !important;
        background: none !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
    }


    .stButton > button {
        position: relative;
        overflow: hidden;
        border-radius: 50px !important;
        /* Deep purple base */
        background:
            /* top-half white gloss highlight */
            linear-gradient(
                180deg,
                rgba(255,255,255,0.32) 0%,
                rgba(255,255,255,0.10) 48%,
                rgba(0,0,0,0.0)        50%,
                rgba(0,0,0,0.18)      100%
            ),
            /* core purple gradient */
            linear-gradient(160deg, #8B5CF6 0%, #6C3FD6 40%, #4F1FB5 100%) !important;
        color: #ffffff !important;
        border: none !important;
        padding: 0.68rem 2.2rem !important;
        font-family: var(--font-body) !important;
        font-size: 0.95rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.8px !important;
        text-transform: uppercase !important;
        /* layered shadow: depth + outer glow */
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.35),
            inset 0 -2px 4px rgba(0,0,0,0.25),
            0 6px 24px rgba(108,63,214,0.65),
            0 0 40px rgba(108,63,214,0.30),
            0 2px 4px rgba(0,0,0,0.4) !important;
        transition: transform 0.25s ease, box-shadow 0.25s ease !important;
        text-shadow: 0 1px 3px rgba(0,0,0,0.4) !important;
    }
    /* inner gloss arc — pseudo element for top shine */
    .stButton > button::before {
        content: '';
        position: absolute;
        top: 0; left: 0;
        width: 100%; height: 50%;
        background: linear-gradient(
            180deg,
            rgba(255,255,255,0.22) 0%,
            rgba(255,255,255,0.04) 100%
        );
        border-radius: 50px 50px 0 0;
        pointer-events: none;
    }
    /* moving shimmer sweep */
    .stButton > button::after {
        content: '';
        position: absolute;
        top: -50%; left: -75%;
        width: 50%; height: 200%;
        background: linear-gradient(
            105deg,
            transparent 40%,
            rgba(255,255,255,0.18) 50%,
            transparent 60%
        );
        transform: skewX(-15deg);
        animation: glow-sweep 3.2s ease-in-out infinite;
    }
    @keyframes glow-sweep {
        0%   { left: -75%; opacity: 0; }
        20%  { opacity: 1; }
        60%  { left: 130%; opacity: 1; }
        61%  { opacity: 0; }
        100% { left: 130%; opacity: 0; }
    }
    .stButton > button:hover {
        transform: translateY(-3px) scale(1.03) !important;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.40),
            inset 0 -2px 4px rgba(0,0,0,0.20),
            0 8px 32px rgba(108,63,214,0.80),
            0 0 70px rgba(139,92,246,0.55),
            0 2px 6px rgba(0,0,0,0.35) !important;
    }
    .stButton > button:active {
        transform: scale(0.97) translateY(1px) !important;
        box-shadow:
            inset 0 2px 6px rgba(0,0,0,0.35),
            0 2px 10px rgba(108,63,214,0.5) !important;
    }
    /* Primary / Start Processing — slightly brighter glow */
    .stButton > button[kind="primary"] {
        background:
            linear-gradient(
                180deg,
                rgba(255,255,255,0.35) 0%,
                rgba(255,255,255,0.10) 48%,
                rgba(0,0,0,0.0)        50%,
                rgba(0,0,0,0.18)      100%
            ),
            linear-gradient(160deg, #A78BFA 0%, #7C3AED 40%, #5B21B6 100%) !important;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.40),
            inset 0 -2px 4px rgba(0,0,0,0.25),
            0 6px 30px rgba(124,58,237,0.75),
            0 0 55px rgba(167,139,250,0.40),
            0 2px 4px rgba(0,0,0,0.4) !important;
        font-size: 1.0rem !important;
        padding: 0.75rem 2.5rem !important;
    }
    /* Form submit button — same 3D gloss style */
    [data-testid="stFormSubmitButton"] button {
        position: relative;
        overflow: hidden;
        border-radius: 50px !important;
        background:
            linear-gradient(
                180deg,
                rgba(255,255,255,0.30) 0%,
                rgba(255,255,255,0.08) 48%,
                rgba(0,0,0,0.0)        50%,
                rgba(0,0,0,0.18)      100%
            ),
            linear-gradient(160deg, #8B5CF6 0%, #6C3FD6 40%, #4F1FB5 100%) !important;
        color: #fff !important;
        font-family: var(--font-body) !important;
        font-weight: 700 !important;
        letter-spacing: 0.8px !important;
        text-transform: uppercase !important;
        border: none !important;
        padding: 0.68rem 2rem !important;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.35),
            inset 0 -2px 4px rgba(0,0,0,0.25),
            0 6px 24px rgba(108,63,214,0.65),
            0 0 40px rgba(108,63,214,0.30) !important;
        transition: all 0.25s ease !important;
        text-shadow: 0 1px 3px rgba(0,0,0,0.4) !important;
    }
    [data-testid="stFormSubmitButton"] button:hover {
        transform: translateY(-2px) scale(1.02) !important;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.40),
            0 8px 32px rgba(108,63,214,0.80),
            0 0 65px rgba(139,92,246,0.50) !important;
    }
    </style>
    """, unsafe_allow_html=True)

local_css()

# -------------------------------------------------
# Utility: Text-to-Speech JS Component
# -------------------------------------------------
def clean_for_tts(text):
    import re
    # Remove metadata lines and markdown
    text = re.sub(r'#+\s*', '', text) # Headers
    text = re.sub(r'\*+', '', text)   # Bold/Italic
    text = re.sub(r'__+', '', text)   # Underline
    text = re.sub(r'\(Detected Language:.*?\)', '', text) # Language footer
    text = re.sub(r'Audio Transcription Summary \(.*?\)', '', text) # Header text
    # Convert bullet points to simple sentences
    text = re.sub(r'^\s*[-•]\s*', 'Next point: ', text, flags=re.MULTILINE)
    return text.strip()

def tts_horn(text):
    cleaned = clean_for_tts(text)
    safe_text = json.dumps(cleaned)
    html = f"""
    <div style="margin-top:15px;display:flex;gap:12px;flex-wrap:wrap;align-items:center;">

      <!-- PRIMARY: Recite / Pause / Resume -->
      <button id="ttsPlayBtn" onclick="handlePlayPause()"
        style="background:linear-gradient(160deg,#8B5CF6,#4F1FB5);
               color:white;border:none;padding:13px 24px;
               border-radius:50px;cursor:pointer;font-size:15px;
               font-weight:700;display:inline-flex;align-items:center;
               gap:9px;box-shadow:inset 0 1px 0 rgba(255,255,255,0.25),
               0 6px 20px rgba(108,63,214,0.55),0 0 35px rgba(108,63,214,0.25);
               transition:all 0.25s ease;
               letter-spacing:0.5px;text-transform:uppercase;">
        <span id="playIcon">🔊</span>
        <span id="playLabel">Recite Summary</span>
      </button>

      <!-- SECONDARY: Stop Reciting (always visible, resets everything) -->
      <button id="ttsStopBtn" onclick="handleStop()"
        style="background:linear-gradient(160deg,#DC2626,#991B1B);
               color:white;border:none;padding:13px 24px;
               border-radius:50px;cursor:pointer;font-size:15px;
               font-weight:700;display:inline-flex;align-items:center;
               gap:9px;box-shadow:inset 0 1px 0 rgba(255,255,255,0.20),
               0 6px 20px rgba(220,38,38,0.50),0 0 30px rgba(220,38,38,0.20);
               transition:all 0.25s ease;
               letter-spacing:0.5px;text-transform:uppercase;">
        <span>⏹</span>
        <span>Stop Reciting</span>
      </button>

      <script>
        // ── State ──────────────────────────────────────────
        const _TTS_TEXT  = {safe_text};
        let _state       = 'idle';   // 'idle' | 'speaking' | 'paused'
        let _charIndex   = 0;        // where we paused
        let _utterance   = null;

        const _playBtn   = document.getElementById('ttsPlayBtn');
        const _playIcon  = document.getElementById('playIcon');
        const _playLabel = document.getElementById('playLabel');

        // ── Helpers ───────────────────────────────────────
        function setPlayState(state) {{
          _state = state;
          if (state === 'idle') {{
            _playIcon.textContent  = '🔊';
            _playLabel.textContent = 'Recite Summary';
            _playBtn.style.background = 'linear-gradient(160deg,#8B5CF6,#4F1FB5)';
            _playBtn.style.boxShadow   = 'inset 0 1px 0 rgba(255,255,255,0.25),0 6px 20px rgba(108,63,214,0.55),0 0 35px rgba(108,63,214,0.25)';
          }} else if (state === 'speaking') {{
            _playIcon.textContent  = '⏸';
            _playLabel.textContent = 'Pause Reciting';
            _playBtn.style.background = 'linear-gradient(160deg,#F59E0B,#B45309)';
            _playBtn.style.boxShadow   = 'inset 0 1px 0 rgba(255,255,255,0.25),0 6px 20px rgba(245,158,11,0.55),0 0 35px rgba(245,158,11,0.25)';
          }} else if (state === 'paused') {{
            _playIcon.textContent  = '▶';
            _playLabel.textContent = 'Resume Reciting';
            _playBtn.style.background = 'linear-gradient(160deg,#10B981,#065F46)';
            _playBtn.style.boxShadow   = 'inset 0 1px 0 rgba(255,255,255,0.25),0 6px 20px rgba(16,185,129,0.55),0 0 35px rgba(16,185,129,0.25)';
          }}
        }}

        function startFrom(charStart) {{
          const slice = _TTS_TEXT.slice(charStart);
          _utterance  = new SpeechSynthesisUtterance(slice);
          _utterance.onboundary = (e) => {{
            if (e.name === 'word') _charIndex = charStart + e.charIndex;
          }};
          _utterance.onend = () => {{
            _charIndex = 0;
            setPlayState('idle');
          }};
          _utterance.onerror = () => {{
            _charIndex = 0;
            setPlayState('idle');
          }};
          window.speechSynthesis.speak(_utterance);
          setPlayState('speaking');
        }}

        // ── Main toggle ───────────────────────────────────
        function handlePlayPause() {{
          if (_state === 'idle') {{
            _charIndex = 0;
            startFrom(0);
          }} else if (_state === 'speaking') {{
            window.speechSynthesis.pause();
            setPlayState('paused');
          }} else if (_state === 'paused') {{
            // Resume native pause if it works, else restart from saved char
            window.speechSynthesis.resume();
            // Some browsers don't support resume, fall back after 200ms check
            setTimeout(() => {{
              if (!window.speechSynthesis.speaking) {{
                window.speechSynthesis.cancel();
                startFrom(_charIndex);
              }} else {{
                setPlayState('speaking');
              }}
            }}, 200);
          }}
        }}

        // ── Stop resets everything ────────────────────────
        function handleStop() {{
          window.speechSynthesis.cancel();
          _charIndex = 0;
          _utterance = null;
          setPlayState('idle');
        }}
      </script>
    </div>
    """
    st.components.v1.html(html, height=80)

# -------------------------------------------------
# Hero Header  — logo + title with descent animation
# (rendered directly in Streamlit, NOT inside an iframe)
# -------------------------------------------------
# ── Hero Header ──
# Using text-based logo from assets.py to bypass Hugging Face binary restrictions
if LOGO_BASE64:
    logo_tag = f'<img src="data:image/png;base64,{LOGO_BASE64}" class="logo-btn hero-logo" width="180" alt="VSG Logo">'
else:
    logo_tag = '<div class="logo-btn hero-logo" style="font-size:80px;display:inline-block;">🎬</div>'

st.markdown(f"""
<div class="hero-header">
    <div class="stars-bg"></div>
    <div class="hero-logo-wrap">
        <div class="vortex-container">
            <div class="v-ring v1"></div>
            <div class="v-ring v2"></div>
            <div class="v-ring v3"></div>
            <div class="v-ring v4"></div>
        </div>
        <div class="hero-logo-bg"></div>
        <div class="clean-neon-ring outer"></div>
        <div class="clean-neon-ring inner"></div>
        {logo_tag}
    </div>
    <div class="hero-title">
        <h1 style="
            font-family: 'Syne', sans-serif;
            font-size: 4.8rem;
            font-weight: 900;
            text-transform: uppercase;
            margin: 18px 0 6px;
            letter-spacing: 2px;
            background: linear-gradient(90deg, #a78bfa, #7C3AED, #3b82f6, #06B6D4);
            -webkit-background-clip: text;
            color: #060818;
            -webkit-text-stroke: 3px transparent;
            filter: drop-shadow(0 0 10px rgba(124,58,237,0.6)) drop-shadow(0 0 25px rgba(6,182,212,0.4));
        ">Video Summary Generator</h1>
    </div>
    <div class="hero-sub"></div>
</div>
""", unsafe_allow_html=True)

# JS-driven looping typewriter below subtitle
st.components.v1.html("""
<div style="text-align:center;margin:-10px 0 16px;">
  <span id="tw" style="
    font-family:'Inter',sans-serif;
    font-size:0.82rem;
    color:#7C3AED;
    letter-spacing:3px;
    text-transform:uppercase;
    border-right:2px solid #a78bfa;
    padding-right:3px;
    display:inline-block;
    min-height:1.2em;
  "></span>
</div>
<script>
  const phrases = [
    'Transcribe  \u2022  Summarize  \u2022  Understand  \u2022  Explore'
  ];
  const el = document.getElementById('tw');
  let pi = 0, ci = 0, deleting = false;

  function tick() {
    const full = phrases[pi % phrases.length];
    if (!deleting) {
      el.textContent = full.slice(0, ci + 1);
      ci++;
      if (ci === full.length) {
        setTimeout(() => { deleting = true; tick(); }, 2500);
        return;
      }
      setTimeout(tick, 55);
    } else {
      el.textContent = full.slice(0, ci - 1);
      ci--;
      if (ci === 0) {
        deleting = false;
        pi++;
        setTimeout(tick, 400);
        return;
      }
      setTimeout(tick, 28);
    }
  }
  tick();
</script>
""", height=40)


# -------------------------------------------------
# Auth UI
# -------------------------------------------------
if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        mode = st.radio("Mode", ["Login", "Register"], horizontal=True, key="auth_mode")

        with st.form(key="auth_form"):
            st.markdown(f"<h3 style='text-align:center;'>{mode} to VSG</h3>", unsafe_allow_html=True)
            username = st.text_input("Username", placeholder="Enter your username")

            email = None
            if mode == "Register":
                email = st.text_input("Email", placeholder="Enter your email address")

            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submit = st.form_submit_button(mode, use_container_width=True)

            if submit:
                if not username or not password or (mode == "Register" and not email):
                    st.error("Please fill in all required fields.")
                else:
                    endpoint = f"{BACKEND_HTTP}/{mode.lower()}"
                    payload = {"username": username, "password": password}
                    if mode == "Register":
                        payload["email"] = email

                    try:
                        res = requests.post(endpoint, json=payload)
                        if res.status_code == 200:
                            if mode == "Login":
                                st.session_state.logged_in = True
                                st.session_state.username = username
                                st.query_params["user"] = username
                                st.session_state.just_logged_in = True
                                st.rerun()
                            else:
                                st.success("Registration successful! Please login.")
                        else:
                            st.error(res.json().get("detail", "Auth failed"))
                    except Exception:
                        st.error("Cannot connect to backend.")
    st.stop()

st.sidebar.success(f"👤 Logged in as: **{st.session_state.username}**")
if st.sidebar.button("Logout"):
    if "user" in st.query_params:
        del st.query_params["user"]
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()

st.sidebar.markdown("---")
# Determine which label/emoji to show for the ACTIVE selection
active_label = "Gemini LLM" if st.session_state.selected_mode == "gemini" else "Local Models (BART/PEGASUS)"
active_emoji = "🤖" if st.session_state.selected_mode == "gemini" else "🧠"

# Check if the unified backend is online
is_offline = _backend_info.get("label") == "Offline"
status_label = "Offline" if is_offline else active_label
status_emoji = "⚠️" if is_offline else active_emoji

st.sidebar.markdown(f"**Active Engine:**\n\n{status_emoji} {status_label} `:{_backend_info.get('port', '????')}`")

if is_offline:
    if st.sidebar.button("🔄 Retry Connection", use_container_width=True, help="Try to reconnect to the backend"):
        st.session_state.force_redetect = True
        st.rerun()

# ── Unified Mode Switcher ──
target_mode = "gemini" if st.session_state.selected_mode == "local" else "local"
target_label = "Gemini LLM" if target_mode == "gemini" else "Local Models (BART/PEGASUS)"

if st.sidebar.button(f"🚀 Switch to {target_label}", use_container_width=True):
    st.session_state.selected_mode = target_mode
    st.toast(f"Switched to {target_label} engine!")
    st.rerun()

# (Auto-Detect functionality still runs once per session at the top of the file)

st.markdown("---")

if st.session_state.get("just_logged_in"):
    st.components.v1.html("""
    <script>
        let tries = 0;
        const interval = setInterval(function() {
            window.parent.scrollTo(0, 0);
            const containers = window.parent.document.querySelectorAll('.main, [data-testid="stAppViewContainer"], .stApp');
            containers.forEach(c => {
                c.scrollTo(0, 0);
                c.scrollTop = 0;
            });
            const hero = window.parent.document.querySelector('.hero-header');
            if (hero) hero.scrollIntoView({behavior: "smooth", block: "start"});
            
            tries++;
            if (tries > 8) clearInterval(interval);
        }, 100);
    </script>
    """, height=0)
    st.session_state.just_logged_in = False


# -------------------------------------------------
# Input UI
# -------------------------------------------------
mode = st.radio(
    "Select Input Method:",
    ["📁 Upload Video File", "🔗 Paste Video URL"],
    horizontal=True
)

# ── Clear result if mode changed ──
if "previous_mode" not in st.session_state:
    st.session_state.previous_mode = mode

if st.session_state.previous_mode != mode:
    st.session_state.result = None
    st.session_state.error = None
    st.session_state.job_id = None
    st.session_state.running = False
    st.session_state.previous_mode = mode
    # Clear the widgets as well
    st.session_state.widget_key += 1
    st.rerun()

uploaded_file = None
video_url     = None

if mode == "📁 Upload Video File":
    uploaded_file = st.file_uploader("Choose a video file", type=["mp4", "avi", "mov", "mkv", "webm", "flv"], key=f"file_uploader_{st.session_state.widget_key}")
    if uploaded_file:
        st.session_state.last_file_name = uploaded_file.name
        st.session_state.last_url = None
        col_info, col_btn = st.columns([3, 1])
        with col_info:
            st.markdown(
                f"<div style='color:#a78bfa;font-size:0.95rem;padding:6px 0;'>📄 <b>{uploaded_file.name}</b> "
                f"<span style='color:#64748b;font-size:0.85rem;'>({round(uploaded_file.size/1024/1024,2)} MB)</span></div>",
                unsafe_allow_html=True
            )
        with col_btn:
            if st.button(
                "🎬 Hide Preview" if st.session_state.show_video else "🎬 View Video",
                key="toggle_video_upload",
                use_container_width=True
            ):
                st.session_state.show_video = not st.session_state.show_video
                st.rerun()
        # (Badge logic moved to Result Display)
        if st.session_state.show_video:
            st.markdown('<div class="video-preview-card"><div class="video-label">Live Preview</div>', unsafe_allow_html=True)
            st.video(uploaded_file)
            # Hide Preview button directly below the player
            if st.button("🙈 Hide Preview", key="hide_video_upload_below", use_container_width=True):
                st.session_state.show_video = False
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
else:
    col_input, col_clear = st.columns([9, 1])
    with col_input:
        video_url = st.text_input(
            "Enter video URL",
            placeholder="https://vimeo.com/...  •  https://twitter.com/...  •  direct .mp4 link",
            key=f"video_url_input_{st.session_state.widget_key}"
        )
    with col_clear:
        st.markdown('<div style="margin-top: 27px;"></div>', unsafe_allow_html=True)
        if st.button("✖", key=f"clear_url_btn_{st.session_state.widget_key}", help="Clear pasted link"):
            st.session_state.widget_key += 1
            st.rerun()

    # ── Supported platforms chip bar ──
    st.markdown("""
    <div style="margin: 6px 0 4px; display:flex; flex-wrap:wrap; gap:7px; align-items:center;">
      <span style="color:#64748b;font-size:0.75rem;font-weight:600;letter-spacing:1px;text-transform:uppercase;">Works with:</span>
      <span style="background:rgba(6,182,212,0.12);border:1px solid rgba(6,182,212,0.3);color:#06B6D4;border-radius:50px;padding:3px 11px;font-size:0.76rem;font-weight:600;">Vimeo</span>
      <span style="background:rgba(6,182,212,0.12);border:1px solid rgba(6,182,212,0.3);color:#06B6D4;border-radius:50px;padding:3px 11px;font-size:0.76rem;font-weight:600;">Dailymotion</span>
      <span style="background:rgba(6,182,212,0.12);border:1px solid rgba(6,182,212,0.3);color:#06B6D4;border-radius:50px;padding:3px 11px;font-size:0.76rem;font-weight:600;">Twitter / X</span>
      <span style="background:rgba(6,182,212,0.12);border:1px solid rgba(6,182,212,0.3);color:#06B6D4;border-radius:50px;padding:3px 11px;font-size:0.76rem;font-weight:600;">Instagram</span>
      <span style="background:rgba(6,182,212,0.12);border:1px solid rgba(6,182,212,0.3);color:#06B6D4;border-radius:50px;padding:3px 11px;font-size:0.76rem;font-weight:600;">TikTok</span>
      <span style="background:rgba(6,182,212,0.12);border:1px solid rgba(6,182,212,0.3);color:#06B6D4;border-radius:50px;padding:3px 11px;font-size:0.76rem;font-weight:600;">Direct .mp4 link</span>
      <span style="background:rgba(239,68,68,0.10);border:1px solid rgba(239,68,68,0.25);color:#f87171;border-radius:50px;padding:3px 11px;font-size:0.76rem;font-weight:600;">⚠ YouTube (often blocked)</span>
    </div>
    """, unsafe_allow_html=True)

    # Persist the URL immediately into session_state so it survives re-runs
    if video_url and video_url.strip():
        video_url = video_url.strip()
        st.session_state.last_url = video_url
        st.session_state.last_file_name = None

        # Basic URL validation
        is_valid_url = video_url.startswith("http://") or video_url.startswith("https://")
        if not is_valid_url:
            st.warning("⚠️ Please enter a valid URL starting with **https://**")
            video_url = None
        else:
            col_info, col_btn = st.columns([3, 1])
            with col_info:
                st.markdown(
                    f"<div style='color:#06B6D4;font-size:0.9rem;padding:6px 0;'>🔗 {video_url[:70]}{'...' if len(video_url)>70 else ''}</div>",
                    unsafe_allow_html=True
                )
            with col_btn:
                if st.button(
                    "🎬 Hide Preview" if st.session_state.show_video else "🎬 View Video",
                    key="toggle_video_url",
                    use_container_width=True
                ):
                    st.session_state.show_video = not st.session_state.show_video
                    st.rerun()
            if st.session_state.show_video:
                # Convert YouTube watch URL to embed URL
                embed_url = video_url
                if "youtube.com/watch?v=" in video_url:
                    vid_id = video_url.split("v=")[1].split("&")[0]
                    embed_url = f"https://www.youtube.com/embed/{vid_id}"
                elif "youtu.be/" in video_url:
                    vid_id = video_url.split("youtu.be/")[1].split("?")[0]
                    embed_url = f"https://www.youtube.com/embed/{vid_id}"
                st.markdown(
                    f'<div class="video-preview-card">'
                    f'<div class="video-label">Live Preview</div>'
                    f'<iframe src="{embed_url}" height="380" allowfullscreen allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture"></iframe>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                # Hide Preview button directly below the iframe
                if st.button("🙈 Hide Preview", key="hide_video_url_below", use_container_width=True):
                    st.session_state.show_video = False
                    st.rerun()

    # ── Retry button when a URL job failed ──
    if st.session_state.get("error") and not st.session_state.running and st.session_state.get("last_url"):
        st.markdown("""
        <div style="margin: 10px 0 4px; padding: 10px 16px;
            background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.25);
            border-radius: 12px; display: flex; align-items: center; gap: 10px;">
            <span style="font-size:1.1rem;">⚠️</span>
            <span style="color:#f87171; font-size:0.88rem; font-weight:600;">
                Previous URL processing failed. You can retry or paste a new URL.
            </span>
        </div>
        """, unsafe_allow_html=True)
        col_retry, col_new = st.columns(2)
        with col_retry:
            if st.button("🔄 Retry This URL", key="retry_url_btn", use_container_width=True):
                retry_url = st.session_state.last_url
                for k in ["job_id", "running", "progress", "status_msg", "result", "error", "start_time", "poll_count", "just_finished"]:
                    st.session_state[k] = defaults[k]
                st.session_state.running = True
                st.session_state.status_msg = "Initializing..."
                st.session_state.start_time = datetime.now()
                try:
                    response = requests.post(
                        f"{BACKEND_HTTP}/start",
                        data={
                            "url": retry_url, 
                            "summary_format": "paragraph",
                            "mode": st.session_state.selected_mode
                        },
                        timeout=30
                    )
                    response.raise_for_status()
                    st.session_state.job_id = response.json()["job_id"]
                except Exception as e:
                    st.session_state.error = str(e)
                    st.session_state.running = False
                st.rerun()
        with col_new:
            if st.button("✖ Clear & Paste New URL", key="clear_failed_url_btn", use_container_width=True):
                st.session_state.error = None
                st.session_state.result = None
                st.session_state.last_url = None
                st.session_state.widget_key += 1
                st.rerun()

st.markdown("---")

# -------------------------------------------------
# POLL FIRST — so the progress display always shows fresh data
# -------------------------------------------------
if st.session_state.running and st.session_state.job_id:
    try:
        poll_data = requests.get(f"{BACKEND_HTTP}/status/{st.session_state.job_id}", timeout=5).json()
        poll_status = poll_data.get("status", "Processing...")

        if poll_status == "not_found" or poll_data.get("error") == "Job ID not found":
            st.session_state.not_found_count = st.session_state.get("not_found_count", 0) + 1
            if st.session_state.not_found_count >= 3:
                st.session_state.running = False
                st.session_state.error = (
                    "⚠️ The backend lost track of this job (it may have restarted). "
                    "Please click 'Process Another Video' and try again."
                )
                st.session_state.not_found_count = 0
            else:
                st.session_state.status_msg = "Connecting to backend..."
        else:
            st.session_state.not_found_count = 0
            st.session_state.progress   = int(poll_data.get("progress", 0))
            st.session_state.status_msg = poll_status

            # Detect failure from backend
            if poll_status == "Failed" or poll_data.get("error"):
                st.session_state.running = False
                st.session_state.error   = poll_data.get("error", "Unknown error occurred")
            elif st.session_state.progress >= 100:
                st.session_state.result        = poll_data.get("result")
                st.session_state.running       = False
                st.session_state.just_finished  = True
    except Exception as poll_err:
        st.session_state.not_found_count = st.session_state.get("not_found_count", 0) + 1
        if st.session_state.not_found_count >= 5:
            st.session_state.running     = False
            st.session_state.error       = f"Lost connection to backend: {poll_err}"
            st.session_state.not_found_count = 0

# -------------------------------------------------
# Progress display (now shows FRESH data from poll above)
# -------------------------------------------------
if st.session_state.running:
    pct = int(st.session_state.progress)
    status_msg = st.session_state.status_msg or "Processing..."
    
    def get_status_icon(msg: str) -> str:
        msg_lower = msg.lower()
        if "init" in msg_lower: return "⚙️"
        if "prepar" in msg_lower: return "🎞️"
        if "download" in msg_lower: return "☁️"
        if "audio" in msg_lower: return "🎵"
        if "transcrib" in msg_lower: return "📝"
        if "muted" in msg_lower or "frame" in msg_lower: return "📸"
        if "summariz" in msg_lower: return "🧠"
        if "complete" in msg_lower: return "✨"
        if "fail" in msg_lower or "error" in msg_lower: return "❌"
        return "⏳"
        
    icon = get_status_icon(status_msg)

    st.components.v1.html(f"""
<!DOCTYPE html>
<html>
<head>
<style>
  body {{
    margin: 0; padding: 0;
    background: transparent;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    font-family: 'Inter', sans-serif;
  }}
  .status-container {{
    display: flex;
    flex-direction: column;
    align-items: center;
    margin-top: 5px;
  }}
  .status-icon-wrapper {{
    background: rgba(124,58,237,0.15);
    border: 1px solid rgba(124,58,237,0.4);
    border-radius: 50%;
    width: 38px;
    height: 38px;
    display: flex;
    justify-content: center;
    align-items: center;
    font-size: 1.25rem;
    box-shadow: 0 0 15px rgba(124,58,237,0.3);
    margin-bottom: 6px;
    animation: bounce-icon 2s infinite ease-in-out;
  }}
  @keyframes bounce-icon {{
    0%, 100% {{ transform: translateY(0); box-shadow: 0 0 15px rgba(124,58,237,0.3); }}
    50% {{ transform: translateY(-4px); box-shadow: 0 0 25px rgba(124,58,237,0.6); }}
  }}
  .ring-wrapper {{
    position: relative;
    width: 220px;
    height: 220px;
    margin: 0 auto 18px;
  }}
  canvas.wave-ring {{
    position: absolute;
    top: 0; left: 0;
    border-radius: 50%;
    z-index: 1;
  }}
  svg.progress-svg {{
    position: absolute;
    top: 0; left: 0;
    z-index: 5;
  }}
  .inner-circle {{
    position: absolute;
    top: 50%; left: 50%;
    transform: translate(-50%, -50%);
    width: 148px; height: 148px;
    border-radius: 50%;
    background: #0d0d1a;
    border: 2px solid rgba(108,99,255,0.15);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    z-index: 10;
  }}
  .pct-num {{
    font-size: 2.4rem;
    font-weight: 800;
    background: linear-gradient(135deg, #a78bfa, #06B6D4);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    line-height: 1;
  }}
  .pct-sym {{
    font-size: 1rem;
    color: #64748b;
    margin-top: 2px;
  }}
  .status-text {{
    color: #94a3b8;
    font-size: 0.9rem;
    letter-spacing: 1px;
    text-align: center;
    margin-top: 6px;
    max-width: 280px;
    animation: pulse-text 2s ease-in-out infinite;
  }}
  @keyframes pulse-text {{
    0%,100% {{ opacity: 1; }}
    50%      {{ opacity: 0.5; }}
  }}
  .typewriter {{
    overflow: hidden;
    white-space: nowrap;
    border-right: .15em solid #a78bfa;
    margin: 0 auto;
    letter-spacing: .1em;
    animation: typing 3.5s steps(30, end), blink-caret .75s step-end infinite;
  }}
  @keyframes typing {{ from {{ width: 0 }} to {{ width: 100% }} }}
  @keyframes blink-caret {{ from, to {{ border-color: transparent }} 50% {{ border-color: #a78bfa }} }}
</style>
</head>
<body>
  <div class="ring-wrapper">
    <svg class="progress-svg" width="220" height="220" viewBox="0 0 220 220">
      <circle cx="110" cy="110" r="62" fill="none" stroke="rgba(108,99,255,0.15)" stroke-width="10" stroke-linecap="round"/>
      <circle id="arc" cx="110" cy="110" r="62" fill="none" stroke="url(#arcGrad)" stroke-width="10" stroke-linecap="round" stroke-dasharray="389.56" stroke-dashoffset="389.56" transform="rotate(-90 110 110)" style="transition: stroke-dashoffset 0.5s ease; filter: drop-shadow(0 0 8px rgba(6,182,212,1)) drop-shadow(0 0 18px rgba(124,58,237,0.8));"/>
      <circle cx="110" cy="110" r="90" fill="none" stroke="rgba(108,99,255,0.06)" stroke-width="1"/>
      <defs>
        <linearGradient id="arcGrad" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stop-color="#7C3AED"/>
          <stop offset="50%" stop-color="#818cf8"/>
          <stop offset="100%" stop-color="#06B6D4"/>
        </linearGradient>
      </defs>
    </svg>
    <canvas class="wave-ring" id="waveCanvas" width="220" height="220"></canvas>
    <!-- Center display -->
    <div class="inner-circle">
      <span class="pct-num" id="pctNum">0</span>
      <span class="pct-sym">%</span>
    </div>
  </div>

  <div class="status-container">
    <div class="status-icon-wrapper">{icon}</div>
    <div class="status-text" id="statusMsg">{status_msg}</div>
  </div>

<script>
  const TARGET = {pct};
  const CIRCUMFERENCE = 2 * Math.PI * 62; // r=62 inside inner circle → 389.56

  // ── Animate SVG arc ──
  const arc = document.getElementById('arc');
  const numEl = document.getElementById('pctNum');
  let current = 0;

  function animateTo(target) {{
    const step = () => {{
      if (current < target) {{
        current = Math.min(current + 1, target);
        const offset = CIRCUMFERENCE - (current / 100) * CIRCUMFERENCE;
        arc.style.strokeDashoffset = offset;
        numEl.textContent = current;
        requestAnimationFrame(step);
      }}
    }};
    requestAnimationFrame(step);
  }}
  animateTo(TARGET);

  // ── Wavy neon ring on canvas (decorative outer ring) ──
  const canvas = document.getElementById('waveCanvas');
  const ctx = canvas.getContext('2d');
  const cx = 110, cy = 110, BASE_R = 90;

  let t = 0;
  function drawWave() {{
    ctx.clearRect(0, 0, 220, 220);

    // Layer 1 — purple wave
    ctx.beginPath();
    for (let a = 0; a <= Math.PI * 2; a += 0.02) {{
      const noise = Math.sin(a * 6 + t) * 4 + Math.cos(a * 4 - t * 1.3) * 3;
      const r = BASE_R + noise;
      const x = cx + r * Math.cos(a);
      const y = cy + r * Math.sin(a);
      a === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    }}
    ctx.closePath();
    ctx.strokeStyle = 'rgba(124,58,237,0.55)';
    ctx.lineWidth = 2;
    ctx.shadowBlur = 14;
    ctx.shadowColor = 'rgba(124,58,237,0.8)';
    ctx.stroke();

    // Layer 2 — cyan wave (offset phase)
    ctx.beginPath();
    for (let a = 0; a <= Math.PI * 2; a += 0.02) {{
      const noise = Math.sin(a * 5 - t * 1.1) * 5 + Math.cos(a * 7 + t * 0.8) * 2.5;
      const r = BASE_R + noise;
      const x = cx + r * Math.cos(a);
      const y = cy + r * Math.sin(a);
      a === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    }}
    ctx.closePath();
    ctx.strokeStyle = 'rgba(6,182,212,0.50)';
    ctx.lineWidth = 1.5;
    ctx.shadowBlur = 12;
    ctx.shadowColor = 'rgba(6,182,212,0.75)';
    ctx.stroke();

    // Layer 3 — thin violet ripple
    ctx.beginPath();
    for (let a = 0; a <= Math.PI * 2; a += 0.025) {{
      const noise = Math.cos(a * 9 + t * 1.6) * 2.5;
      const r = BASE_R + noise;
      const x = cx + r * Math.cos(a);
      const y = cy + r * Math.sin(a);
      a === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    }}
    ctx.closePath();
    ctx.strokeStyle = 'rgba(167,139,250,0.35)';
    ctx.lineWidth = 1;
    ctx.shadowBlur = 8;
    ctx.shadowColor = 'rgba(167,139,250,0.6)';
    ctx.stroke();

    t += 0.025;
    requestAnimationFrame(drawWave);
  }}
  drawWave();
</script>
</body>
</html>
""", height=360, scrolling=False)

if st.session_state.error:
    err_text = st.session_state.error or ""

    if err_text.startswith("YOUTUBE_BLOCKED:"):
        # ── Premium YouTube-blocked error card ──
        st.markdown("""
        <div style="
            background: linear-gradient(145deg, rgba(239,68,68,0.10) 0%, rgba(124,58,237,0.06) 100%);
            border: 1px solid rgba(239,68,68,0.35);
            border-left: 5px solid #EF4444;
            border-radius: 0 16px 16px 0;
            padding: 22px 26px;
            margin: 12px 0;
            box-shadow: 0 0 30px rgba(239,68,68,0.12), -3px 0 15px rgba(239,68,68,0.2);
            animation: summary-enter 0.5s cubic-bezier(0.22,1,0.36,1) both;
        ">
          <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;">
            <span style="font-size:2rem;">🚫</span>
            <div>
              <div style="font-family:'Syne',sans-serif;font-size:1.15rem;font-weight:800;color:#f87171;">YouTube Has Blocked This Request</div>
              <div style="font-size:0.82rem;color:#94a3b8;margin-top:2px;">YouTube actively prevents automated video access</div>
            </div>
          </div>
          <div style="color:#cbd5e1;font-size:0.95rem;line-height:1.7;margin-bottom:16px;">
            YouTube's bot-protection system detected and blocked the download. This is a known, intentional restriction by YouTube — not a bug in this app.
          </div>
          <div style="font-family:'Syne',sans-serif;font-size:0.78rem;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:#94a3b8;margin-bottom:10px;">✅ What You Can Do Instead</div>
          <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px;">
            <span style="background:rgba(16,185,129,0.15);border:1px solid rgba(16,185,129,0.3);color:#34d399;border-radius:50px;padding:5px 14px;font-size:0.82rem;font-weight:600;">📁 Upload the file directly</span>
            <span style="background:rgba(6,182,212,0.12);border:1px solid rgba(6,182,212,0.3);color:#06B6D4;border-radius:50px;padding:5px 14px;font-size:0.82rem;font-weight:600;">🎬 Vimeo</span>
            <span style="background:rgba(6,182,212,0.12);border:1px solid rgba(6,182,212,0.3);color:#06B6D4;border-radius:50px;padding:5px 14px;font-size:0.82rem;font-weight:600;">📺 Dailymotion</span>
            <span style="background:rgba(6,182,212,0.12);border:1px solid rgba(6,182,212,0.3);color:#06B6D4;border-radius:50px;padding:5px 14px;font-size:0.82rem;font-weight:600;">🐦 Twitter / X</span>
            <span style="background:rgba(6,182,212,0.12);border:1px solid rgba(6,182,212,0.3);color:#06B6D4;border-radius:50px;padding:5px 14px;font-size:0.82rem;font-weight:600;">📸 Instagram</span>
            <span style="background:rgba(6,182,212,0.12);border:1px solid rgba(6,182,212,0.3);color:#06B6D4;border-radius:50px;padding:5px 14px;font-size:0.82rem;font-weight:600;">🎵 TikTok</span>
            <span style="background:rgba(6,182,212,0.12);border:1px solid rgba(6,182,212,0.3);color:#06B6D4;border-radius:50px;padding:5px 14px;font-size:0.82rem;font-weight:600;">🔗 Direct .mp4 URL</span>
          </div>
          <div style="font-size:0.82rem;color:#64748b;border-top:1px solid rgba(255,255,255,0.06);padding-top:12px;">
            💡 <b style="color:#94a3b8;">Pro tip:</b> Download the YouTube video locally using a browser extension, then use <b style="color:#a78bfa;">📁 Upload Video File</b> to process it here.
          </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Generic error
        st.error(f"❌ **Error:** {err_text}")

    if st.button("🔄 Refresh / Paste Again", key="clear_error_btn", use_container_width=True):
        st.session_state.error = None
        st.session_state.running = False
        st.rerun()

# -------------------------------------------------
# Result display
# -------------------------------------------------
if st.session_state.result and not st.session_state.running:
    res = st.session_state.result
    if st.session_state.just_finished:
        # Random celebration — pick one per result
        import random
        _clb = random.choice(["confetti", "sparkle_burst"])

        if _clb == "confetti":
            _cols = ['#a78bfa','#06B6D4','#f59e0b','#f43f5e','#10b981','#818cf8','#fbbf24']
            _pieces = "".join([
                f'<div style="position:absolute;left:{random.randint(0,98)}vw;top:-30px;'
                f'width:{random.randint(8,14)}px;height:{random.randint(14,22)}px;'
                f'background:{random.choice(_cols)};border-radius:2px;opacity:1;'
                f'animation:cf-fall {random.uniform(0.8,1.6):.1f}s {random.uniform(0,0.8):.1f}s ease-in forwards;"></div>'
                for _ in range(80)
            ])
            st.markdown(f"""
<style>
@keyframes cf-fall{{0%{{transform:translateY(0) rotate(0deg);opacity:1;}}100%{{transform:translateY(110vh) rotate(720deg);opacity:0;}}}}
</style>
<div style="position:fixed;top:0;left:0;width:100vw;height:100vh;pointer-events:none;z-index:99999;overflow:hidden;">{_pieces}</div>
""", unsafe_allow_html=True)
        elif _clb == "sparkle_burst":
            _scols2 = ['#a78bfa','#06B6D4','#fbbf24','#f43f5e','#fff','#10b981']
            _sparks = "".join([
                f'<div style="position:absolute;left:{random.randint(5,90)}vw;top:{random.randint(5,80)}vh;'
                f'width:{random.randint(6,14)}px;height:{random.randint(6,14)}px;border-radius:50%;'
                f'background:{random.choice(_scols2)};box-shadow:0 0 12px {random.choice(_scols2)};opacity:1;'
                f'animation:spk-fly {random.uniform(0.3,0.7):.1f}s {random.uniform(0,0.6):.1f}s ease-out forwards;'
                f'transform:translate({random.randint(-30,30)}px,{random.randint(-30,30)}px);"></div>'
                for _ in range(60)
            ])
            st.markdown(f"""
<style>
@keyframes spk-fly{{0%{{transform:translate(0,0) scale(0);opacity:1;}}60%{{opacity:1;}}100%{{transform:translate(var(--tx,80px),var(--ty,-80px)) scale(1);opacity:0;}}}}
</style>
<div style="position:fixed;top:0;left:0;width:100vw;height:100vh;pointer-events:none;z-index:99999;overflow:hidden;">{_sparks}</div>
""", unsafe_allow_html=True)
        st.session_state.just_finished = False

    # ── Premium result header banner ──

    lang = res.get("language", "unknown").upper()
    device = res.get("device", "unknown").upper()
    length = f"{res.get('transcript_length', 0)} chars"
    model = res.get("model_used", "Unknown").split()[0]

    # ── Speech status badge ──
    if "is_silent" in res:
        if res["is_silent"]:
            st.markdown(
                "<div style='margin-bottom:12px;'><span style='display:inline-flex;align-items:center;gap:5px;padding:5px 16px;"
                "background:rgba(6,182,212,0.12);border:1px solid rgba(6,182,212,0.4);"
                "color:#06B6D4;border-radius:50px;font-size:0.8rem;font-weight:700;"
                "letter-spacing:0.5px;'>🔇 SPEECH NOT DETECTED / MUTE</span></div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                "<div style='margin-bottom:12px;'><span style='display:inline-flex;align-items:center;gap:5px;padding:5px 16px;"
                "background:rgba(16,185,129,0.12);border:1px solid rgba(16,185,129,0.4);"
                "color:#10B981;border-radius:50px;font-size:0.8rem;font-weight:700;"
                "letter-spacing:0.5px;'>🔊 SPEECH DETECTED</span></div>",
                unsafe_allow_html=True
            )

    st.markdown(f"""
    <div style="margin-bottom:18px;">
      <h3 style="font-family:'Syne',sans-serif;font-size:1.6rem;font-weight:800;
          color:#a78bfa;margin-bottom:14px;display:flex;align-items:center;gap:8px;">
        ✨ Generated Summary
      </h3>
      <div class="stats-row">
        <div class="stat-card">
          <div class="stat-title">🌐 Language</div>
          <div class="stat-value">{lang}</div>
        </div>
        <div class="stat-card">
          <div class="stat-title">⚡ Engine</div>
          <div class="stat-value">{device}</div>
        </div>
        <div class="stat-card">
          <div class="stat-title">📏 Length</div>
          <div class="stat-value">{length}</div>
        </div>
        <div class="stat-card">
          <div class="stat-title">🧠 Model</div>
          <div class="stat-value">{model}</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    summary_text = res["summary"]
    view_format = st.radio("📝 Choose Summary Format", ["Paragraph", "Bullet Points"], horizontal=True)

    display_text = summary_text

    if view_format == "Bullet Points":
        import re
        lines = summary_text.split('\n')
        bullet_lines = []

        def is_meaningful(text: str) -> bool:
            """Return True only if the text has at least 3 real words and 20+ chars."""
            # Strip all punctuation, quotes, spaces
            stripped = re.sub(r'[^a-zA-Z]', ' ', text).strip()
            words = [w for w in stripped.split() if len(w) > 1]
            return len(words) >= 3 and len(text.strip()) >= 20

        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Section headers → styled header div
            if line.startswith('###'):
                header_text = line.replace('###', '').strip()
                bullet_lines.append(f"<h3 style='margin-top: 20px; margin-bottom: 10px; color: #a78bfa; font-size: 1.2rem;'>{header_text}</h3>")
            elif line.startswith('##'):
                header_text = line.replace('##', '').strip()
                bullet_lines.append(f"<h2 style='margin-top: 20px; margin-bottom: 10px; color: #a78bfa; font-size: 1.4rem;'>{header_text}</h2>")
            elif line.startswith('- ') or line.startswith('• '):
                # Retain the backend's explicit bullet points without duplicating
                text = line[2:].strip()
                bullet_lines.append(f"<div style='display:flex;gap:8px;margin-bottom:5px;'><span style='color:#06B6D4;flex-shrink:0;'>◆</span><span>{text}</span></div>")
            elif line.startswith('**') or line.startswith('🎬') or line.startswith('👁'):
                bullet_lines.append(f"<div style='color:#a78bfa;font-weight:700;margin-top:14px;margin-bottom:6px;font-size:1.05rem;'>{line}</div>")
            else:
                # Split on real sentence boundaries only
                sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z\"\'])', line)
                for s in sentences:
                    s = s.strip().strip('"\'.,;: ')
                    if is_meaningful(s):
                        bullet_lines.append(f"<div style='display:flex;gap:8px;margin-bottom:5px;'><span style='color:#06B6D4;flex-shrink:0;'>◆</span><span>{s}</span></div>")
        display_text = "\n".join(bullet_lines)
    else:
        # Paragraph mode: render markdown properly
        import re
        processed = summary_text
        
        # Convert markdown headers to styled HTML headers
        processed = re.sub(r'(?m)^### (.*?)$', r'<h3 style="margin-top: 20px; margin-bottom: 10px; color: #a78bfa; font-size: 1.2rem;">\1</h3>', processed)
        processed = re.sub(r'(?m)^## (.*?)$', r'<h2 style="margin-top: 20px; margin-bottom: 10px; color: #a78bfa; font-size: 1.4rem;">\1</h2>', processed)
        
        # Convert bold and italics
        processed = re.sub(r'\*\*(.*?)\*\*', r'<strong style="color:#a78bfa;">\1</strong>', processed)
        processed = re.sub(r'(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)', r'<em style="color:#94a3b8;">\1</em>', processed)
        
        # Since this is PARAGRAPH mode, we remove bullet characters and form a cohesive paragraph
        processed = re.sub(r'(?m)^[-•]\s+(.*?)$', r'\1. ', processed)
        
        # Clean up stray newlines between the newly formed list sentences
        processed = re.sub(r'\.\ \n+(?=[A-Za-z])', '. ', processed)
        
        # Convert remaining newlines to breaks, avoiding breaks around HTML elements
        processed = processed.replace('\n\n', '<br><br>').replace('\n', '<br>')
        
        # Clean up stray breaks around headings and list elements
        processed = processed.replace('</h3><br><br>', '</h3>').replace('</h3><br>', '</h3>')
        processed = processed.replace('</h2><br><br>', '</h2>').replace('</h2><br>', '</h2>')
        processed = processed.replace('</div><br>', '</div>')
        
        display_text = processed

    # Premium glowing summary card
    st.markdown(f"""
    <div style="
        position:relative;
        background: linear-gradient(160deg, rgba(108,99,255,0.07) 0%, rgba(6,182,212,0.04) 100%);
        border: 1px solid rgba(108,99,255,0.22);
        border-left: 5px solid;
        border-image: linear-gradient(180deg,#7C3AED,#06B6D4) 1;
        padding: 28px 30px;
        border-radius: 0 18px 18px 0;
        font-size: 1.08rem;
        line-height: 1.9;
        color: #e2e8f0;
        box-shadow: 0 0 40px rgba(108,99,255,0.12), -4px 0 20px rgba(124,58,237,0.2);
        animation: summary-enter 0.7s cubic-bezier(0.22,1,0.36,1) both;
    ">
      <div style="position:absolute;top:14px;right:18px;font-size:1.6rem;opacity:0.12;user-select:none;">❝</div>
      <div style='font-family:"Inter",sans-serif;'>{display_text}</div>
    </div>
    """, unsafe_allow_html=True)
    tts_horn(summary_text)


    st.markdown("<br/>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        # ── Download buttons (TXT + PDF) rendered via HTML component ──
        plain_text = display_text.replace("<br>", "\n").replace("• ", "• ")
        
        # Build a minimal PDF as a data-URI using jsPDF (CDN)
        safe_summary_js = json.dumps(plain_text)
        
        # Use a regular string with .replace() to avoid Pyrefly f-string bugs with JS braces
        html_code = """
        <script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
        <style>
          * { box-sizing: border-box; margin: 0; padding: 0; }
          html, body { margin: 0; padding: 0; background: transparent;
            font-family: 'Inter', sans-serif; overflow: visible; }
          .dropdown {
            position: relative;
            display: block;
            width: 100%;
          }
          .dl-btn {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 8px;
            width: 100%;
            height: 44px;
            border-radius: 50px;
            position: relative;
            overflow: hidden;
            background:
              linear-gradient(180deg,rgba(255,255,255,0.28) 0%,rgba(255,255,255,0.06) 48%,rgba(0,0,0,0) 50%,rgba(0,0,0,0.16) 100%),
              linear-gradient(160deg,#8B5CF6 0%,#6C3FD6 40%,#4F1FB5 100%);
            color:#fff;
            border: none;
            font-size: 0.9rem;
            font-weight: 700;
            letter-spacing: 0.8px;
            text-transform: uppercase;
            cursor: pointer;
            box-shadow:
              inset 0 1px 0 rgba(255,255,255,0.35),
              inset 0 -2px 4px rgba(0,0,0,0.22),
              0 6px 22px rgba(108,63,214,0.60),
              0 0 36px rgba(108,63,214,0.25);
            transform-origin: center center;
            transition: transform 0.22s cubic-bezier(0.22,1,0.36,1),
                        box-shadow 0.22s ease;
          }
          .dl-btn:hover {
            transform: translateY(-4px);
            box-shadow:
              inset 0 1px 0 rgba(255,255,255,0.45),
              inset 0 -2px 4px rgba(0,0,0,0.18),
              0 12px 38px rgba(108,63,214,0.85),
              0 0 80px rgba(139,92,246,0.60);
          }
          .dl-btn:active {
            transform: translateY(1px);
            opacity: 0.9;
          }
          .dropdown-content {
            display: none;
            position: absolute;
            top: 115%; left: 2%; width: 96%;
            background: rgba(17,20,42,0.95);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(167,139,250,0.3);
            border-radius: 12px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.5);
            z-index: 100;
            overflow: hidden;
            animation: slide-down 0.2s ease-out forwards;
          }
          .dropdown.show .dropdown-content { display: block; }
          @keyframes slide-down {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
          }
          .dd-item {
            padding: 12px 16px;
            color: #CBD5E1; cursor: pointer;
            font-weight: 600; font-size: 0.9rem;
            display: flex; align-items: center; gap: 10px;
            transition: all 0.2s;
          }
          .dd-item:hover { background: rgba(124,58,237,0.2); color: #fff; padding-left: 20px; }
          .dd-item:not(:last-child) { border-bottom: 1px solid rgba(255,255,255,0.05); }
          /* Sweep shimmer */
          .dl-btn::after {
            content:'';
            position:absolute; top:-50%; left:-75%;
            width:50%; height:200%;
            background:linear-gradient(105deg,transparent 40%,rgba(255,255,255,0.18) 50%,transparent 60%);
            transform:skewX(-15deg);
            animation:dl-sweep 3s ease-in-out infinite;
          }
          @keyframes dl-sweep {
            0%   { left:-75%; opacity:0; }
            20%  { opacity:1; }
            60%  { left:130%; opacity:1; }
            61%  { opacity:0; }
            100% { left:130%; opacity:0; }
          }
        </style>
        <div class="dropdown" id="dlDrop">
          <button class="dl-btn" onclick="toggleDrop(event)">
            <span>📥 &nbsp;Download Summary</span>
            <span style="font-size:0.8em; margin-left: 4px;">▼</span>
          </button>
          <div class="dropdown-content">
            <div class="dd-item" onclick="downloadTxt(event)">📄 &nbsp;Text Document (.txt)</div>
            <div class="dd-item" onclick="downloadPdf(event)">📑 &nbsp;PDF Document (.pdf)</div>
          </div>
        </div>
        <script>
          function toggleDrop(e) {
            document.getElementById('dlDrop').classList.toggle('show');
          }
          window.onclick = function(e) {
            if (!e.target.closest('.dropdown')) {
              document.getElementById('dlDrop').classList.remove('show');
            }
          }
          const safe_summary = __SUMMARY_DATA__;
          function downloadTxt(e) {
            document.getElementById('dlDrop').classList.remove('show');
            const blob = new Blob([safe_summary], {type:'text/plain'});
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = 'video_summary.txt';
            a.click();
          }
          function downloadPdf(e) {
            document.getElementById('dlDrop').classList.remove('show');
            const { jsPDF } = window.jspdf;
            const doc = new jsPDF({ orientation:'p', unit:'mm', format:'a4' });
            doc.setFont('helvetica','normal');
            doc.setFontSize(12);
            const lines = doc.splitTextToSize(safe_summary, 170);
            doc.setFontSize(16);
            doc.setTextColor(124,58,237);
            doc.text('Video Summary', 20, 20);
            doc.setFontSize(11);
            doc.setTextColor(60,60,80);
            doc.text(lines, 20, 32);
            doc.save('video_summary.pdf');
          }
        </script>
        """
        
        html_code = html_code.replace("__SUMMARY_DATA__", safe_summary_js)
        st.components.v1.html(html_code, height=140)

    with c2:
        if st.button("🔄 Process Another Video", use_container_width=True):
            # Full reset by deleting keys (this prevents StreamlitAPIException on widgets)
            for k in list(st.session_state.keys()):
                if k not in ("logged_in", "username", "widget_key"):
                    del st.session_state[k]
            st.session_state.widget_key += 1
            st.rerun()



# -------------------------------------------------
# Action buttons
# -------------------------------------------------
if not st.session_state.running and not st.session_state.result:
    start_disabled = not uploaded_file and not video_url
    if st.button("🚀 Start Processing", disabled=start_disabled, use_container_width=True, type="primary"):
        for k in ["job_id", "running", "progress", "status_msg", "result", "error", "start_time", "poll_count", "just_finished"]:
            st.session_state[k] = defaults[k]
        st.session_state.running = True
        st.session_state.status_msg = "Initializing..."
        st.session_state.start_time = datetime.now()
        if uploaded_file:
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
        else:
            files = None
            
        data = {
            "summary_format": "paragraph",
            "mode": st.session_state.selected_mode
        }
        if video_url:
            data["url"] = video_url
        try:
            response = requests.post(f"{BACKEND_HTTP}/start", files=files, data=data, timeout=30)
            response.raise_for_status()
            st.session_state.job_id = response.json()["job_id"]
        except Exception as e:
            st.session_state.error = str(e)
            st.session_state.running = False
        st.rerun()

# -------------------------------------------------
# Auto-rerun while job is active (fast polling loop)
# -------------------------------------------------
if st.session_state.running and st.session_state.job_id:
    time.sleep(0.8)
    st.rerun()

# -------------------------------------------------
# Footer
# -------------------------------------------------
# ── Decorative ambient footer animation ──
st.markdown("""
<div style="display: flex; flex-direction: column; align-items: center; margin-top: 40px; margin-bottom: -15px;">
    <div style="width: 2px; height: 35px; background: linear-gradient(180deg, #06B6D4, transparent); animation: scroll-line 2s infinite;"></div>
</div>
<style>
@keyframes scroll-line { 0% { transform: scaleY(0); transform-origin: top; } 50% { transform: scaleY(1); transform-origin: top; } 50.1% { transform: scaleY(1); transform-origin: bottom; } 100% { transform: scaleY(0); transform-origin: bottom; } }
</style>
""", unsafe_allow_html=True)

# ── Team footer ──
st.markdown('<div class="team-footer">✦ &nbsp; DEVELOPED BY TEAM SOT &nbsp; ✦</div>', unsafe_allow_html=True)
