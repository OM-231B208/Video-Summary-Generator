---
title: Video Summary Generator
emoji: 🎬
colorFrom: indigo
colorTo: blue
sdk: docker
pinned: false
---

# 🎬 Video Summary Generator (VSG)

**[🚀 Try the Live Demo here!](https://omsharma1-video-summary-generator.hf.space)**

---

A powerful, AI-driven tool that transforms long videos and URLs into concise, readable summaries. Whether it's a lecture, a meeting, or a movie trailer, VSG helps you get the gist in seconds! 🚀

---

## ✨ Features

*   **Audio Summarization:** Converts speech to text and generates smart summaries. 🎙️
*   **Visual Summarization:** "Watches" muted videos and describes what's happening on screen. 👁️
*   **YouTube Integration:** Instantly fetch transcripts from YouTube links. 📺
*   **Multi-Model Support:** Uses **BART**, **PEGASUS**, and **Google Gemini** for high-quality results. 🧠
*   **Beautiful UI:** Sleek, modern interface with real-time progress tracking. 💎
*   **Export Options:** Download your summaries as **PDF** or **TXT** files. 📄
*   **Text-to-Speech:** Listen to your summaries with the built-in "Recite" feature. 🔊

---

## 🛠️ Tech Stack

- **Backend:** FastAPI, Python, SQLAlchemy
- **Frontend:** Streamlit, Custom CSS/JS
- **AI Models:** OpenAI Whisper, BART-Large-CNN, PEGASUS-XSum, BLIP, Google Gemini
- **Utilities:** FFmpeg, yt-dlp

---

## 🚀 Getting Started

### 1. Prerequisites
Make sure you have **Python 3.10+** and **FFmpeg** installed on your system.

### 2. Clone the Repo
```bash
git clone https://github.com/OM-231B208/Video-Summary-Generator.git
cd Video-Summary-Generator
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Set Up Environment
Create a `.env` file in the root directory and add your API keys:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### 5. Run the App
Start the Backend:
```bash
uvicorn Backend.api:app --reload --port 8000
```
Start the Frontend:
```bash
streamlit run Frontend/app.py
```

---

## 🔒 Privacy & Security
VSG processes your video files **locally** whenever possible, ensuring your data stays private and secure. 🛡️

---

## 🤝 Contributing
Feel free to fork this project and submit pull requests! All contributions are welcome.

---

### **Developed by [OM-231B208](https://github.com/OM-231B208)**
