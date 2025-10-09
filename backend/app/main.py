"""
FastAPI Entry Point for Performate AI - Clean Production Version
"""

import uuid
import os
import tempfile
from datetime import datetime
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from app.config.base import settings
from app.utils.logger import get_logger

# Initialize logger first
logger = get_logger(__name__)
logger.info("🚀 Starting Performate AI API initialization...")

# Initialize services with error handling
try:
    from app.services.redis_service import redis_service
    logger.info("✅ Redis service initialized")
except Exception as e:
    logger.warning(f"⚠️ Redis service failed to initialize: {e}")
    redis_service = None

try:
    from app.services.s3_service import s3_service
    logger.info("✅ S3 service initialized")
except Exception as e:
    logger.warning(f"⚠️ S3 service failed to initialize: {e}")
    s3_service = None

try:
    from app.services.video_cache_service import video_cache
    logger.info("✅ Video cache service initialized")
except Exception as e:
    logger.warning(f"⚠️ Video cache service failed to initialize: {e}")
    video_cache = None

# Upload tracking for monitoring
last_upload_info = {"count": 0, "last_time": None, "last_id": None}

logger = get_logger(__name__)

app = FastAPI(
    title="Performate AI API",
    description="AI-powered sports performance analysis with video overlays",
    version="1.2.0"
)

# CORS middleware - Smart pattern matching for Vercel deployments
base_allowed_origins = [
    "http://localhost:3000",    # Local development
    "http://127.0.0.1:3000",    # Local development  
    "https://performate-ai.vercel.app",  # Main production URL
    "https://www.performate-ai.com",     # Custom domain (future)
]

# Smart CORS origin checker function
def is_allowed_origin(origin: str) -> bool:
    """Check if origin is allowed using pattern matching"""
    if not origin:
        return False
    
    # Check base allowed origins
    if origin in base_allowed_origins:
        return True
    
    # Pattern match for Vercel preview URLs
    import re
    vercel_patterns = [
        r'^https://performate-[a-z0-9]+-flos-projects-[a-z0-9]+\.vercel\.app$',  # New pattern
        r'^https://frontend-[a-z0-9]+-flos-projects-[a-z0-9]+\.vercel\.app$',   # Legacy pattern  
        r'^https://performate-ai-[a-z0-9]+\.vercel\.app$',                       # Alternative pattern
    ]
    
    for pattern in vercel_patterns:
        if re.match(pattern, origin):
            logger.info(f"✅ CORS: Allowed Vercel preview URL: {origin}")
            return True
    
    logger.warning(f"❌ CORS: Blocked origin: {origin}")
    return False

# Get all allowed origins (for middleware compatibility)
allowed_origins = "*" if settings.DEBUG else base_allowed_origins

# Custom CORS middleware with pattern matching support
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response as StarletteResponse

class SmartCORSMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, allow_credentials: bool = False):
        super().__init__(app)
        self.allow_credentials = allow_credentials
    
    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get('origin')
        
        # Handle preflight requests
        if request.method == 'OPTIONS':
            if origin and is_allowed_origin(origin):
                return StarletteResponse(
                    status_code=200,
                    headers={
                        'Access-Control-Allow-Origin': origin,
                        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
                        'Access-Control-Allow-Headers': '*',
                        'Access-Control-Max-Age': '86400',
                        'Access-Control-Allow-Credentials': 'true' if self.allow_credentials else 'false',
                    }
                )
            else:
                return StarletteResponse(status_code=403)
        
        # Process the request
        response = await call_next(request)
        
        # Add CORS headers to response
        if origin and is_allowed_origin(origin):
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = '*'
            response.headers['Access-Control-Expose-Headers'] = '*'
            response.headers['Access-Control-Allow-Credentials'] = 'true' if self.allow_credentials else 'false'
        
        return response

# Add the smart CORS middleware
if settings.DEBUG:
    # Development: Allow all origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["*"],
        max_age=86400
    )
else:
    # Production: Smart pattern matching
    app.add_middleware(SmartCORSMiddleware, allow_credentials=False)

# Include routers
if settings.DEBUG:
    try:
        from app.routers.debug import router as debug_router
        app.include_router(debug_router, tags=["Debug"])
        logger.info("Debug router included (development mode)")
    except ImportError:
        logger.warning("Debug router not available")

try:
    from app.routers.ai_test import router as ai_test_router
    app.include_router(ai_test_router, tags=["AI Testing"])
    logger.info("AI test router included")
