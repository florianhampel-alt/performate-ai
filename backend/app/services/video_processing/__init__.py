"""
Enterprise Video Processing Package
Production-grade video processing with comprehensive error handling
"""

from .core import (
    VideoProcessor,
    VideoMetadata, 
    FrameData,
    ProcessingResult,
    ProcessingError,
    VideoFormat,
    ProcessorFactory,
    VideoProcessingService
)

from .opencv_processor import OpenCVProcessor

# Global service instance
_processor_factory = None
_processing_service = None


def get_video_processing_service() -> VideoProcessingService:
    """Get singleton video processing service instance"""
    global _processor_factory, _processing_service
    
    if _processing_service is None:
        # Initialize factory
        _processor_factory = ProcessorFactory()
        
        # Register processors
        opencv_processor = OpenCVProcessor(
            target_size=(640, 480),
            jpeg_quality=90
        )
        _processor_factory.register_processor(opencv_processor)
        
        # Create service
        _processing_service = VideoProcessingService(_processor_factory)
    
    return _processing_service


# Legacy compatibility functions for frame_extraction_service
async def extract_frames_from_video(video_path: str, analysis_id: str) -> dict:
    """
    Legacy compatibility function
    
    Returns:
        Dict with legacy format for backward compatibility
    """
    try:
        # Import logging for detailed diagnostics
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"🏗️ ENTERPRISE PROCESSING START for {analysis_id}")
        logger.info(f"   Video path: {video_path}")
        
        service = get_video_processing_service()
        logger.info(f"   Service initialized successfully")
        
        result = service.process_video(video_path, max_frames=5)
        logger.info(f"   Processing completed: {result.get_summary()}")
        
        if result.success:
            # Convert to legacy format
            frames = [(frame.base64_data, frame.timestamp) for frame in result.frames]
            
            logger.info(f"✅ ENTERPRISE SUCCESS: {len(frames)} frames extracted, duration={result.video_metadata.duration:.1f}s")
            
            return {
                'frames': frames,
                'video_duration': result.video_metadata.duration,
                'total_frames': result.video_metadata.total_frames,
                'fps': result.video_metadata.fps,
                'success': True,
                'extraction_method': f'enterprise_{result.processor_used}'
            }
        else:
            error_code = result.error.error_code if result.error else 'UNKNOWN_ERROR'
            error_details = result.error.details if result.error else {}
            
            logger.error(f"❌ ENTERPRISE FAILURE: {error_code}")
            logger.error(f"   Error details: {error_details}")
            logger.error(f"   Processing time: {result.processing_time_ms:.1f}ms")
            
            return {
                'frames': [],
                'video_duration': 0,
                'total_frames': 0,
                'fps': 0,
                'success': False,
                'error': f'ENTERPRISE_{error_code}',
                'error_details': error_details
            }
            
    except Exception as e:
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        
        logger.error(f"❌ ENTERPRISE SYSTEM EXCEPTION: {str(e)}")
        logger.error(f"   Traceback: {traceback.format_exc()}")
        
        return {
            'frames': [],
            'video_duration': 0,
            'total_frames': 0,
            'fps': 0,
            'success': False,
            'error': f'ENTERPRISE_EXCEPTION: {str(e)}',
            'traceback': traceback.format_exc()
        }


__all__ = [
    'VideoProcessor',
    'VideoMetadata',
    'FrameData', 
    'ProcessingResult',
    'ProcessingError',
    'VideoFormat',
    'ProcessorFactory',
    'VideoProcessingService',
    'OpenCVProcessor',
    'get_video_processing_service',
    'extract_frames_from_video'
]