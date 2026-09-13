# ── Build React Frontend ─────────────────────────────────────
FROM node:18-alpine AS frontend-builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

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

# Copy pre-built React frontend from builder stage
COPY --from=frontend-builder /app/dist ./dist/

# Set PORT environment variable (default to 10000 for local, Render provides its own)
ENV PORT=10000
EXPOSE $PORT

# Start gunicorn (same command as Render Procfile)
CMD ["sh", "-c", "gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 2 --timeout 120 --log-level info"]
