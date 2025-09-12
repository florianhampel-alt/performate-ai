"""
Celery worker for background video analysis tasks
"""

import os
import sys
from celery import Celery
from typing import Dict

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.base import settings
from app.analyzers.sport_analyzer import comprehensive_sport_analyzer
from app.services.s3_service import s3_service
from app.services.redis_service import redis_service
from app.utils.logger import get_logger
from app.utils.video_processor import video_processor

logger = get_logger(__name__)

# Create Celery app
celery_app = Celery(
    "performate-ai-worker",
    broker=settings.BROKER_URL,
    backend=settings.RESULT_BACKEND
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=settings.ANALYSIS_TIMEOUT,
    task_soft_time_limit=settings.ANALYSIS_TIMEOUT - 30,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=10,
)


@celery_app.task(bind=True)
def analyze_video_task(self, analysis_id: str, video_url: str, sport_type: str) -> Dict:
    """
    Background task for video analysis
    
    Args:
        analysis_id: Unique identifier for the analysis
        video_url: URL of the video to analyze
        sport_type: Type of sport being analyzed
        
    Returns:
        Dict containing analysis results
    """
    try:
        logger.info(f"Starting video analysis task {analysis_id} for {sport_type}")
        
        # Update task status
        self.update_state(
            state="PROCESSING",
            meta={"status": "Starting analysis", "progress": 0}
        )
        
        # Cache initial status
        await redis_service.set_json(
            f"analysis_status:{analysis_id}",
            {
                "status": "processing",
                "progress": 0,
                "message": "Starting video analysis"
            },
            expire=3600
        )
        
        # Download video from S3 or URL
        self.update_state(
            state="PROCESSING",
            meta={"status": "Downloading video", "progress": 10}
        )
        
        video_data = await _prepare_video_data(video_url)
        
        # Extract frames for analysis
        self.update_state(
            state="PROCESSING",
            meta={"status": "Extracting frames", "progress": 30}
        )
        
        frames = await video_processor.extract_frames(
            video_data["local_path"],
            max_frames=settings.MAX_ANALYSIS_FRAMES
        )
        
        if not frames:
            raise Exception("No frames could be extracted from video")
        
        # Process frames
        self.update_state(
            state="PROCESSING",
            meta={"status": "Processing frames", "progress": 50}
        )
        
        processed_frames = await video_processor.apply_preprocessing(frames, sport_type)
        
        # Perform comprehensive analysis
        self.update_state(
            state="PROCESSING",
            meta={"status": "Running AI analysis", "progress": 70}
        )
        
        analysis_results = await comprehensive_sport_analyzer.analyze(
            {"frames": processed_frames, "url": video_url},
            sport_type
        )
        
        # Save results
        self.update_state(
            state="PROCESSING",
            meta={"status": "Saving results", "progress": 90}
        )
        
        # Cache results in Redis
        await redis_service.cache_analysis_result(analysis_id, analysis_results, expire=86400)
        
        # Clean up temporary files
        await _cleanup_temp_files(video_data.get("local_path"))
        
        self.update_state(
            state="SUCCESS",
            meta={"status": "Analysis completed", "progress": 100}
        )
        
        logger.info(f"Completed video analysis task {analysis_id}")
        return analysis_results
        
    except Exception as e:
        logger.error(f"Error in video analysis task {analysis_id}: {str(e)}")
        
        self.update_state(
            state="FAILURE",
            meta={"status": f"Analysis failed: {str(e)}", "progress": 0}
        )
        
        # Cache error status
        await redis_service.set_json(
            f"analysis_status:{analysis_id}",
            {
                "status": "failed",
                "error": str(e),
                "progress": 0
            },
            expire=3600
        )
        
        raise


async def _prepare_video_data(video_url: str) -> Dict:
    """Prepare video data for analysis"""
    import tempfile
    import requests
    
    # Create temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    
    try:
        if video_url.startswith("http"):
            # Download from URL
            response = requests.get(video_url, stream=True)
            response.raise_for_status()
            
            for chunk in response.iter_content(chunk_size=8192):
                temp_file.write(chunk)
        else:
            # Assume S3 key, generate presigned URL and download
            presigned_url = await s3_service.generate_presigned_url(video_url)
            if presigned_url:
                response = requests.get(presigned_url, stream=True)
                response.raise_for_status()
                
                for chunk in response.iter_content(chunk_size=8192):
                    temp_file.write(chunk)
        
        temp_file.close()
        
        return {
            "local_path": temp_file.name,
            "original_url": video_url
        }
        
    except Exception as e:
        temp_file.close()
        os.unlink(temp_file.name)
        raise Exception(f"Failed to prepare video data: {str(e)}")


async def _cleanup_temp_files(file_path: str):
    """Clean up temporary files"""
    try:
        if file_path and os.path.exists(file_path):
            os.unlink(file_path)
            logger.debug(f"Cleaned up temp file: {file_path}")
    except Exception as e:
        logger.warning(f"Failed to cleanup temp file {file_path}: {str(e)}")


@celery_app.task
def health_check_task() -> Dict:
    """Health check task for worker monitoring"""
    return {
        "status": "healthy",
        "worker": "performate-ai-worker",
        "timestamp": "2024-01-01T00:00:00Z"  # Would use actual timestamp
    }


# Task routing
celery_app.conf.task_routes = {
    "worker.worker.analyze_video_task": {"queue": "analysis"},
    "worker.worker.health_check_task": {"queue": "health"},
}

if __name__ == "__main__":
    celery_app.start()