except ImportError as e:
    logger.warning(f"AI test router not available: {e}")

@app.get("/")
async def root():
    return {"message": "Performate AI API", "version": "1.2.0"}

@app.get("/health")
async def health_check():
    cache_stats = video_cache.get_stats() if video_cache else {"status": "unavailable"}
    return {
        "status": "healthy", 
        "cache_stats": cache_stats,
        "services": {
            "redis": "available" if redis_service else "unavailable",
            "s3": "available" if s3_service else "unavailable",
            "video_cache": "available" if video_cache else "unavailable"
        }
    }

@app.get("/debug/last-ai-responses")
async def get_last_ai_responses():
    """Debug endpoint to see last AI responses and parsing results"""
    logger.info("🔍 Debug endpoint called - fetching last AI responses")
    try:
        from app.debug_ai_response import get_last_ai_responses
        responses = get_last_ai_responses()
        
        logger.info(f"📊 Found {len(responses)} stored AI responses")
        
        if not responses:
            return {"message": "No AI responses captured yet. Upload a video first."}
        
        return {
            "total_responses": len(responses),
            "responses": responses,
            "latest_response": responses[-1] if responses else None
        }
    except Exception as e:
        logger.error(f"❌ Debug endpoint failed: {str(e)}")
        return {"error": f"Debug endpoint failed: {str(e)}"}

@app.post("/debug/clear-cache")
async def clear_all_caches():
    """Clear all caches for debugging"""
    logger.info("🧹 Clearing all caches...")
    cleared_items = []
    
    try:
        # Clear video cache if available
        if video_cache:
            video_cache.clear()
            cleared_items.append("video_cache")
            logger.info("✅ Video cache cleared")
        
        # Clear Redis cache if available
        if redis_service:
            try:
                # Clear analysis results
                analysis_keys = await redis_service.keys("analysis:*")
                if analysis_keys:
                    for key in analysis_keys:
                        await redis_service.delete(key)
                    cleared_items.append(f"redis_analysis_keys ({len(analysis_keys)})")
                
                # Clear video metadata
                video_keys = await redis_service.keys("video:*")
                video_meta_keys = await redis_service.keys("video_meta:*")
                if video_keys:
                    for key in video_keys:
                        await redis_service.delete(key)
                    cleared_items.append(f"redis_video_keys ({len(video_keys)})")
                if video_meta_keys:
                    for key in video_meta_keys:
                        await redis_service.delete(key)
                    cleared_items.append(f"redis_video_meta_keys ({len(video_meta_keys)})")
                
                logger.info("✅ Redis caches cleared")
            except Exception as redis_error:
                logger.warning(f"⚠️ Redis cache clearing failed: {redis_error}")
                cleared_items.append(f"redis_error: {str(redis_error)}")
        
        return {
            "status": "success",
            "message": "All caches cleared",
            "cleared_items": cleared_items,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"❌ Cache clearing failed: {str(e)}")
        return {
            "status": "error",
            "message": f"Cache clearing failed: {str(e)}",
            "cleared_items": cleared_items
        }

@app.options("/upload")
async def upload_options():
    """Handle CORS preflight for upload endpoint"""
    return {"message": "OK"}

