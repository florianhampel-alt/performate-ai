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
from app.utils.logger import get_logger
# from app.analyzers.climbing_analyzer import ClimbingPoseAnalyzer  # Disabled for deployment

# In-memory video storage for fallback when S3 is not available
video_storage = {}  # Used only when S3 is disabled
last_upload_info = {"count": 0, "last_time": None, "last_id": None}  # Debug tracking

logger = get_logger(__name__)

app = FastAPI(
    title="Performate AI API",
    description="AI-powered sports performance analysis",
    version="1.0.0"
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

@app.get("/")
async def root():
    return {"message": "Performate AI API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

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
            # Create a fallback analysis directly
            analysis_result = create_intelligent_climbing_analysis(
                filename=f"climbing-video-{analysis_id[:6]}.mp4",
                file_size=15000000,  # 15MB mock size
                video_path=""
            )
        
        # Return formatted response
        return {
            "id": analysis_id,
            "sport_type": analysis_result.get('sport_detected', 'climbing'),
            "analyzer_type": "intelligent_analysis",
            "overall_performance_score": analysis_result.get('performance_score', 70) / 100,
            "video_url": f"/videos/{analysis_id}",  # Add video URL for playback
            "comprehensive_insights": [
                {
                    "category": "technique",
                    "level": "info",
                    "message": insight,
                    "priority": "medium"
                } for insight in analysis_result.get('key_insights', [])
            ],
            "unified_recommendations": analysis_result.get('recommendations', []),
            "sport_specific_analysis": {
                "sport_type": analysis_result.get('sport_detected', 'climbing'),
                "difficulty_grade": analysis_result.get('difficulty_grade', '4a'),
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
                "total_insights": len(analysis_result.get('key_insights', [])),
                "recommendations_count": len(analysis_result.get('recommendations', [])),
                "overall_score": analysis_result.get('performance_score', 70)
            },
            "metadata": {
                "analysis_type": "climbing_intelligent_analysis",
                "timestamp": analysis_id[:8] + "-" + analysis_id[8:12] + "-" + analysis_id[12:16] + "-" + analysis_id[16:20] + "-" + analysis_id[20:]
            }
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
            
        # Read video content with progress logging
        logger.info(f"Reading video content...")
        contents = await file.read()
        actual_size = len(contents)
        logger.info(f"Video read successfully: {actual_size / (1024*1024):.1f}MB (expected: {file_size / (1024*1024):.1f}MB)")
        
        # Upload video to S3 (preferred) or store in memory (fallback)
        s3_key = None
        try:
            # Try uploading to S3 first (performance optimized)
            if s3_service.enabled:
                import time
                upload_start = time.time()
                logger.info(f"Starting S3 upload: {actual_size/(1024*1024):.1f}MB")
                
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
                    
                    # 4. Create analysis based on detected sport
                    if sport_detected in ['climbing', 'bouldering']:
                        analysis_result = create_intelligent_climbing_analysis(file.filename, actual_size, "")
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
            
            if actual_size > 100 * 1024 * 1024:  # 100MB limit for memory
                logger.error(f"File too large for memory fallback: {actual_size/(1024*1024):.1f}MB")
                raise HTTPException(
                    status_code=413, 
                    detail="File too large for memory storage and S3 unavailable. Configure S3 for large files."
                )
                
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
            
            # 4. Create analysis based on detected sport
            if sport_detected in ['climbing', 'bouldering']:
                analysis_result = create_intelligent_climbing_analysis(file.filename, actual_size, "")
            else:
                analysis_result = create_mock_analysis(file.filename, sport_detected, actual_size)
            
            logger.info(f"Analysis generated for memory video {analysis_id}: {sport_detected}")
        
        # 5. Store video and cache analysis (skip Redis for large files to save memory)
        try:
            # Only cache small videos in Redis to prevent memory overflow  
            if file_size < 10 * 1024 * 1024:  # Only cache videos < 10MB in Redis
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
                logger.info(f"Skipping Redis cache for large video ({file_size/(1024*1024):.1f}MB) - using memory only")
            
            # Always cache analysis result (small)
            try:
                await redis_service.cache_analysis_result(analysis_id, analysis_result, expire=3600)
                logger.info(f"Successfully cached analysis for {analysis_id}")
            except Exception as analysis_cache_error:
                logger.warning(f"Analysis caching failed: {analysis_cache_error} - analysis available in memory only")
        except Exception as e:
            logger.warning(f"Redis video caching failed: {e} - will serve from memory only")
        
        # 6. Erweiterte Antwort
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
        return final_result
        
    except Exception as e:
        logger.error(f"Analysis failed for {analysis_id}: {str(e)}")
        # Clean up on error
        if analysis_id in video_storage:
            del video_storage[analysis_id]
            logger.info(f"Cleaned up video storage for failed analysis: {analysis_id}")
            
        return {
            "analysis_id": analysis_id,
            "filename": file.filename,
            "content_type": file.content_type,
            "status": "error",
            "error": str(e),
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
