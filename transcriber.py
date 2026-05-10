import whisper
import torch
import os
import subprocess

_whisper_models = {}

def extract_audio(video_path: str, audio_path: str = "temp_audio.wav") -> str:
    if os.path.exists(audio_path):
        os.remove(audio_path)

    command = [
        "ffmpeg",
        "-i", video_path,
        "-q:a", "0",
        "-map", "a",
        "-ac", "1",
        audio_path,
        "-y"
    ]

    subprocess.run(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True
    )
    return audio_path


def transcribe_audio(
    audio_path: str,
    model_size: str = "base",
    use_gpu: bool = False
) -> tuple[str, str, str]:

    if use_gpu:
        if not torch.cuda.is_available():
            raise RuntimeError("GPU requested but CUDA is NOT available")
        device = "cuda"
    else:
        device = "cpu"

    cache_key = f"{model_size}_{device}"

    if cache_key not in _whisper_models:
        _whisper_models[cache_key] = whisper.load_model(
            model_size,
            device=device
        )

    model = _whisper_models[cache_key]

    result = model.transcribe(
        audio_path,
        fp16=(device == "cuda")
    )

    return result["text"], result.get("language", "unknown"), device
