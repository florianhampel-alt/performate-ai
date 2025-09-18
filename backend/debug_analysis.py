#!/usr/bin/env python3
"""
Quick debug script to test the analysis endpoint locally
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

import asyncio
import logging
from app.config.base import settings
from app.services.ai_vision_service import ai_vision_service

# Set up logging to see what's happening
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_analysis():
    """Test the analysis with a dummy request"""
    try:
        print("🔧 DEBUGGING AI ANALYSIS")
        print(f"AI Analysis enabled: {ai_vision_service.ai_analysis_enabled}")
        print(f"OpenAI API Key present: {bool(settings.OPENAI_API_KEY)}")
        print(f"OpenAI API Key length: {len(settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else 0}")
        
        # Check if we can at least initialize without crashing
        print("✅ AI Vision Service initialized successfully")
        
        # Try to analyze a dummy video (this will likely fail but we'll see where)
        test_analysis_id = "test-debug-12345"
        
        print(f"🎯 Testing analysis for ID: {test_analysis_id}")
        
        # This will probably fail, but let's see the exact error
        result = await ai_vision_service.analyze_climbing_video(
            "/nonexistent/test.mp4",
            test_analysis_id,
            "climbing"
        )
        
        print("✅ Analysis completed successfully")
        print(f"Result keys: {list(result.keys())}")
        
    except Exception as e:
        print(f"❌ Analysis failed with error: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_analysis())