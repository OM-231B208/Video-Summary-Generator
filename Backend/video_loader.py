import subprocess
import uuid
import os

def download_video_from_link(url: str) -> str:
    """
    Downloads full video using yt-dlp.
    Returns local video path.
    """
    filename = f"{uuid.uuid4()}.mp4"

    command = [
        "yt-dlp",
        "-f", "best",
        "-o", filename,
        url
    ]

    subprocess.run(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True
    )

    if not os.path.exists(filename):
        raise RuntimeError("Video download failed")

    return filename
