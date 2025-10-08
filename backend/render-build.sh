#!/bin/bash

# Render build script for OpenCV dependencies
set -e

echo "🔧 Installing system dependencies for OpenCV video processing..."

# Install system packages needed for OpenCV video codecs
apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgstreamer1.0-0 \
    libgstreamer-plugins-base1.0-0 \
    libavcodec58 \
    libavformat58 \
    libavutil56 \
    libswscale5 \
    libavresample4

echo "✅ System dependencies installed successfully"

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

echo "🎉 Build completed successfully"