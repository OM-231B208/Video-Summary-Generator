'''import os
from transcriber import extract_audio, transcribe_audio
from summarizer import summarize_text
from utils import enhanced_summarize, format_summary
from video_loader import download_audio_from_link


def video_to_summary(
    source: str,
    source_type: str,
    summary_format: str,
    use_gpu: bool,
    progress_callback=None
) -> tuple[str, str, str]:

    audio_path = None

    def check_cancel():
        if progress_callback:
            progress_callback(0, "")  # triggers cancel check

    try:
        if progress_callback:
            progress_callback(10, "Preparing input...")

        check_cancel()

        # STEP 1: audio acquisition
        if source_type == "url":
            audio_path = download_audio_from_link(source)
        else:
            audio_path = extract_audio(source)

        if progress_callback:
            progress_callback(35, "Transcribing with Whisper (base)...")

        check_cancel()

        transcript, language, device_used = transcribe_audio(
            audio_path,
            model_size="base",
            use_gpu=use_gpu
        )

        if progress_callback:
            progress_callback(70, "Summarizing with Transformers (BART)...")

        check_cancel()

        summary = enhanced_summarize(
            transcript,
            summarize_func=summarize_text
        )

        formatted = format_summary(summary, summary_format)

        if progress_callback:
            progress_callback(100, "Completed")

        return formatted, language, device_used

    finally:
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
'''