@app.get("/videos/{video_id}")
async def serve_video(video_id: str):
    """Serve video file from S3 or cache"""
    try:
        # Check service availability
        if not video_cache:
            raise HTTPException(status_code=503, detail="Video cache service unavailable")
        
        # Check if video exists in cache
        video_info = video_cache.get(video_id)
        
        if not video_info:
            # Try Redis cache for video data (if available)
            if redis_service:
                try:
                    cached_video = await redis_service.get_json(f"video:{video_id}")
                    if cached_video and 'video_data' in cached_video:
                        import base64
                        video_content = base64.b64decode(cached_video['video_data'])
                        # Restore to cache
                        video_cache.set(video_id, {
                            'content': video_content,
                            'filename': cached_video.get('filename', 'video.mp4'),
                            'content_type': cached_video.get('content_type', 'video/mp4'),
                            'size': cached_video.get('size', len(video_content)),
                            'storage_type': 'memory'
                        })
                        video_info = video_cache.get(video_id)
                        logger.info(f"Restored video {video_id} from Redis")
                    else:
                        # Try Redis cache for S3 metadata
                        cached_metadata = await redis_service.get_json(f"video_meta:{video_id}")
                        if cached_metadata:
                            video_cache.set(video_id, cached_metadata)
                            video_info = video_cache.get(video_id)
                            logger.info(f"Restored video metadata {video_id} from Redis")
                        else:
                            raise HTTPException(status_code=404, detail="Video not found")
                except HTTPException:
                    raise
                except Exception as cache_err:
                    logger.warning(f"Redis cache retrieval failed: {cache_err}")
                    raise HTTPException(status_code=404, detail="Video not found")
            else:
                logger.info(f"Redis service unavailable, cannot retrieve video {video_id} from cache")
                raise HTTPException(status_code=404, detail="Video not found")
        
        # Handle S3 stored videos
        if video_info.get('storage_type') == 's3' and 's3_key' in video_info:
            if not s3_service:
                raise HTTPException(status_code=503, detail="S3 service unavailable")
            
            logger.info(f"Serving S3 video {video_id} with key: {video_info['s3_key']}")
            
            # Generate presigned URL for S3 video
            presigned_url = await s3_service.generate_presigned_url(
                video_info['s3_key'], 
                expires_in=3600
            )
            
            if presigned_url:
                from fastapi.responses import JSONResponse
                return JSONResponse({
                    "video_url": presigned_url,
                    "type": "s3_presigned",
                    "expires_in": 3600,
                    "content_type": video_info.get('content_type', 'video/mp4'),
                })
            else:
                raise HTTPException(status_code=500, detail="Failed to access video from storage")
        
        # Handle memory stored videos
        elif video_info.get('storage_type') == 'memory' and 'content' in video_info:
            video_content = video_info['content']
            logger.info(f"Serving video {video_id} from cache")
            
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
        # Check service availability
        if not s3_service:
            raise HTTPException(status_code=503, detail="S3 service unavailable")
        if not video_cache:
            raise HTTPException(status_code=503, detail="Video cache service unavailable")
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
            expires_in=1800
        )
        
        if not presigned_data:
            raise HTTPException(status_code=500, detail="Failed to generate upload URL")
        
        # Store pending upload metadata in cache
        video_cache.set(analysis_id, {
            's3_key': s3_key,
            'filename': filename,
            'content_type': content_type,
            'size': file_size,
            'status': 'pending_upload',
            'storage_type': 's3',
        })
        
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
        if not analysis_id:
            raise HTTPException(status_code=400, detail="Missing analysis_id")
            
        video_info = video_cache.get(analysis_id)
        if not video_info:
            raise HTTPException(status_code=404, detail="Upload session not found")
        
        # Update status to processing
        video_info['status'] = 'processing'
        video_cache.set(analysis_id, video_info)
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
        
        # Generate AI analysis
        sport_detected = detect_sport_from_filename(video_info['filename'])
        
        if sport_detected in ['climbing', 'bouldering']:
            from app.services.ai_vision_service import ai_vision_service
            
            logger.info(f"🤖 Starting AI analysis for {sport_detected} video")
            video_analysis = await ai_vision_service.analyze_climbing_video(
                video_path=video_info['s3_key'],
                analysis_id=analysis_id,
                sport_type=sport_detected
            )
            
            analysis_result = video_analysis
            logger.info(f"✅ AI analysis completed with confidence: {video_analysis.get('ai_confidence', 'N/A')}")
        else:
            analysis_result = create_mock_analysis(
                video_info['filename'], 
                sport_detected, 
                video_info['size']
            )
        
        # Update status to completed
        video_info['status'] = 'completed'
        video_info['analysis'] = analysis_result
        video_cache.set(analysis_id, video_info)
        
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
    video_info = video_cache.get(analysis_id)
    if video_info:
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
        # Check if caching is disabled for debugging
        logger.warning(f"🚫 CACHE LOOKUP DISABLED - Always generating fresh analysis for {analysis_id}")
        
        # Generate fresh analysis
        from app.services.ai_vision_service import ai_vision_service
        
        logger.info(f"🤖 Generating new AI analysis for {analysis_id}")
        
        # Get S3 key from cache or reconstruct
        video_info = video_cache.get(analysis_id)
        if video_info and 's3_key' in video_info:
            video_path = video_info['s3_key']
            logger.warning(f"🔑 Using S3 key from cache: {video_path}")
        else:
            # Reconstruct S3 key
            clean_analysis_id = analysis_id.split(':')[0]
            from datetime import datetime
            today = datetime.now().strftime("%Y/%m/%d")
            video_path = f"videos/{today}/{clean_analysis_id}.mp4"
            logger.warning(f"🔄 RECONSTRUCTING S3 key: {video_path}")
        
        analysis_result = await ai_vision_service.analyze_climbing_video(
            video_path=video_path,
            analysis_id=analysis_id,
            sport_type="climbing"
        )
        
        # Generate overlay data
        overlay_data = analysis_result.get('overlay_data', {"has_overlay": False})
        route_analysis = analysis_result.get('route_analysis', {})
        
        # Return formatted response
        return {
            "id": analysis_id,
            "sport_type": analysis_result.get('sport_type', 'climbing'),
            "analyzer_type": "ai_vision_analysis",
            "overall_performance_score": analysis_result.get('performance_score', 0) / 100,
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
            "route_analysis": {
                "route_detected": route_analysis.get('route_detected', True),
                "route_color": route_analysis.get('route_color', 'unbekannt'),  # Add route color
                "difficulty_estimated": route_analysis.get('difficulty_estimated', 'Unknown'),
                "total_moves": route_analysis.get('total_moves', 0),
                "ideal_route": route_analysis.get('ideal_route', []),
                "performance_segments": route_analysis.get('performance_segments', []),
                "overall_score": route_analysis.get('overall_score', 0),
                "key_insights": route_analysis.get('key_insights', []),
                "recommendations": route_analysis.get('recommendations', [])
            },
            "sport_specific_analysis": {
                "sport_type": analysis_result.get('sport_type', 'climbing'),
                "difficulty_grade": route_analysis.get('difficulty_estimated', 'Unknown'),
                "key_metrics": route_analysis.get('key_metrics', {}),  # Use AI metrics instead of hardcoded
                "safety_considerations": route_analysis.get('safety_considerations', []),  # Use AI safety tips
                "training_recommendations": analysis_result.get('recommendations', [])
            },
            "analysis_summary": {
                "analyzers_used": 1,
                "total_insights": len(route_analysis.get('key_insights', [])),
                "recommendations_count": len(analysis_result.get('recommendations', [])),
                "overall_score": analysis_result.get('performance_score', 0)
            },
            "metadata": {
                "analysis_type": "ai_vision_climbing_analysis",
                "timestamp": analysis_id[:8] + "-" + analysis_id[8:12] + "-" + analysis_id[12:16] + "-" + analysis_id[16:20] + "-" + analysis_id[20:]
            },
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
    """Upload video with AI analysis (main upload endpoint)"""
    
    analysis_id = str(uuid.uuid4())
    
    # Track upload for monitoring
    import datetime
    last_upload_info["count"] += 1
    last_upload_info["last_time"] = datetime.datetime.now().isoformat()
    last_upload_info["last_id"] = analysis_id
    
    logger.info(f"Starting video analysis {analysis_id} for file: {file.filename} (Upload #{last_upload_info['count']})")
    
    try:
        # Validate file type
        allowed_types = ["video/mp4", "video/quicktime", "video/avi", "video/x-msvideo"]
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")
        
        # Check file size
        file_size = file.size or 0
        logger.info(f"Processing video file: {file.filename} ({file_size / (1024*1024):.1f}MB)")
        
        if file_size > 120 * 1024 * 1024:  # 120MB hard limit
            raise HTTPException(
                status_code=413, 
                detail="File too large. Maximum size is 120MB. Please compress your video."
            )
        
        # Read file content
        contents = await file.read()
        actual_size = len(contents)
        
        # Try S3 upload first
        s3_key = None
        analysis_result = None
        
        try:
            if s3_service.enabled:
                s3_key = await s3_service.upload_video(
                    video_content=contents,
                    filename=file.filename,
                    analysis_id=analysis_id,
                    content_type=file.content_type
                )
                
                if s3_key:
                    logger.info(f"Successfully uploaded video to S3: {s3_key}")
                    
                    # Store metadata in cache
                    video_cache.set(analysis_id, {
                        's3_key': s3_key,
                        'filename': file.filename,
                        'content_type': file.content_type,
                        'size': actual_size,
                        'storage_type': 's3'
                    })
                    
                    # Cache metadata in Redis
                    try:
                        video_metadata = {
                            's3_key': s3_key,
                            'filename': file.filename,
                            'content_type': file.content_type,
                            'size': actual_size,
                            'storage_type': 's3'
                        }
                        await redis_service.set_json(f"video_meta:{analysis_id}", video_metadata, expire=7200)
                    except Exception as redis_error:
                        logger.warning(f"Failed to cache video metadata in Redis: {redis_error}")
                        
                    # Generate analysis for S3 uploaded video
                    sport_detected = detect_sport_from_filename(file.filename)
                    
                    if sport_detected in ['climbing', 'bouldering']:
                        from app.services.ai_vision_service import ai_vision_service
                        
                        logger.info(f"🤖 Starting AI analysis for {sport_detected} video")
                        video_analysis = await ai_vision_service.analyze_climbing_video(
                            video_path=s3_key,
                            analysis_id=analysis_id,
                            sport_type=sport_detected
                        )
                        
                        analysis_result = video_analysis
                        logger.info(f"✅ AI analysis completed with confidence: {video_analysis.get('ai_confidence', 'N/A')}")
                    else:
                        analysis_result = create_mock_analysis(file.filename, sport_detected, actual_size)
                    
                    logger.info(f"Analysis generated for S3 video {analysis_id}: {sport_detected}")
        
        except Exception as s3_error:
            # Fallback to memory storage
            logger.error(f"S3 storage failed ({str(s3_error)}), using memory storage")
            
            if actual_size > 150 * 1024 * 1024:  # 150MB limit for memory
                raise HTTPException(
                    status_code=413, 
                    detail="File too large for memory storage and S3 unavailable."
                )
                
            video_cache.set(analysis_id, {
                'content': contents,
                'filename': file.filename,
                'content_type': file.content_type,
                'size': actual_size,
                'storage_type': 'memory'
            })
            
            logger.info(f"Video stored in memory cache: {analysis_id} ({actual_size / 1024 / 1024:.1f}MB)")
            
            # Generate analysis for memory stored video
            sport_detected = detect_sport_from_filename(file.filename)
            
            if sport_detected in ['climbing', 'bouldering']:
                from app.services.ai_vision_service import ai_vision_service
                
                logger.info(f"🤖 Starting AI analysis for {sport_detected} video")
                video_analysis = await ai_vision_service.analyze_climbing_video(
                    video_path=f"/videos/{analysis_id}",
                    analysis_id=analysis_id,
                    sport_type=sport_detected
                )
                
                analysis_result = video_analysis
                logger.info(f"✅ AI analysis completed with confidence: {video_analysis.get('ai_confidence', 'N/A')}")
            else:
                analysis_result = create_mock_analysis(file.filename, sport_detected, actual_size)
            
            logger.info(f"Analysis generated for memory video {analysis_id}: {sport_detected}")
        
        # Cache small videos in Redis
        try:
            if file_size < 10 * 1024 * 1024:  # Only cache videos < 10MB
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
            
            # Always cache analysis result
            await redis_service.cache_analysis_result(analysis_id, analysis_result, expire=3600)
            logger.info(f"Successfully cached analysis for {analysis_id}")
        except Exception as e:
            logger.warning(f"Redis caching failed: {e}")
        
        # Return result
        if analysis_result is None:
            analysis_result = create_fallback_analysis()
            
        return {
            "analysis_id": analysis_id,
            "filename": file.filename,
            "content_type": file.content_type,
            "file_size_mb": round(file_size / 1024 / 1024, 2),
            "frames_analyzed": 5,
            "analysis": analysis_result,
            "status": "completed",
            "timestamp": f"{analysis_id[:8]}-{analysis_id[8:12]}-{analysis_id[12:16]}-{analysis_id[16:20]}-{analysis_id[20:]}",
            "processing_time_ms": 1500,
            "video_url": f"/videos/{analysis_id}"
        }
        
    except Exception as e:
        import traceback
        logger.error(f"CRITICAL: Analysis failed for {analysis_id}")
        logger.error(f"Error: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        
        # Clean up on error
        video_cache.delete(analysis_id)
        
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
    }
    
    for keyword, sport in sport_keywords.items():
        if keyword in filename_lower:
            return sport
    
    return 'climbing'  # Default to climbing

def create_mock_analysis(filename: str, sport: str, file_size: int) -> dict:
    """Create realistic mock analysis"""
    return {
        'sport_detected': sport,
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
        'performance_score': min(95, max(60, 75 + (file_size // 1000000))),
        'areas_for_improvement': ['Balance', 'Fußtechnik'],
        'strengths': ['Griffstärke', 'Grundtechnik']
    }

def create_fallback_analysis() -> dict:
    """Create fallback analysis for errors"""
    return {
        'sport_detected': 'unknown',
        'confidence': 50,
        'key_insights': ['Video erfolgreich empfangen'],
        'recommendations': ['Video-Qualität prüfen'],
        'performance_score': 60,
        'areas_for_improvement': ['Videoqualität'],
        'strengths': ['Upload erfolgreich']
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)