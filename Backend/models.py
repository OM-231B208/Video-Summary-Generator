# ============================================
# CRITICAL: ENV VARS MUST COME FIRST
# ============================================
import os

os.environ["TRANSFORMERS_FORCE_PYTORCH"] = "1"
os.environ["TRANSFORMERS_NO_TF"] = "1"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

import sys
import io
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ============================================
# Imports AFTER env vars
# ============================================
import re
import torch
import whisper
from transformers import pipeline

# ============================================
# Detect device
# ============================================
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

print(f"[BACKEND] Using device: {DEVICE}")
print(f"[BACKEND] CUDA available: {torch.cuda.is_available()}")

if torch.cuda.is_available():
    print(f"[BACKEND] CUDA device: {torch.cuda.get_device_name(0)}")
    print(f"[BACKEND] CUDA version: {torch.version.cuda}")

# ============================================
# Load Whisper
# ============================================
print(f"[BACKEND] Loading Whisper base model on {DEVICE}...")
whisper_model = whisper.load_model("base", device=DEVICE)
print(f"[BACKEND] ✓ Whisper loaded")


# ============================================
# MODEL 1: PEGASUS-XSUM
# ============================================
print(f"[BACKEND] Loading PEGASUS-xsum (short text specialist)...")

try:
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    model_name = "google/pegasus-xsum"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name).to(DEVICE)
    pegasus_summarizer = pipeline(
        "text2text-generation",
        model=model,
        tokenizer=tokenizer,
        device=0 if DEVICE == "cuda" else -1
    )

    # Freeze positional embeddings (stability hardening)
    for p in pegasus_summarizer.model.model.encoder.embed_positions.parameters():
        p.requires_grad = False
    for p in pegasus_summarizer.model.model.decoder.embed_positions.parameters():
        p.requires_grad = False

    print(f"[BACKEND] ✓ PEGASUS-xsum loaded")
    PEGASUS_AVAILABLE = True

except Exception as e:
    print(f"[BACKEND] ⚠️  PEGASUS failed to load: {e}")
    pegasus_summarizer = None
    PEGASUS_AVAILABLE = False


# ============================================
# MODEL 2: BART-LARGE-CNN
# ============================================
print(f"[BACKEND] Loading BART-large-cnn (long text specialist)...")

try:
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    model_name = "facebook/bart-large-cnn"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name).to(DEVICE)
    bart_summarizer = pipeline(
        "text2text-generation",
        model=model,
        tokenizer=tokenizer,
        device=0 if DEVICE == "cuda" else -1
    )

    # Silence generation warning
    bart_summarizer.model.config.forced_bos_token_id = 0

    print(f"[BACKEND] ✓ BART-large-cnn loaded")
    BART_AVAILABLE = True

except Exception as e:
    print(f"[BACKEND] ❌ BART failed to load: {e}")
    bart_summarizer = None
    BART_AVAILABLE = False


# ============================================
# MODEL 3: BLIP (Salesforce — visual captioning)
# Used by port 8000 (local mode) for silent / visual-only videos
# ============================================
print(f"[BACKEND] Loading BLIP image captioning model (Salesforce/blip-image-captioning-base)...")

try:
    from transformers import BlipProcessor, BlipForConditionalGeneration

    blip_processor = BlipProcessor.from_pretrained(
        "Salesforce/blip-image-captioning-base",
        use_fast=True
    )
    blip_model = BlipForConditionalGeneration.from_pretrained(
        "Salesforce/blip-image-captioning-base",
        torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32
    ).to(DEVICE)
    blip_model.eval()

    print(f"[BACKEND] ✓ BLIP image captioning loaded on {DEVICE}")
    BLIP_AVAILABLE = True

except Exception as e:
    print(f"[BACKEND] ⚠️  BLIP failed to load: {e}")
    blip_processor = None
    blip_model     = None
    BLIP_AVAILABLE = False


# ============================================
# Print final model status
# ============================================
print(f"[BACKEND] ============================================")
print(f"[BACKEND] MODEL SETUP COMPLETE:")
print(f"[BACKEND]   Whisper  : ✓ Ready")
print(f"[BACKEND]   PEGASUS  : {'✓ Ready' if PEGASUS_AVAILABLE else '✗ Unavailable'}")
print(f"[BACKEND]   BART     : {'✓ Ready' if BART_AVAILABLE else '✗ Unavailable'}")
print(f"[BACKEND]   BLIP     : {'✓ Ready (visual captioning)' if BLIP_AVAILABLE else '✗ Unavailable'}")
print(f"[BACKEND] ============================================")


# ============================================
# Simple extractive fallback (no model needed)
# ============================================
def simple_summary(text: str, max_sentences: int = 5) -> str:
    sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
    result = ". ".join(sentences[:max_sentences])
    return result + "." if result else text[:500]


# ============================================
# Exports
# ============================================
short_summarizer = pegasus_summarizer
long_summarizer  = bart_summarizer
summarizer       = bart_summarizer if BART_AVAILABLE else pegasus_summarizer

__all__ = [
    "whisper_model",
    "short_summarizer",
    "long_summarizer",
    "summarizer",
    "DEVICE",
    "simple_summary",
    "PEGASUS_AVAILABLE",
    "BART_AVAILABLE",
    "BLIP_AVAILABLE",
    "blip_processor",
    "blip_model",
]