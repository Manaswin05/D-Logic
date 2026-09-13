#!/bin/bash
# Build script for Render deployment
set -e

echo "==> Building React frontend..."
npm install --include=dev
npm run build

echo "==> Installing Python dependencies..."
pip install -r requirements.txt

echo "==> Build complete!"
