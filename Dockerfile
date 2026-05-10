# Use a professional Python 3.10 image
FROM python:3.10-slim

# Install system dependencies (FFmpeg is critical for VSG)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set up a new user named "user" with user ID 1000
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
	PATH=/home/user/.local/bin:$PATH

# Set working directory
WORKDIR $HOME/app

# Copy requirements first for better caching
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY --chown=user . .

# Create necessary directories
RUN mkdir -p temp_uploads

# Expose the port Streamlit uses (Hugging Face expects 7860)
EXPOSE 7860

# Ensure the run script is executable
RUN chmod +x run.sh

# Use a shell script to start both Backend and Frontend
CMD ["sh", "run.sh"]
