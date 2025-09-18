"""
FastAPI Entry Point for Performate AI
"""

import uuid
import os
import tempfile
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from app.config.base import settings
from app.services.redis_service import redis_service
from app.services.s3_service import s3_service
# Removed: from app.services.video_analysis_service import video_analysis_service  # Using ai_vision_service instead
from app.utils.logger import get_logger

# Import AI test router
try:
    from app.routers.ai_test import router as ai_test_router
    AI_TEST_AVAILABLE = True
except ImportError as e:
    logger.warning(f"AI test router not available: {e}")
    AI_TEST_AVAILABLE = False
# from app.analyzers.climbing_analyzer import ClimbingPoseAnalyzer  # Disabled for deployment

# In-memory video storage for fallback when S3 is not available
video_storage = {}  # Used only when S3 is disabled
last_upload_info = {"count": 0, "last_time": None, "last_id": None}  # Debug tracking

logger = get_logger(__name__)

app = FastAPI(
    title="Performate AI API",
    description="AI-powered sports performance analysis with video overlays",
    version="1.1.0"
)

# CORS middleware - Allow all origins to fix Vercel deployment CORS issues
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins - required for Vercel preview deployments
    allow_credentials=False,  # Must be False when allow_origins=["*"]
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=86400  # Cache preflight response for 24 hours
)

# Include AI test router if available
if AI_TEST_AVAILABLE:
    app.include_router(ai_test_router, tags=["AI Testing"])
    logger.info("AI test router included")
else:
    logger.warning("AI test router not available")

@app.get("/")
async def root():
    return {"message": "Performate AI API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/debug/ai")
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

@app.get("/debug/ai-test")
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

@app.post("/debug/test-moves")
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
            "debug_message": "Check Render logs for detailed AI response and move extraction logs"
        }
        
    except Exception as e:
        logger.error(f"🔧 MOVE DEBUG: Test failed - {str(e)}")
        import traceback
        logger.error(f"🔧 MOVE DEBUG: Traceback - {traceback.format_exc()}")
        return {"error": str(e)}

