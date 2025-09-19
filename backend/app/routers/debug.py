"""
Debug endpoints for development and testing
These endpoints should NOT be included in production deployments
"""

import uuid
import os
import tempfile
import cv2
import numpy as np
from fastapi import APIRouter, HTTPException
from app.config.base import settings
from app.services.redis_service import redis_service
from app.utils.logger import get_logger

# Import video_storage - avoid circular import
# We'll import it inside functions where needed

logger = get_logger(__name__)
router = APIRouter(prefix="/debug", tags=["Debug"])

@router.get("/ai")
async def debug_ai():
    """Debug AI services availability"""
    try:
        from app.services.ai_vision_service import ai_vision_service
        from app.services.frame_extraction_service import frame_extraction_service
        import cv2
        import openai
        
        return {
            "ai_vision_service_available": True,
            "frame_extraction_available": True, 
            "opencv_version": cv2.__version__,
            "openai_available": True,
            "openai_api_key_configured": bool(settings.OPENAI_API_KEY),
            "status": "AI services ready"
        }
    except ImportError as e:
        return {
            "ai_vision_service_available": False,
            "frame_extraction_available": False,
            "error": str(e),
            "status": "AI services unavailable"
        }
    except Exception as e:
        return {
            "ai_vision_service_available": False,
            "error": str(e),
            "status": "AI services error"
        }

@router.get("/ai-test")
async def test_ai_simple():
    """Test AI analysis with simple mock data"""
    try:
        from app.services.ai_vision_service import ai_vision_service
        
        # Create a simple test
        result = {
            "ai_services_working": True,
            "test_result": "AI vision service initialized successfully",
            "model": ai_vision_service.model,
            "max_tokens": ai_vision_service.max_tokens
        }
        
        return result
        
    except Exception as e:
        return {
            "ai_services_working": False,
            "error": str(e)
        }

@router.post("/test-moves")
async def test_move_extraction():
    """Debug endpoint to test move count extraction with fresh AI analysis"""
    try:
        from app.services.ai_vision_service import ai_vision_service
        import uuid
        
        # Create a test analysis ID
        test_id = f"movetest_{uuid.uuid4().hex[:8]}"
        
        logger.warning(f"🔧 MOVE DEBUG: Starting test for {test_id}")
        
        # Test the AI analysis with dummy data to force AI call
        result = await ai_vision_service.analyze_climbing_video(
            video_path="dummy_for_move_test",
            analysis_id=test_id,
            sport_type="bouldering"
        )
        
        # Extract the key data we need
        route_analysis = result.get('route_analysis', {})
        total_moves = route_analysis.get('total_moves')
        ideal_route = route_analysis.get('ideal_route', [])
        
        logger.warning(f"🔧 MOVE DEBUG: Result - total_moves: {total_moves}, route_points: {len(ideal_route)}")
        
        return {
            "test_id": test_id,
            "ai_enabled": ai_vision_service.ai_analysis_enabled,
            "total_moves": total_moves,
            "route_points_count": len(ideal_route),
            "performance_score": result.get('performance_score'),
            "key_insights": route_analysis.get('key_insights', []),
            "debug_message": "Check logs for detailed AI response and move extraction logs"
        }
        
    except Exception as e:
        logger.error(f"🔧 MOVE DEBUG: Test failed - {str(e)}")
        import traceback
        logger.error(f"🔧 MOVE DEBUG: Traceback - {traceback.format_exc()}")
        return {"error": str(e)}

@router.get("/cache/{analysis_id}")
async def debug_cache_analysis(analysis_id: str):
    """Debug endpoint to investigate analysis caching issues"""
    try:
        import datetime
        
        logger.warning(f"🔍 CACHE DEBUG: Investigating {analysis_id}")
        
        # Check what's in Redis cache
        cached_result = await redis_service.get_cached_analysis(analysis_id)
        
        # Check what's in memory storage
        from app.main import video_storage
        memory_data = video_storage.get(analysis_id, {})
        
        return {
            "analysis_id": analysis_id,
            "timestamp": datetime.datetime.now().isoformat(),
            "cached_data": {
                "exists": cached_result is not None,
                "total_moves": cached_result.get('route_analysis', {}).get('total_moves') if cached_result else None,
                "cache_key": f"analysis:{analysis_id}",
                "performance_score": cached_result.get('performance_score') if cached_result else None
            },
            "memory_data": {
                "exists": analysis_id in video_storage,
                "filename": memory_data.get('filename'),
                "size_mb": memory_data.get('size', 0) / (1024*1024) if memory_data.get('size') else 0,
                "storage_type": memory_data.get('storage_type')
            }
        }
        
    except Exception as e:
        logger.error(f"🔍 CACHE DEBUG failed for {analysis_id}: {str(e)}")
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc()}

@router.post("/clear-cache")
async def clear_all_cache():
    """Clear all caches for testing - use with caution"""
    try:
        cleared_count = 0
        
        # Clear Redis cache patterns
        try:
            # Get all analysis keys
            keys = await redis_service.get_all_keys()
            analysis_keys = [key for key in keys if key.startswith('analysis:')]
            
            for key in analysis_keys:
                await redis_service.delete(key)
                cleared_count += 1
                
            logger.warning(f"🗾 CACHE CLEARED: Removed {cleared_count} analysis entries from Redis")
        except Exception as redis_err:
            logger.warning(f"Redis cache clear failed: {redis_err}")
        
        # Clear memory storage 
        from app.main import video_storage
        memory_cleared = len(video_storage)
        video_storage.clear()
        logger.warning(f"🗾 MEMORY CLEARED: Removed {memory_cleared} video entries from memory")
        
        return {
            "success": True,
            "redis_keys_cleared": cleared_count,
            "memory_entries_cleared": memory_cleared,
            "message": "All caches cleared successfully",
            "warning": "This will cause regeneration of all analyses on next request"
        }
        
    except Exception as e:
        logger.error(f"Cache clear failed: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/videos")
async def debug_videos():
    """Debug endpoint to list all stored videos"""
    import datetime
    from app.main import video_storage
    
    return {
        "video_storage_count": len(video_storage),
        "stored_video_ids": list(video_storage.keys()),
        "video_details": {
            video_id: {
                "storage_type": info.get("storage_type"),
                "filename": info.get("filename"),
                "size_mb": info.get("size", 0) / (1024 * 1024) if info.get("size") else 0,
                "s3_key": info.get("s3_key", "N/A")
            }
            for video_id, info in video_storage.items()
        },
        "server_time": datetime.datetime.now().isoformat()
    }
