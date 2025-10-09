"""
Diagnostic script to test deployment environment
"""
import sys
import os

print("=== DIAGNOSTIC START ===")
print(f"Python version: {sys.version}")
print(f"Python path: {sys.path}")
print(f"Current working directory: {os.getcwd()}")

# Test basic imports
try:
    import fastapi
    print("✅ FastAPI import successful")
except Exception as e:
    print(f"❌ FastAPI import failed: {e}")

try:
    import uvicorn
    print("✅ Uvicorn import successful")
except Exception as e:
    print(f"❌ Uvicorn import failed: {e}")

try:
    import openai
    print("✅ OpenAI import successful")
except Exception as e:
    print(f"❌ OpenAI import failed: {e}")

try:
    import cv2
    print("✅ OpenCV import successful")
except Exception as e:
    print(f"❌ OpenCV import failed: {e}")

# Test app imports
try:
    from app.utils.logger import get_logger
    print("✅ Logger import successful")
except Exception as e:
    print(f"❌ Logger import failed: {e}")

try:
    from app.config.base import settings
    print("✅ Settings import successful")
except Exception as e:
    print(f"❌ Settings import failed: {e}")

try:
    from app.services.video_processing import get_video_processing_service
    print("✅ Video processing import successful")
except Exception as e:
    print(f"❌ Video processing import failed: {e}")
    import traceback
    print(f"Traceback: {traceback.format_exc()}")

try:
    from app.services.ai_vision_service import AIVisionService
    print("✅ AI vision service import successful")
except Exception as e:
    print(f"❌ AI vision service import failed: {e}")
    import traceback
    print(f"Traceback: {traceback.format_exc()}")

try:
    from app.main import app
    print("✅ Main app import successful")
except Exception as e:
    print(f"❌ Main app import failed: {e}")
    import traceback
    print(f"Traceback: {traceback.format_exc()}")

print("=== DIAGNOSTIC END ===")