@app.get("/debug/cache/{analysis_id}")
async def debug_cache_analysis(analysis_id: str):
    """Debug endpoint to investigate analysis caching issues"""
    try:
        import datetime
        import tempfile
        import os
        
        logger.warning(f"🔍 CACHE DEBUG: Investigating {analysis_id}")
        
        # Check what's in Redis cache
        cached_result = await redis_service.get_cached_analysis(analysis_id)
        
        # Check what's in memory storage
        memory_data = video_storage.get(analysis_id, {})
        
        # Generate a fresh analysis using new frame extraction and AI analysis logic
        from app.services.ai_vision_service import ai_vision_service
        from app.services.frame_extraction_service import frame_extraction_service
        import cv2
        import numpy as np
        
        fresh_analysis = None
        frame_debug_info = {}
        
        try:
            logger.warning(f"🔍 Generating fresh analysis with frame extraction for comparison...")
            
            # Create a synthetic video for testing (since original video might not exist)
            # This simulates different video content to test the AI analysis variability
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_video:
                # Create a simple test video with different patterns
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                out = cv2.VideoWriter(temp_video.name, fourcc, 30.0, (640, 480))
                
                # Generate frames with varying patterns based on analysis_id
                seed = hash(analysis_id) % 1000
                np.random.seed(seed)
                
                for i in range(150):  # 5 seconds at 30 fps
                    # Create varied frame content based on analysis_id and frame number
                    frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
                    
                    # Add some climbing-like shapes/patterns
                    cv2.rectangle(frame, (100 + (i//10)*20, 100), (200 + (i//10)*20, 300), (255, 255, 255), -1)
                    cv2.circle(frame, (300 + seed//10, 200 + (i//20)*10), 30, (0, 255, 0), -1)
                    
                    out.write(frame)
                
                out.release()
                temp_video_path = temp_video.name
            
            # Extract frames using the new frame extraction service
            frames_data = await frame_extraction_service.extract_frames(
                video_path=temp_video_path,
                analysis_id=f"debug_{analysis_id}",
                frame_interval=1.0
            )
            
            frame_debug_info = {
                "frames_extracted": len(frames_data.get('frame_paths', [])),
                "extraction_successful": frames_data.get('success', False),
                "frame_interval": frames_data.get('frame_interval', 'unknown')
            }
            
            logger.warning(f"🔍 Extracted {len(frames_data.get('frame_paths', []))} frames for debug analysis")
            
            # Perform AI analysis on extracted frames
            if frames_data.get('success') and frames_data.get('frame_paths'):
                fresh_analysis = await ai_vision_service.analyze_extracted_frames(
                    frame_paths=frames_data['frame_paths'],
                    analysis_id=f"debug_{analysis_id}",
                    sport_type="bouldering"
                )
                
                logger.warning(f"🔍 Fresh analysis completed - total_moves: {fresh_analysis.get('route_analysis', {}).get('total_moves')}")
            else:
                logger.warning(f"🔍 Frame extraction failed, falling back to mock analysis")
                fresh_analysis = {
                    "route_analysis": {"total_moves": 10},
                    "performance_score": 70,
                    "debug_note": "Frame extraction failed - using fallback"
                }
            
            # Clean up temporary video
            try:
                os.unlink(temp_video_path)
            except:
                pass
                
        except Exception as fresh_err:
            logger.error(f"🔍 Fresh analysis failed: {fresh_err}")
            import traceback
            logger.error(f"🔍 Fresh analysis traceback: {traceback.format_exc()}")
        
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
            },
            "frame_debug": frame_debug_info,
            "fresh_analysis": {
                "generated": fresh_analysis is not None,
                "total_moves": fresh_analysis.get('route_analysis', {}).get('total_moves') if fresh_analysis else None,
                "performance_score": fresh_analysis.get('performance_score') if fresh_analysis else None,
                "debug_note": fresh_analysis.get('debug_note') if fresh_analysis else None
            },
            "comparison": {
                "moves_match": (
                    cached_result and fresh_analysis and 
                    cached_result.get('route_analysis', {}).get('total_moves') == 
                    fresh_analysis.get('route_analysis', {}).get('total_moves')
                ) if cached_result and fresh_analysis else None,
                "score_match": (
                    cached_result and fresh_analysis and
                    cached_result.get('performance_score') == fresh_analysis.get('performance_score')
                ) if cached_result and fresh_analysis else None
            }
        }
        
    except Exception as e:
        logger.error(f"🔍 CACHE DEBUG failed for {analysis_id}: {str(e)}")
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc()}

@app.get("/debug/test-variability")
async def test_ai_variability():
    """Test if AI analysis produces varied results with different synthetic videos"""
    try:
        from app.services.ai_vision_service import ai_vision_service
        from app.services.frame_extraction_service import frame_extraction_service
        import tempfile
        import os
        import cv2
        import numpy as np
        import uuid
        
        results = []
        
        # Test with 3 different synthetic videos
        for test_num in range(3):
            test_id = f"variability_test_{test_num}_{uuid.uuid4().hex[:8]}"
            
            logger.warning(f"🧪 VARIABILITY TEST {test_num + 1}: Starting test for {test_id}")
            
            # Create a unique synthetic video for each test
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_video:
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                out = cv2.VideoWriter(temp_video.name, fourcc, 30.0, (640, 480))
                
                # Use different seed for each test to create varied content
                seed = (test_num + 1) * 123
                np.random.seed(seed)
                
                for i in range(120):  # 4 seconds at 30 fps
                    # Create unique frame content for each test
                    frame = np.random.randint(50 + test_num * 50, 200 + test_num * 20, (480, 640, 3), dtype=np.uint8)
                    
                    # Add different climbing-like patterns for each test
                    if test_num == 0:
                        # Test 1: More rectangular holds
                        cv2.rectangle(frame, (50 + i//5, 100), (150 + i//5, 200), (255, 255, 255), -1)
                        cv2.rectangle(frame, (200 + i//8, 250), (300 + i//8, 350), (200, 200, 200), -1)
                    elif test_num == 1:
                        # Test 2: More circular holds
                        cv2.circle(frame, (100 + i//3, 150), 25, (255, 255, 0), -1)
                        cv2.circle(frame, (300 + i//6, 300), 35, (0, 255, 255), -1)
                        cv2.circle(frame, (450 + i//4, 200), 20, (255, 0, 255), -1)
                    else:
                        # Test 3: Mixed shapes, more complex route
                        cv2.rectangle(frame, (80 + i//4, 80), (120 + i//4, 120), (255, 255, 255), -1)
                        cv2.circle(frame, (250 + i//3, 180), 30, (255, 255, 0), -1)
                        cv2.rectangle(frame, (400 + i//5, 280), (450 + i//5, 330), (0, 255, 0), -1)
                        cv2.circle(frame, (150 + i//6, 350), 25, (0, 0, 255), -1)
                    
                    out.write(frame)
                
                out.release()
                temp_video_path = temp_video.name
            
            try:
                # Extract frames
                frames_data = await frame_extraction_service.extract_frames(
                    video_path=temp_video_path,
                    analysis_id=test_id,
                    frame_interval=1.0
                )
                
                # Perform AI analysis
                if frames_data.get('success') and frames_data.get('frame_paths'):
                    analysis_result = await ai_vision_service.analyze_extracted_frames(
                        frame_paths=frames_data['frame_paths'],
                        analysis_id=test_id,
                        sport_type="bouldering"
                    )
                    
                    route_analysis = analysis_result.get('route_analysis', {})
                    
                    results.append({
                        "test_id": test_id,
                        "test_number": test_num + 1,
                        "frames_extracted": len(frames_data.get('frame_paths', [])),
                        "total_moves": route_analysis.get('total_moves'),
                        "performance_score": analysis_result.get('performance_score'),
                        "route_points": len(route_analysis.get('ideal_route', [])),
                        "key_insights_count": len(route_analysis.get('key_insights', [])),
                        "success": True
                    })
                    
                    logger.warning(f"🧪 Test {test_num + 1} result - moves: {route_analysis.get('total_moves')}, score: {analysis_result.get('performance_score')}")
                else:
                    results.append({
                        "test_id": test_id,
                        "test_number": test_num + 1,
                        "success": False,
                        "error": "Frame extraction failed"
                    })
                
                # Clean up
                try:
                    os.unlink(temp_video_path)
                except:
                    pass
                    
            except Exception as test_err:
                logger.error(f"🧪 Test {test_num + 1} failed: {test_err}")
                results.append({
                    "test_id": test_id,
                    "test_number": test_num + 1,
                    "success": False,
                    "error": str(test_err)
                })
        
        # Analyze variability
        successful_results = [r for r in results if r.get('success')]
        if len(successful_results) > 1:
            moves_values = [r.get('total_moves') for r in successful_results if r.get('total_moves') is not None]
            score_values = [r.get('performance_score') for r in successful_results if r.get('performance_score') is not None]
            
            variability_analysis = {
                "moves_unique_values": len(set(moves_values)) if moves_values else 0,
                "moves_range": f"{min(moves_values)}-{max(moves_values)}" if moves_values else "N/A",
                "scores_unique_values": len(set(score_values)) if score_values else 0,
                "scores_range": f"{min(score_values)}-{max(score_values)}" if score_values else "N/A",
                "all_identical": len(set(moves_values)) == 1 and len(set(score_values)) == 1 if moves_values and score_values else None
            }
        else:
            variability_analysis = {"insufficient_data": "Not enough successful results to analyze variability"}
        
        return {
            "status": "completed",
            "total_tests": 3,
            "successful_tests": len(successful_results),
            "test_results": results,
            "variability_analysis": variability_analysis,
            "message": "Check if AI analysis produces varied results for different synthetic climbing videos"
        }
        
    except Exception as e:
        logger.error(f"🧪 VARIABILITY TEST failed: {str(e)}")
        import traceback
        logger.error(f"🧪 Traceback: {traceback.format_exc()}")
        return {"error": str(e), "traceback": traceback.format_exc()}

@app.get("/debug/force-ai/{analysis_id}")
async def force_ai_analysis(analysis_id: str):
    """Force AI analysis for a specific video"""
    try:
        from app.services.ai_vision_service import ai_vision_service
        
        logger.info(f"🧪 FORCING AI analysis for {analysis_id}")
        
        # Force AI analysis directly
        result = await ai_vision_service.analyze_climbing_video(
            video_path=f"/videos/{analysis_id}",
            analysis_id=analysis_id,
            sport_type="climbing"
        )
        
        return {
            "status": "success",
            "analysis_id": analysis_id,
            "ai_confidence": result.get("ai_confidence", "N/A"),
            "has_overlay": result.get("overlay_data", {}).get("has_overlay", False),
            "overlay_elements": len(result.get("overlay_data", {}).get("elements", [])),
            "performance_score": result.get("performance_score", "N/A"),
            "error": result.get("error", None),
            "route_detected": result.get("route_analysis", {}).get("route_detected", False)
        }
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"❌ FORCE AI TEST FAILED: {str(e)}")
        logger.error(f"Full traceback: {error_details}")
        
        return {
            "status": "error",
            "analysis_id": analysis_id,
            "error": str(e),
            "traceback": error_details
        }

@app.get("/debug/s3")
async def debug_s3():
    """Debug S3 configuration"""
    return {
        "s3_enabled": s3_service.enabled,
        "s3_bucket": s3_service.bucket if s3_service.enabled else None,
        "s3_region": s3_service.region if s3_service.enabled else None,
        "has_access_key": bool(settings.AWS_ACCESS_KEY_ID),
        "has_secret_key": bool(settings.AWS_SECRET_ACCESS_KEY),
        "access_key_length": len(settings.AWS_ACCESS_KEY_ID) if settings.AWS_ACCESS_KEY_ID else 0,
        "secret_key_length": len(settings.AWS_SECRET_ACCESS_KEY) if settings.AWS_SECRET_ACCESS_KEY else 0
    }

@app.post("/debug/clear-cache")
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
                
            logger.warning(f"🖾 CACHE CLEARED: Removed {cleared_count} analysis entries from Redis")
        except Exception as redis_err:
            logger.warning(f"Redis cache clear failed: {redis_err}")
        
        # Clear memory storage 
        memory_cleared = len(video_storage)
        video_storage.clear()
        logger.warning(f"🖾 MEMORY CLEARED: Removed {memory_cleared} video entries from memory")
        
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

@app.get("/debug/videos")
async def debug_videos():
    """Debug endpoint to list all stored videos"""
    import datetime
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
        "upload_tracking": {
            "total_uploads": last_upload_info["count"],
            "last_upload_time": last_upload_info["last_time"],
            "last_upload_id": last_upload_info["last_id"],
            "last_error": last_upload_info.get("last_error", None),
            "last_error_time": last_upload_info.get("last_error_time", None),
            "server_time": datetime.datetime.now().isoformat()
        }
    }

@app.get("/debug/redis/{video_id}")
async def debug_redis_video(video_id: str):
    """Debug endpoint to check Redis data for specific video"""
    try:
        redis_data = {}
        
        # Check video metadata
        try:
            meta_data = await redis_service.get_json(f"video_meta:{video_id}")
            redis_data["video_meta"] = meta_data
        except Exception as e:
            redis_data["video_meta_error"] = str(e)
        
        # Check video data (Base64)
        try:
            video_data = await redis_service.get_json(f"video:{video_id}")
            if video_data:
                redis_data["video_data"] = {k: v if k != "video_data" else f"[{len(v)} chars]" for k, v in video_data.items()}
            else:
                redis_data["video_data"] = None
        except Exception as e:
            redis_data["video_data_error"] = str(e)
        
        # Check analysis data  
        try:
            analysis_data = await redis_service.get_cached_analysis(video_id)
            redis_data["analysis_data"] = "Found" if analysis_data else "Not found"
        except Exception as e:
            redis_data["analysis_data_error"] = str(e)
        
        return {
            "video_id": video_id,
            "redis_data": redis_data,
            "memory_storage": video_id in video_storage
        }
    except Exception as e:
        return {"error": str(e), "video_id": video_id}

@app.options("/upload")
async def upload_options():
    """Handle CORS preflight for upload endpoint"""
    return {"message": "OK"}

@app.get("/videos/{video_id}")
async def serve_video(video_id: str):
    """Serve video file from S3 or in-memory storage"""
    try:
        # Check if video exists in storage metadata
        if video_id not in video_storage:
            # Try Redis cache for video data (Base64 encoded videos)
            try:
                cached_video = await redis_service.get_json(f"video:{video_id}")
                if cached_video and 'video_data' in cached_video:
                    import base64
                    video_content = base64.b64decode(cached_video['video_data'])
                    # Restore to memory for faster access
                    video_storage[video_id] = {
                        'content': video_content,
                        'filename': cached_video.get('filename', 'video.mp4'),
                        'content_type': cached_video.get('content_type', 'video/mp4'),
                        'size': cached_video.get('size', len(video_content)),
                        'storage_type': 'memory'
                    }
                    logger.info(f"Restored video {video_id} from Redis video cache")
                else:
                    # Try Redis cache for video metadata (S3 keys)
                    cached_metadata = await redis_service.get_json(f"video_meta:{video_id}")
                    if cached_metadata:
                        # Restore S3 metadata to memory
                        video_storage[video_id] = cached_metadata
                        logger.info(f"Restored video metadata {video_id} from Redis")
                    else:
                        raise HTTPException(status_code=404, detail="Video not found")
            except HTTPException:
                raise
            except Exception as cache_err:
                logger.warning(f"Redis cache retrieval failed: {cache_err}")
                raise HTTPException(status_code=404, detail="Video not found")
        
        video_info = video_storage[video_id]
        
        # Handle S3 stored videos
        if video_info.get('storage_type') == 's3' and 's3_key' in video_info:
            logger.info(f"Serving S3 video {video_id} with key: {video_info['s3_key']}")
            
            # Generate presigned URL for S3 video
            presigned_url = await s3_service.generate_presigned_url(
                video_info['s3_key'], 
                expires_in=3600  # 1 hour
            )
            
            if presigned_url:
                logger.info(f"Generated presigned URL for {video_id}: {presigned_url[:100]}...")
                
                # Return presigned URL directly for frontend to handle
                # This avoids redirect issues with video players
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    {
                        "video_url": presigned_url,
                        "type": "s3_presigned",
                        "expires_in": 3600,
                        "content_type": video_info.get('content_type', 'video/mp4'),
                        "s3_key": video_info['s3_key'],
                        "debug": {
                            "bucket": "performate-ai-uploads-dev01",
                            "region": "eu-north-1",
                            "video_id": video_id,
                            "presigned_url_length": len(presigned_url)
                        }
                    },
                    headers={
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Methods": "GET, OPTIONS",
                        "Access-Control-Allow-Headers": "*"
                    }
                )
            else:
                logger.error(f"Failed to generate presigned URL for {video_id}")
                logger.error(f"S3 key: {video_info.get('s3_key')}, S3 enabled: {s3_service.enabled}")
                
                # Try direct S3 URL as fallback
                if 's3_key' in video_info:
                    direct_url = f"https://performate-ai-uploads-dev01.s3.eu-north-1.amazonaws.com/{video_info['s3_key']}"
                    logger.info(f"Trying direct S3 URL fallback: {direct_url[:100]}...")
                    return JSONResponse({
                        "video_url": direct_url,
                        "type": "s3_direct",
                        "warning": "Using direct S3 URL - presigned URL generation failed"
                    })
                
                raise HTTPException(status_code=500, detail="Failed to access video from storage")
        
        # Handle memory stored videos (fallback)
        elif video_info.get('storage_type') == 'memory' and 'content' in video_info:
            video_content = video_info['content']
            logger.info(f"Serving video {video_id} from memory")
            
            return Response(
                content=video_content,
                media_type=video_info.get('content_type', 'video/mp4'),
                headers={
                    "Accept-Ranges": "bytes",
                    "Content-Length": str(len(video_content)),
                    "Cache-Control": "public, max-age=3600"
                }
            )
        
        else:
            logger.error(f"Invalid video storage info for {video_id}: {video_info}")
            raise HTTPException(status_code=500, detail="Invalid video storage configuration")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving video {video_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error serving video: {str(e)}")


@app.post("/upload/init")
async def init_upload(request: dict):
    """Initialize upload and return presigned S3 URL for direct client upload"""
    try:
        # Extract request data
        filename = request.get('filename', 'video.mp4')
        content_type = request.get('content_type', 'video/mp4')
        file_size = request.get('file_size', 0)
        
        # Generate analysis ID
        analysis_id = str(uuid.uuid4())
        
        # Validate file type
        allowed_types = ["video/mp4", "video/quicktime", "video/avi", "video/x-msvideo"]
        if content_type not in allowed_types:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {content_type}")
        
        # Validate file size
        if file_size > 120 * 1024 * 1024:  # 120MB
            raise HTTPException(status_code=413, detail="File too large. Maximum size is 120MB.")
        
        # Generate S3 key
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y/%m/%d")
        file_extension = filename.split('.')[-1] if '.' in filename else 'mp4'
        s3_key = f"videos/{timestamp}/{analysis_id}.{file_extension}"
        
        # Generate presigned upload URL
        presigned_data = await s3_service.generate_presigned_upload_url(
            key=s3_key,
            content_type=content_type,
            expires_in=1800  # 30 minutes
        )
        
        if not presigned_data:
            raise HTTPException(status_code=500, detail="Failed to generate upload URL")
        
        # Store pending upload metadata
        video_storage[analysis_id] = {
            's3_key': s3_key,
            'filename': filename,
            'content_type': content_type,
            'size': file_size,
            'status': 'pending_upload',
            'storage_type': 's3',
            'timestamp': uuid.uuid4().hex[:8]
        }
        
        logger.info(f"Upload initialized for {analysis_id}: {filename} ({file_size/(1024*1024):.1f}MB)")
        
        return {
            "analysis_id": analysis_id,
            "upload_url": presigned_data['url'],
            "upload_fields": presigned_data['fields'],
            "s3_key": s3_key,
            "expires_in": 1800,
            "max_file_size": 120 * 1024 * 1024
        }
        
    except Exception as e:
        logger.error(f"Failed to initialize upload: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to initialize upload: {str(e)}")


@app.post("/upload/complete")
async def complete_upload(request: dict):
    """Complete upload after client has uploaded to S3 - start analysis"""
    try:
        analysis_id = request.get('analysis_id')
        if not analysis_id or analysis_id not in video_storage:
            raise HTTPException(status_code=404, detail="Upload session not found")
        
        video_info = video_storage[analysis_id]
        
        # Update status to processing
        video_info['status'] = 'processing'
        logger.info(f"Starting analysis for {analysis_id}: {video_info['filename']}")
        
        # Store metadata in Redis for persistence
        try:
            video_metadata = {
                's3_key': video_info['s3_key'],
                'filename': video_info['filename'],
                'content_type': video_info['content_type'],
                'size': video_info['size'],
                'storage_type': 's3',
                'status': 'processing'
            }
            await redis_service.set_json(f"video_meta:{analysis_id}", video_metadata, expire=7200)
            logger.info(f"Video metadata cached in Redis for {analysis_id}")
        except Exception as redis_error:
            logger.warning(f"Failed to cache video metadata in Redis: {redis_error}")
        
        # Generate enhanced analysis with route overlay
        sport_detected = detect_sport_from_filename(video_info['filename'])
        
        if sport_detected in ['climbing', 'bouldering']:
            # Use AI Vision Service for climbing videos (unified architecture)
            from app.services.ai_vision_service import ai_vision_service
            
            logger.info(f"🤖 Starting unified AI analysis for {sport_detected} video")
            video_analysis = await ai_vision_service.analyze_climbing_video(
                video_path=video_info['s3_key'],  # Use actual S3 key for frame extraction
                analysis_id=analysis_id,
                sport_type=sport_detected
            )
            
            # Use AI Vision Service result directly (no mixing with old mock data)
            analysis_result = video_analysis
            logger.info(f"✅ AI Vision analysis completed with confidence: {video_analysis.get('ai_confidence', 'N/A')}")
        else:
            analysis_result = create_mock_analysis(
                video_info['filename'], 
                sport_detected, 
                video_info['size']
            )
        
        # Cache analysis result
        try:
            await redis_service.cache_analysis_result(analysis_id, analysis_result, expire=3600)
            logger.info(f"Successfully cached analysis for {analysis_id}")
        except Exception as analysis_cache_error:
            logger.warning(f"Analysis caching failed: {analysis_cache_error}")
        
        # Update status to completed
        video_info['status'] = 'completed'
        video_info['analysis'] = analysis_result
        
        logger.info(f"Analysis completed for {analysis_id}: {sport_detected}")
        
        return {
            "analysis_id": analysis_id,
            "status": "completed",
            "sport_detected": sport_detected,
            "video_url": f"/videos/{analysis_id}"
        }
        
    except Exception as e:
        logger.error(f"Failed to complete upload: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to complete upload: {str(e)}")


@app.get("/upload/status/{analysis_id}")
async def get_upload_status(analysis_id: str):
    """Get upload and analysis status"""
    if analysis_id in video_storage:
        video_info = video_storage[analysis_id]
        return {
            "analysis_id": analysis_id,
            "status": video_info.get('status', 'unknown'),
            "filename": video_info.get('filename'),
            "size_mb": video_info.get('size', 0) / (1024 * 1024)
        }
    else:
        raise HTTPException(status_code=404, detail="Upload session not found")


@app.get("/analysis/{analysis_id}/overlay")
async def get_video_overlay(analysis_id: str):
    """Get video overlay data for frontend rendering"""
    try:
        # Try to get cached analysis result
        cached_result = await redis_service.get_cached_analysis(analysis_id)
        
        if cached_result and cached_result.get("overlay_data"):
            overlay_data = cached_result["overlay_data"]
            
            return {
                "analysis_id": analysis_id,
                "has_overlay": overlay_data.get("has_overlay", False),
                "overlay_elements": overlay_data.get("elements", []),
                "video_dimensions": overlay_data.get("video_dimensions", {"width": 640, "height": 480}),
                "total_duration": overlay_data.get("total_duration", 15.0),
                "route_info": {
                    "difficulty": cached_result.get("difficulty_estimated", "Unknown"),
                    "total_moves": cached_result.get("route_analysis", {}).get("total_moves", 0),
                    "overall_score": cached_result.get("route_analysis", {}).get("overall_score", 0)
                }
            }
        else:
            return {
                "analysis_id": analysis_id,
                "has_overlay": False,
                "message": "No overlay data available for this analysis"
            }
            
    except Exception as e:
        logger.error(f"Error retrieving overlay data for {analysis_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve overlay data")


@app.get("/analysis/{analysis_id}")
async def get_analysis_results(analysis_id: str):
    """Get analysis results by analysis ID"""
    try:
        # Try to get from Redis cache first
        try:
            cached_result = await redis_service.get_cached_analysis(analysis_id)
        except Exception as redis_err:
            logger.warning(f"Redis error: {str(redis_err)}. Generating fallback analysis.")
            cached_result = None
            
        if cached_result:
            logger.info(f"Retrieved analysis {analysis_id} from cache")
            analysis_result = cached_result
        else:
            # For demo purposes - generate a new analysis on demand when Redis is unavailable
            logger.info(f"Analysis {analysis_id} not in cache, generating new analysis")
            
            # Use AI Vision Service directly (unified architecture)
            from app.services.ai_vision_service import ai_vision_service
            
            logger.info(f"🤖 Generating new AI analysis for {analysis_id}")
            analysis_result = await ai_vision_service.analyze_climbing_video(
                video_path=f"/videos/{analysis_id}",
                analysis_id=analysis_id,
                sport_type="climbing"
            )
        
        # Generate overlay data if it exists in analysis result
        overlay_data = analysis_result.get('overlay_data', {"has_overlay": False})
        
        # CRITICAL FIX: Include the complete route_analysis object that frontend expects
        route_analysis = analysis_result.get('route_analysis', {})
        
        # Return formatted response with AI Vision data included
        return {
            "id": analysis_id,
            "sport_type": analysis_result.get('sport_type', 'climbing'),
            "analyzer_type": "ai_vision_analysis",
            "overall_performance_score": analysis_result.get('performance_score', 70) / 100,
            "video_url": f"/videos/{analysis_id}",
            "comprehensive_insights": [
                {
                    "category": "technique",
                    "level": "info",
                    "message": insight,
                    "priority": "medium"
                } for insight in route_analysis.get('key_insights', [])
            ],
            "unified_recommendations": analysis_result.get('recommendations', []),
            
            # 🎯 CRITICAL: Include the route_analysis object that frontend expects for total_moves!
            "route_analysis": {
                "route_detected": route_analysis.get('route_detected', True),
                "difficulty_estimated": route_analysis.get('difficulty_estimated', 'Unknown'),
                "total_moves": route_analysis.get('total_moves', 0),  # ⭐ This is what frontend needs!
                "ideal_route": route_analysis.get('ideal_route', []),
                "performance_segments": route_analysis.get('performance_segments', []),
                "overall_score": route_analysis.get('overall_score', 70),
                "key_insights": route_analysis.get('key_insights', []),
                "recommendations": route_analysis.get('recommendations', [])
            },
            
            "sport_specific_analysis": {
                "sport_type": analysis_result.get('sport_type', 'climbing'),
                "difficulty_grade": route_analysis.get('difficulty_estimated', '4a'),
                "key_metrics": {
                    "balance": {
                        "status": "good" if analysis_result.get('detailed_metrics', {}).get('balance_score', 0.5) > 0.7 else "needs_improvement",
                        "score": analysis_result.get('detailed_metrics', {}).get('balance_score', 0.5)
                    },
                    "efficiency": {
                        "status": "good" if analysis_result.get('detailed_metrics', {}).get('efficiency_score', 0.5) > 0.7 else "needs_improvement",
                        "score": analysis_result.get('detailed_metrics', {}).get('efficiency_score', 0.5)
                    },
                    "technique": {
                        "status": "good" if analysis_result.get('detailed_metrics', {}).get('technique_score', 0.5) > 0.7 else "needs_improvement",
                        "score": analysis_result.get('detailed_metrics', {}).get('technique_score', 0.5)
                    }
                },
                "safety_considerations": [
                    "Achte auf sicheren Griff und gute Fußplatzierung",
                    "Verwende Sicherungsausrüstung in angemessener Höhe"
                ],
                "training_recommendations": analysis_result.get('recommendations', [])
            },
            "analysis_summary": {
                "analyzers_used": 1,
                "total_insights": len(route_analysis.get('key_insights', [])),
                "recommendations_count": len(analysis_result.get('recommendations', [])),
                "overall_score": analysis_result.get('performance_score', 70)
            },
            "metadata": {
                "analysis_type": "ai_vision_climbing_analysis",
                "timestamp": analysis_id[:8] + "-" + analysis_id[8:12] + "-" + analysis_id[12:16] + "-" + analysis_id[16:20] + "-" + analysis_id[20:]
            },
            # Add overlay data directly to analysis response
            "overlay_data": overlay_data,
            "has_route_overlay": overlay_data.get("has_overlay", False),
            "enhanced_insights": route_analysis.get('key_insights', []),
            "difficulty_estimated": route_analysis.get('difficulty_estimated', 'Unknown')
        }
            
    except Exception as e:
        logger.error(f"Error retrieving analysis {analysis_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving analysis: {str(e)}")

@app.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    """Upload video with basic AI analysis (simplified for deployment)"""
    
    # Generiere Analysis ID
    analysis_id = str(uuid.uuid4())
    
    # Track upload for debugging
    import datetime
    last_upload_info["count"] += 1
    last_upload_info["last_time"] = datetime.datetime.now().isoformat()
    last_upload_info["last_id"] = analysis_id
    
    logger.info(f"Starting video analysis {analysis_id} for file: {file.filename} (Upload #{last_upload_info['count']})")
    
    try:
        # 1. Validiere Dateityp
        allowed_types = ["video/mp4", "video/quicktime", "video/avi", "video/x-msvideo"]
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")
        
        # 2. Check file size before reading to prevent memory issues
        file_size = file.size or 0
        logger.info(f"Processing video file: {file.filename} ({file_size / (1024*1024):.1f}MB)")
        
        # Allow larger files but with memory management warnings
        if file_size > 120 * 1024 * 1024:  # 120MB hard limit
            raise HTTPException(
                status_code=413, 
                detail="File too large. Maximum size is 120MB. Please compress your video."
            )
        elif file_size > 50 * 1024 * 1024:  # Warning for large files
            logger.warning(f"Large file upload: {file_size/(1024*1024):.1f}MB - may hit memory limits")
            
        # For large files, use streaming upload to avoid memory issues
        if file_size > 50 * 1024 * 1024:  # Stream files > 50MB
            logger.info(f"Large file detected ({file_size/(1024*1024):.1f}MB) - using streaming upload")
            actual_size = file_size
            contents = None  # Don't load into memory
        else:
            # Small files can be loaded into memory
            logger.info(f"Reading small video content...")
            contents = await file.read()
            actual_size = len(contents)
            logger.info(f"Video read successfully: {actual_size / (1024*1024):.1f}MB")
        
        # Upload video to S3 (preferred) or store in memory (fallback)
        s3_key = None
        analysis_result = None  # Initialize to prevent undefined variable errors
        try:
            # Try uploading to S3 first (performance optimized)
            if s3_service.enabled:
                import time
                upload_start = time.time()
                logger.info(f"Starting S3 upload: {actual_size/(1024*1024):.1f}MB")
                
                # Use streaming upload for large files
                if contents is None:  # Large file - stream directly
                    # Reset file pointer for streaming
                    await file.seek(0)
                    s3_key = await s3_service.upload_video_stream(
                        video_stream=file.file,  # Direct file stream
                        filename=file.filename,
                        analysis_id=analysis_id,
                        content_type=file.content_type,
                        file_size=actual_size
                    )
                else:  # Small file - use memory upload
                    s3_key = await s3_service.upload_video(
                        video_content=contents,
                        filename=file.filename,
                        analysis_id=analysis_id,
                        content_type=file.content_type
                    )
                
                upload_time = time.time() - upload_start
                speed_mbps = (actual_size / (1024 * 1024)) / upload_time if upload_time > 0 else 0
                logger.info(f"S3 upload completed in {upload_time:.1f}s ({speed_mbps:.1f} MB/s)")
                
                if s3_key:
                    upload_time = time.time() - upload_start
                    speed_mbps = (actual_size / (1024 * 1024)) / upload_time if upload_time > 0 else 0
                    logger.info(f"S3 upload completed in {upload_time:.1f}s ({speed_mbps:.1f} MB/s)")
                    logger.info(f"Successfully uploaded video to S3: {s3_key}")
                    
                    # Store minimal metadata in memory for quick access
                    video_storage[analysis_id] = {
                        's3_key': s3_key,
                        'filename': file.filename,
                        'content_type': file.content_type,
                        'size': actual_size,
                        'timestamp': uuid.uuid4().hex[:8],
                        'storage_type': 's3'
                    }
                    logger.info(f"Video metadata stored for analysis_id: {analysis_id}")
                    
                    # Also store metadata in Redis for persistence across server restarts
                    try:
                        video_metadata = {
                            's3_key': s3_key,
                            'filename': file.filename,
                            'content_type': file.content_type,
                            'size': actual_size,
                            'storage_type': 's3'
                        }
                        await redis_service.set_json(f"video_meta:{analysis_id}", video_metadata, expire=7200)
                        logger.info(f"Video metadata cached in Redis for {analysis_id}")
                    except Exception as redis_error:
                        logger.warning(f"Failed to cache video metadata in Redis: {redis_error}")
                        
                    # 3. Generate analysis for S3 uploaded video
                    sport_detected = detect_sport_from_filename(file.filename)
                    
                    # 4. Create AI-powered analysis for climbing videos
                    if sport_detected in ['climbing', 'bouldering']:
                        try:
                            # Use AI Vision Service directly
                            from app.services.ai_vision_service import ai_vision_service
                            
                            logger.info(f"🤖 Starting AI analysis for {sport_detected} video")
                            video_analysis = await ai_vision_service.analyze_climbing_video(
                                video_path=s3_key,  # Use actual S3 key, not hardcoded path
                                analysis_id=analysis_id,
                                sport_type=sport_detected
                            )
                            
                            # Use AI analysis result directly
                            analysis_result = video_analysis
                            logger.info(f"✅ AI analysis completed with confidence: {video_analysis.get('ai_confidence', 'N/A')}")
                            
                        except Exception as ai_error:
                            logger.error(f"❌ AI analysis failed: {ai_error}")
                            # DO NOT override AI results - let the AI Vision Service handle fallbacks internally
                            if 'video_analysis' not in locals() or video_analysis is None:
                                # Only if AI Vision Service completely failed to return anything
                                analysis_result = {
                                    "error": "AI analysis service unavailable",
                                    "analysis_id": analysis_id,
                                    "sport_type": sport_detected,
                                    "route_analysis": {"route_detected": False, "overall_score": 0},
                                    "ai_confidence": 0.0
                                }
                            else:
                                analysis_result = video_analysis
                    else:
                        analysis_result = create_mock_analysis(file.filename, sport_detected, actual_size)
                    
                    logger.info(f"Analysis generated for S3 video {analysis_id}: {sport_detected}")
                else:
                    logger.warning("S3 upload failed, falling back to memory storage")
                    raise Exception("S3 upload failed")
            else:
                raise Exception("S3 not configured")
                
        except Exception as s3_error:
            # Fallback to memory storage
            logger.error(f"S3 storage failed ({str(s3_error)}), using memory storage")
            logger.error(f"S3 error details: {type(s3_error).__name__}: {str(s3_error)}")
            
            if actual_size > 150 * 1024 * 1024:  # 150MB limit for memory (temporary until S3 fixed)
                logger.error(f"File too large for memory fallback: {actual_size/(1024*1024):.1f}MB")
                raise HTTPException(
                    status_code=413, 
                    detail="File too large for memory storage and S3 unavailable. Configure S3 for large files."
                )
            
            # If we don't have contents (streaming case), read them now for fallback
            if contents is None:
                logger.info("Reading file contents for memory fallback...")
                await file.seek(0)  # Reset file pointer
                contents = await file.read()
                actual_size = len(contents)
                logger.info(f"File read for fallback: {actual_size/(1024*1024):.1f}MB")
                
            video_storage[analysis_id] = {
                'content': contents,
                'filename': file.filename,
                'content_type': file.content_type,
                'size': actual_size,
                'timestamp': uuid.uuid4().hex[:8],
                'storage_type': 'memory'
            }
            logger.info(f"Video stored in memory (fallback): {analysis_id} ({actual_size / 1024 / 1024:.1f}MB)")
            logger.info(f"Current video_storage keys: {list(video_storage.keys())}")
            
            # 3. Generate analysis for memory stored video
            sport_detected = detect_sport_from_filename(file.filename)
            
            # 4. Create AI-powered analysis for climbing videos (memory fallback)
            if sport_detected in ['climbing', 'bouldering']:
                try:
                    # Use AI Vision Service directly for memory storage
                    from app.services.ai_vision_service import ai_vision_service
                    
                    logger.info(f"🤖 Starting AI analysis for {sport_detected} video (memory storage)")
                    video_analysis = await ai_vision_service.analyze_climbing_video(
                        video_path=f"/videos/{analysis_id}",  # Reference for memory-stored videos
                        analysis_id=analysis_id,
                        sport_type=sport_detected
                    )
                    
                    # Use AI analysis result directly
                    analysis_result = video_analysis
                    logger.info(f"✅ AI analysis completed with confidence: {video_analysis.get('ai_confidence', 'N/A')}")
                    
                except Exception as ai_error:
                    logger.error(f"❌ AI analysis failed: {ai_error}")
                    # DO NOT override AI results - let the AI Vision Service handle fallbacks internally
                    if 'video_analysis' not in locals() or video_analysis is None:
                        analysis_result = {
                            "error": "AI analysis service unavailable",
                            "analysis_id": analysis_id,
                            "sport_type": sport_detected,
                            "route_analysis": {"route_detected": False, "overall_score": 0},
                            "ai_confidence": 0.0
                        }
                    else:
                        analysis_result = video_analysis
            else:
                analysis_result = create_mock_analysis(file.filename, sport_detected, actual_size)
            
            logger.info(f"Analysis generated for memory video {analysis_id}: {sport_detected}")
        
        # 5. Store video and cache analysis (skip Redis for large files to save memory)
        try:
            # Only cache small videos in Redis to prevent memory overflow  
            if file_size < 10 * 1024 * 1024 and contents is not None:  # Only cache videos < 10MB in Redis
                import base64
                video_b64 = base64.b64encode(contents).decode('utf-8')
                video_cache_data = {
                    'video_data': video_b64,
                    'filename': file.filename,
                    'content_type': file.content_type,
                    'size': file_size
                }
                await redis_service.set_json(f"video:{analysis_id}", video_cache_data, expire=7200)
                logger.info(f"Cached small video ({file_size/(1024*1024):.1f}MB) in Redis")
            else:
                logger.info(f"Skipping Redis cache for large video ({file_size/(1024*1024):.1f}MB) - using S3 metadata only")
            
            # Always cache analysis result (small)
            try:
                await redis_service.cache_analysis_result(analysis_id, analysis_result, expire=3600)
                logger.info(f"Successfully cached analysis for {analysis_id}")
            except Exception as analysis_cache_error:
                logger.warning(f"Analysis caching failed: {analysis_cache_error} - analysis available in memory only")
        except Exception as e:
            logger.warning(f"Redis video caching failed: {e} - will serve from memory only")
        
        # 6. Safety check and final result
        if analysis_result is None:
            logger.error(f"Analysis result is None for {analysis_id} - creating fallback")
            analysis_result = create_fallback_analysis()
            
        final_result = {
            "analysis_id": analysis_id,
            "filename": file.filename,
            "content_type": file.content_type,
            "file_size_mb": round(file_size / 1024 / 1024, 2),
            "frames_analyzed": 5,  # Simuliert
            "analysis": analysis_result,
            "status": "completed",
            "timestamp": f"{analysis_id[:8]}-{analysis_id[8:12]}-{analysis_id[12:16]}-{analysis_id[16:20]}-{analysis_id[20:]}",
            "processing_time_ms": 1500,  # Simuliert
            "video_url": f"/videos/{analysis_id}"  # Add video URL for later playback
        }
        
        logger.info(f"Analysis completed successfully for {analysis_id}: {file.filename} ({file_size/(1024*1024):.1f}MB)")
        logger.info(f"Final video_storage keys: {list(video_storage.keys())}")
        return final_result
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"CRITICAL: Analysis failed for {analysis_id}")
        logger.error(f"Error: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Full traceback: {error_details}")
        logger.error(f"Video storage before cleanup: {list(video_storage.keys())}")
        
        # Clean up on error
        if analysis_id in video_storage:
            del video_storage[analysis_id]
            logger.info(f"Cleaned up video storage for failed analysis: {analysis_id}")
        
        # Update tracking
        last_upload_info["last_error"] = str(e)
        last_upload_info["last_error_time"] = datetime.datetime.now().isoformat()
            
        return {
            "analysis_id": analysis_id,
            "filename": file.filename,
            "content_type": file.content_type,
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__,
            "analysis": create_fallback_analysis()
        }


def detect_sport_from_filename(filename: str) -> str:
    """Detect sport from filename"""
    filename_lower = filename.lower()
    
    sport_keywords = {
        'climb': 'climbing', 'boulder': 'bouldering', 'klettern': 'climbing',
        'ski': 'skiing', 'snowboard': 'snowboarding', 'board': 'snowboarding',
        'bike': 'cycling', 'rad': 'cycling', 'cycle': 'cycling',
        'run': 'running', 'lauf': 'running', 'marathon': 'running',
        'swim': 'swimming', 'schwimm': 'swimming',
        'tennis': 'tennis', 'golf': 'golf', 'soccer': 'soccer',
        'basketball': 'basketball', 'volleyball': 'volleyball',
        'yoga': 'yoga', 'fitness': 'fitness', 'gym': 'fitness'
    }
    
    for keyword, sport in sport_keywords.items():
        if keyword in filename_lower:
            return sport
    
    return 'general_sports'


def create_mock_analysis(filename: str, sport: str, file_size: int) -> dict:
    """Create realistic mock analysis"""
    
    # Sport-specific analysis
    sport_analyses = {
        'climbing': {
            'confidence': 85,
            'key_insights': [
                'Gute Grifftechnik erkennbar',
                'Balance könnte verbessert werden',
                'Fußtechnik zeigt Potenzial'
            ],
            'recommendations': [
                'Arbeite an der Fußplatzierung',
                'Übe statische Positionen für bessere Balance',
                'Konzentriere dich auf flüssige Bewegungsübergänge'
            ],
            'areas_for_improvement': ['Balance', 'Fußtechnik', 'Kraft'],
            'strengths': ['Griffstärke', 'Grundtechnik']
        },
        'running': {
            'confidence': 78,
            'key_insights': [
                'Gleichmäßiger Laufrhythmus',
                'Gute Grundausdauer erkennbar',
                'Lauftechnik zeigt solide Basis'
            ],
            'recommendations': [
                'Arbeite an der Schrittfrequenz',
                'Achte auf aufrechte Körperhaltung',
                'Integriere Intervalltraining'
            ],
            'areas_for_improvement': ['Lauftechnik', 'Geschwindigkeit'],
            'strengths': ['Ausdauer', 'Konstanz']
        },
        'general_sports': {
            'confidence': 70,
            'key_insights': [
                'Athletische Bewegungen erkennbar',
                'Gute Grundfitness sichtbar',
                'Koordination zeigt Potenzial'
            ],
            'recommendations': [
                'Arbeite an der Bewegungsqualität',
                'Fokussiere auf Techniktraining',
                'Integriere Krafttraining'
            ],
            'areas_for_improvement': ['Technik', 'Koordination'],
            'strengths': ['Motivation', 'Grundfitness']
        }
    }
    
    base_analysis = sport_analyses.get(sport, sport_analyses['general_sports'])
    
    # Performance score basierend auf File-Größe und Sport
    performance_score = min(95, max(60, base_analysis['confidence'] + (file_size // 1000000)))
    
    return {
        'sport_detected': sport,
        'confidence': base_analysis['confidence'],
        'technical_analysis': f'Video-Analyse für {sport} durchgeführt. Das Video zeigt {filename} mit einer Dateigröße von {file_size//1000000}MB. Grundlegende Bewegungsanalyse completed.',
        'key_insights': base_analysis['key_insights'],
        'recommendations': base_analysis['recommendations'],
        'performance_score': performance_score,
        'areas_for_improvement': base_analysis['areas_for_improvement'],
        'strengths': base_analysis['strengths']
    }


def create_intelligent_climbing_analysis(filename: str, file_size: int, video_path: str) -> dict:
    """Create intelligent climbing analysis based on video metadata and advanced heuristics"""
    import random
    import os
    
    # Analyze video properties if possible (without heavy dependencies)
    video_duration = get_video_duration_estimate(file_size)  # Simple estimation
    
    # Generate realistic scores based on filename hints and file properties
    base_scores = analyze_filename_for_hints(filename)
    
    # Enhanced difficulty detection from multiple factors
    difficulty_grade = detect_route_difficulty(filename, file_size, video_duration)
    
    # File size analysis (larger files often mean longer/more complex climbs)
    file_size_mb = file_size / (1024 * 1024)
    complexity_bonus = min(0.2, file_size_mb / 50)  # Up to 0.2 bonus for larger files
    
    # Calculate realistic scores based on detected difficulty
    grade_modifiers = get_grade_performance_modifiers(difficulty_grade)
    
    balance_score = max(0.3, min(0.95, base_scores['balance'] + complexity_bonus + grade_modifiers['balance'] + random.uniform(-0.1, 0.1)))
    efficiency_score = max(0.3, min(0.95, base_scores['efficiency'] + complexity_bonus + grade_modifiers['efficiency'] + random.uniform(-0.1, 0.1)))
    technique_score = max(0.3, min(0.95, base_scores['technique'] + complexity_bonus + grade_modifiers['technique'] + random.uniform(-0.1, 0.1)))
    
    overall_score = (balance_score + efficiency_score + technique_score) / 3
    
    # Generate insights based on scores and difficulty
    insights = generate_climbing_insights(balance_score, efficiency_score, technique_score, difficulty_grade)
    recommendations = generate_climbing_recommendations(balance_score, efficiency_score, technique_score)
    strengths, improvements = identify_climbing_strengths_improvements(balance_score, efficiency_score, technique_score)
    
    # Create realistic movement timeline segments
    segments = create_movement_timeline(video_duration, difficulty_grade, overall_score)
    
    return {
        'sport_detected': 'climbing',
        'difficulty_grade': difficulty_grade,
        'confidence': int(overall_score * 100),
        'technical_analysis': f'Klettern-Video analysiert. Schwierigkeitsgrad: {difficulty_grade}. '
                            f'Bewegungsqualität: {overall_score:.2f}/1.0. '
                            f'Balance: {balance_score:.2f}, Effizienz: {efficiency_score:.2f}, '
                            f'Technik: {technique_score:.2f}.',
        'key_insights': insights,
        'recommendations': recommendations,
        'performance_score': int(overall_score * 100),
        'areas_for_improvement': improvements,
        'strengths': strengths,
        'detailed_metrics': {
            'balance_score': balance_score,
            'efficiency_score': efficiency_score,
            'technique_score': technique_score,
            'wall_distance_avg': random.uniform(0.2, 0.6),
            'movement_segments': segments,
            'timeline_analysis': segments  # Add timeline for frontend
        },
        'route_analysis': {
            'estimated_difficulty': difficulty_grade,
            'route_type': detect_route_type(filename),
            'key_moves': generate_key_moves_analysis(difficulty_grade, segments),
            'ideal_sequence': generate_ideal_sequence_tips(difficulty_grade)
        }
    }


def get_video_duration_estimate(file_size: int) -> float:
    """Estimate video duration from file size (rough approximation)"""
    # Assume average bitrate of 2-5 Mbps for typical videos
    avg_bitrate_mbps = 3.0  # Conservative estimate
    size_mb = file_size / (1024 * 1024)
    duration_seconds = (size_mb * 8) / avg_bitrate_mbps  # Convert MB to bits, divide by bitrate
    return max(10, min(300, duration_seconds))  # Clamp between 10 seconds and 5 minutes


def analyze_filename_for_hints(filename: str) -> dict:
    """Analyze filename for climbing difficulty hints"""
    filename_lower = filename.lower()
    
    # Look for grade hints in filename
    if any(grade in filename_lower for grade in ['6a', '6b', '6c', '7a']):
        return {'balance': 0.8, 'efficiency': 0.8, 'technique': 0.85}  # Advanced
    elif any(grade in filename_lower for grade in ['5a', '5b', '5c']):
        return {'balance': 0.7, 'efficiency': 0.7, 'technique': 0.75}  # Intermediate
    elif any(grade in filename_lower for grade in ['4a', '4b', '4c']):
        return {'balance': 0.6, 'efficiency': 0.6, 'technique': 0.65}  # Beginner
    
    # Look for skill level hints
    if any(word in filename_lower for word in ['expert', 'advanced', 'hard', 'difficult']):
        return {'balance': 0.75, 'efficiency': 0.8, 'technique': 0.8}
    elif any(word in filename_lower for word in ['beginner', 'easy', 'first', 'learning']):
        return {'balance': 0.5, 'efficiency': 0.5, 'technique': 0.55}
    elif any(word in filename_lower for word in ['boulder', 'problem']):
        return {'balance': 0.65, 'efficiency': 0.7, 'technique': 0.7}  # Bouldering typically more technical
    
    # Default scores
    return {'balance': 0.6, 'efficiency': 0.65, 'technique': 0.6}


def generate_climbing_insights(balance: float, efficiency: float, technique: float, grade: str) -> list:
    """Generate climbing-specific insights"""
    insights = []
    
    if balance >= 0.75:
        insights.append("Ausgezeichnete Balance und Körperstabilität erkennbar")
    elif balance >= 0.6:
        insights.append("Gute Grundbalance vorhanden, Verbesserungspotenzial bei der Stabilität")
    else:
        insights.append("Balance benötigt deutliche Verbesserung für höhere Schwierigkeitsgrade")
    
    if efficiency >= 0.7:
        insights.append("Effiziente Bewegungsführung mit guter Routenplanung")
    elif efficiency >= 0.5:
        insights.append("Solide Bewegungseffizienz, Optimierung der Kletterpfade möglich")
    else:
        insights.append("Viele unnötige Bewegungen erkennbar, Fokus auf direktere Routen empfohlen")
    
    if technique >= 0.7:
        insights.append(f"Solide Klettertechnik für Schwierigkeitsgrad {grade}")
    else:
        insights.append("Techniktraining empfohlen, besonders bei Arm- und Fußpositionierung")
    
    insights.append(f"Geschätzte Kletterkompetenz: {grade} basierend auf Bewegungsanalyse")
    
    return insights


def generate_climbing_recommendations(balance: float, efficiency: float, technique: float) -> list:
    """Generate specific climbing recommendations"""
    recommendations = []
    
    if balance < 0.7:
        recommendations.append("Übe statische Positionen und Körperspannung")
        recommendations.append("Integriere Core-Training und Planks in dein Trainingsprogramm")
    
    if efficiency < 0.7:
        recommendations.append("Plane deine Route im Voraus und visualisiere Bewegungen")
        recommendations.append("Übe bewusstes, langsames Klettern für bessere Kontrolle")
    
    if technique < 0.7:
        recommendations.append("Fokussiere auf entspannte Armhaltung, vermeide Überstreckung")
        recommendations.append("Arbeite gezielt an der Fußtechnik und Gewichtsverteilung")
    
    # Always add general recommendations
    recommendations.append("Übe verschiedene Griffarten für vielseitigere Technik")
    recommendations.append("Integriere Ausdauertraining für längere Routen")
    
    return recommendations


def identify_climbing_strengths_improvements(balance: float, efficiency: float, technique: float) -> tuple:
    """Identify climbing strengths and areas for improvement"""
    strengths = []
    improvements = []
    
    if balance >= 0.7:
        strengths.append("Ausgezeichnete Balance")
    else:
        improvements.append("Balance und Körperstabilität")
    
    if efficiency >= 0.7:
        strengths.append("Effiziente Bewegungsführung")
    else:
        improvements.append("Routenplanung und Bewegungseffizienz")
    
    if technique >= 0.7:
        strengths.append("Solide Klettertechnik")
    else:
        improvements.append("Grundtechnik und Körperpositionierung")
    
    # Ensure we always have something
    if not strengths:
        strengths.append("Motivation und Engagement")
    if not improvements:
        improvements.append("Kontinuierliche Verfeinerung der Technik")
    
    return strengths, improvements


def convert_climbing_metrics_to_dict(metrics) -> dict:
    """Convert ClimbingMetrics to dictionary format for API response"""
    return {
        'sport_detected': 'climbing',
        'difficulty_grade': metrics.difficulty_grade,
        'confidence': int(metrics.movement_quality_score * 100),
        'technical_analysis': f'Klettern-Video analysiert. Schwierigkeitsgrad: {metrics.difficulty_grade}. '
                            f'Bewegungsqualität: {metrics.movement_quality_score:.2f}/1.0. '
                            f'Balance: {metrics.balance_score:.2f}, Effizienz: {metrics.efficiency_score:.2f}, '
                            f'Technik: {metrics.technique_score:.2f}.',
        'key_insights': metrics.key_insights,
        'recommendations': metrics.recommendations,
        'performance_score': int(metrics.movement_quality_score * 100),
        'areas_for_improvement': metrics.areas_for_improvement,
        'strengths': metrics.strengths,
        'detailed_metrics': {
            'balance_score': metrics.balance_score,
            'efficiency_score': metrics.efficiency_score,
            'technique_score': metrics.technique_score,
            'wall_distance_avg': metrics.wall_distance_avg,
            'movement_segments': metrics.movement_segments
        }
    }


def detect_route_difficulty(filename: str, file_size: int, duration: float) -> str:
    """Enhanced route difficulty detection from multiple factors"""
    filename_lower = filename.lower()
    
    # Look for explicit grades in filename
    grade_patterns = {
        r'[78][abc][+]?': '7a+',  # Advanced grades
        r'6[abc][+]?': '6a',      # Intermediate-advanced
        r'5[abc][+]?': '5a',      # Intermediate  
        r'4[abc][+]?': '4c',      # Beginner-intermediate
    }
    
    import re
    for pattern, grade in grade_patterns.items():
        if re.search(pattern, filename_lower):
            return grade
    
    # Analyze based on video characteristics
    file_size_mb = file_size / (1024 * 1024)
    
    # Longer, larger videos often indicate harder routes
    difficulty_score = 0
    
    if duration > 120:  # > 2 minutes
        difficulty_score += 2
    elif duration > 60:  # > 1 minute
        difficulty_score += 1
        
    if file_size_mb > 50:
        difficulty_score += 2
    elif file_size_mb > 20:
        difficulty_score += 1
    
    # Check for difficulty keywords
    if any(word in filename_lower for word in ['hard', 'difficult', 'project', 'send']):
        difficulty_score += 2
    elif any(word in filename_lower for word in ['easy', 'warm', 'beginner']):
        difficulty_score -= 1
        
    # Map score to grade
    if difficulty_score >= 4:
        return '6b'
    elif difficulty_score >= 3:
        return '6a'
    elif difficulty_score >= 2:
        return '5c'
    elif difficulty_score >= 1:
        return '5a'
    else:
        return '4c'


def get_grade_performance_modifiers(grade: str) -> dict:
    """Get performance modifiers based on climbing grade"""
    grade_difficulty = {
        '4a': 0.0, '4b': 0.05, '4c': 0.1,
        '5a': 0.15, '5b': 0.2, '5c': 0.25,
        '6a': 0.3, '6a+': 0.35, '6b': 0.4,
        '7a': 0.5, '7a+': 0.6
    }
    
    base_modifier = grade_difficulty.get(grade, 0.2)
    
    return {
        'balance': base_modifier,
        'efficiency': base_modifier * 0.8,  # Efficiency slightly less affected
        'technique': base_modifier * 1.2   # Technique most affected by grade
    }


def detect_route_type(filename: str) -> str:
    """Detect climbing route type from filename"""
    filename_lower = filename.lower()
    
    if any(word in filename_lower for word in ['boulder', 'problem', 'bloc']):
        return 'bouldering'
    elif any(word in filename_lower for word in ['sport', 'lead', 'redpoint']):
        return 'sport_climbing'
    elif any(word in filename_lower for word in ['trad', 'traditional', 'multi']):
        return 'traditional_climbing'
    else:
        return 'sport_climbing'  # Default


def create_movement_timeline(duration: float, grade: str, overall_score: float) -> list:
    """Create realistic movement timeline with quality assessments"""
    import random
    
    num_segments = max(3, min(8, int(duration / 8)))  # 1 segment per 8 seconds
    segments = []
    
    # Create a realistic climbing progression
    for i in range(num_segments):
        start_time = (duration / num_segments) * i
        end_time = (duration / num_segments) * (i + 1)
        
        # Middle segments often harder
        segment_difficulty = 1.0
        if i == 0:  # Start easier
            segment_difficulty = 0.7
        elif i == num_segments - 1:  # End can be crux or easier
            segment_difficulty = random.choice([0.6, 1.3])  # Either easy finish or crux
        elif i == num_segments // 2:  # Middle often hardest
            segment_difficulty = 1.4
            
        base_quality = overall_score * segment_difficulty
        quality_score = max(0.2, min(0.95, base_quality + random.uniform(-0.2, 0.2)))
        
        if quality_score >= 0.75:
            quality = "excellent"
            color = "green"
        elif quality_score >= 0.6:
            quality = "good"
            color = "green"
        elif quality_score >= 0.4:
            quality = "needs_improvement"
            color = "yellow"
        else:
            quality = "poor"
            color = "red"
            
        segments.append({
            'start_time': round(start_time, 1),
            'end_time': round(end_time, 1),
            'quality': quality,
            'color': color,
            'stability_score': quality_score,
            'duration': round(end_time - start_time, 1),
            'description': generate_segment_description(i, quality, grade)
        })
    
    return segments


def generate_segment_description(segment_index: int, quality: str, grade: str) -> str:
    """Generate description for movement segment"""
    import random
    
    descriptions = {
        'excellent': [
            'Perfekte Balance und Körperspannung',
            'Flüssige, effiziente Bewegungen',
            'Optimale Gewichtsverteilung',
            'Starke technische Ausführung'
        ],
        'good': [
            'Solide Grundtechnik erkennbar',
            'Gute Körperpositionierung',
            'Kontrollierte Bewegungsführung',
            'Angemessene Kraftverteilung'
        ],
        'needs_improvement': [
            'Fußtechnik könnte optimiert werden',
            'Leichte Balance-Probleme',
            'Unnötige Bewegungen erkennbar',
            'Mehr Körperspannung empfohlen'
        ],
        'poor': [
            'Übermäßige Armbelastung erkennbar',
            'Instabile Körperposition',
            'Ineffiziente Bewegungssequenz',
            'Bedeutende technische Schwächen'
        ]
    }
    
    base_desc = random.choice(descriptions.get(quality, descriptions['good']))
    
    # Add segment context
    if segment_index == 0:
        return f'{base_desc} beim Einstieg'
    elif segment_index == 1:
        return f'{base_desc} im unteren Bereich'
    else:
        return f'{base_desc} in der Schlüsselpassage'


def generate_key_moves_analysis(grade: str, segments: list) -> list:
    """Generate key moves analysis based on grade and segments"""
    moves = []
    
    # Find crux segment (lowest quality)
    crux_segment = min(segments, key=lambda x: x['stability_score'])
    
    moves.append({
        'time': f"{crux_segment['start_time']:.1f}s",
        'type': 'crux_move',
        'description': f'Schlüsselstelle bei {crux_segment["start_time"]:.1f}s - schwierigster Teil der Route',
        'difficulty': grade
    })
    
    # Add other key moves
    if len(segments) > 3:
        moves.append({
            'time': f"{segments[1]['start_time']:.1f}s", 
            'type': 'technical_sequence',
            'description': 'Technische Sequenz erfordert präzise Fußarbeit',
            'difficulty': grade
        })
    
    return moves


def generate_ideal_sequence_tips(grade: str) -> list:
    """Generate ideal climbing sequence tips based on grade"""
    tips = [
        'Mehr Gewichtsverlagerung auf die Beine in den ersten 15 Sekunden',
        'Direktere Linie zum Hauptgriff würde Energie sparen',
        'Ruhepositionen zwischen den Schlüsselzügen besser nutzen'
    ]
    
    grade_specific = {
        '4a': 'Fokus auf Grundbalance und sichere Griffe',
        '4b': 'Bessere Fußplatzierung für mehr Stabilität', 
        '4c': 'Koordination zwischen Arm- und Beinbewegungen verbessern',
        '5a': 'Mehr Körperspannung in überhängenden Passagen',
        '5b': 'Dynamische Züge mit besserer Vorbereitung',
        '5c': 'Präzisere Gewichtsverlagerung bei technischen Zügen',
        '6a': 'Optimierung der Greiftechnik für bessere Effizienz',
        '6a+': 'Komplexe Bewegungssequenzen flüssiger verbinden',
        '6b': 'Maximale Körperspannung bei kraftintensiven Passagen',
    }
    
    if grade in grade_specific:
        tips.append(grade_specific[grade])
    
    return tips


def create_fallback_analysis() -> dict:
    """Create fallback analysis for errors"""
    return {
        'sport_detected': 'unknown',
        'confidence': 50,
        'technical_analysis': 'Video wurde hochgeladen und verarbeitet. Detailanalyse war nicht möglich.',
        'key_insights': ['Video erfolgreich empfangen', 'Basis-Verarbeitung durchgeführt'],
        'recommendations': ['Video-Qualität prüfen', 'Erneut versuchen'],
        'performance_score': 60,
        'areas_for_improvement': ['Videoqualität'],
        'strengths': ['Upload erfolgreich']
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
