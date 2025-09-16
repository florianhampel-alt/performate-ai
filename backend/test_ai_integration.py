#!/usr/bin/env python3
"""
Test script for AI Vision integration
Tests the complete pipeline: frame extraction -> GPT-4 Vision -> overlay generation
"""

import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, '/Users/florianhampel/performate-ai/backend')

from app.services.ai_vision_service import ai_vision_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def test_ai_integration():
    """Test AI integration with a sample climbing video"""
    print("🚀 Testing AI Vision Integration...")
    
    # Test with existing uploaded video
    analysis_id = "3bf0cc62-1f76-469e-a920-0d37f466a50f"
    video_path = f"/videos/{analysis_id}"
    
    try:
        print(f"📺 Analyzing video: {video_path}")
        print(f"📊 Analysis ID: {analysis_id}")
        
        # Run AI analysis
        result = await ai_vision_service.analyze_climbing_video(
            video_path=video_path,
            analysis_id=analysis_id,
            sport_type="climbing"
        )
        
        print("✅ AI Analysis Results:")
        print(f"   Sport Type: {result.get('sport_type')}")
        print(f"   AI Confidence: {result.get('ai_confidence', 'N/A')}")
        print(f"   Route Detected: {result.get('route_analysis', {}).get('route_detected')}")
        print(f"   Performance Score: {result.get('performance_score')}")
        print(f"   Has Overlay: {result.get('overlay_data', {}).get('has_overlay')}")
        
        overlay_data = result.get('overlay_data', {})
        if overlay_data.get('has_overlay'):
            elements = overlay_data.get('elements', [])
            print(f"   Overlay Elements: {len(elements)}")
            for i, element in enumerate(elements[:3]):  # Show first 3
                print(f"     Element {i+1}: {element.get('type')}")
        
        insights = result.get('route_analysis', {}).get('key_insights', [])
        if insights:
            print("🔍 AI Insights:")
            for insight in insights[:3]:  # Show first 3
                print(f"   • {insight}")
        
        recommendations = result.get('recommendations', [])
        if recommendations:
            print("💡 AI Recommendations:")
            for rec in recommendations[:3]:  # Show first 3
                print(f"   • {rec}")
        
        print("🎉 AI Integration Test Completed Successfully!")
        return True
        
    except Exception as e:
        print(f"❌ AI Integration Test Failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_ai_integration())
    exit(0 if success else 1)