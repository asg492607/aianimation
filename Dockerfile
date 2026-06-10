FROM python:3.11-slim

# Install system dependencies (FFmpeg, espeak for fallback TTS)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    espeak \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the backend requirements and install
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend code into /app
COPY backend/ .

# Expose port for FastAPI
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
