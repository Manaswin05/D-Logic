# ── Python / Flask runtime ────────────────────────────────────────
FROM python:3.11-slim

# Install system libs required by OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python deps and install
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py ./

# Copy pre-built React frontend (already built locally)
COPY dist/ ./dist/

# Hugging Face Spaces requires port 7860
ENV PORT=7860

# Expose the port HF Spaces expects
EXPOSE 7860

# Start gunicorn (same command as Render Procfile)
CMD ["gunicorn", "app:app", \
     "--bind", "0.0.0.0:7860", \
     "--workers", "1", \
     "--threads", "2", \
     "--timeout", "120", \
     "--log-level", "info"]
