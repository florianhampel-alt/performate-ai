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
def extract_frames_from_video(video_path: str, analysis_id: str) -> dict:
    """
    Legacy compatibility function
    
    Returns:
        Dict with legacy format for backward compatibility
    """
    try:
        service = get_video_processing_service()
        result = service.process_video(video_path, max_frames=5)
        
        if result.success:
            # Convert to legacy format
            frames = [(frame.base64_data, frame.timestamp) for frame in result.frames]
            
            return {
                'frames': frames,
                'video_duration': result.video_metadata.duration,
                'total_frames': result.video_metadata.total_frames,
                'fps': result.video_metadata.fps,
                'success': True,
                'extraction_method': result.processor_used
            }
        else:
            return {
                'frames': [],
                'video_duration': 0,
                'total_frames': 0,
                'fps': 0,
                'success': False,
                'error': result.error.error_code if result.error else 'UNKNOWN_ERROR'
            }
            
    except Exception as e:
        return {
            'frames': [],
            'video_duration': 0,
            'total_frames': 0,
            'fps': 0,
            'success': False,
            'error': f'COMPATIBILITY_ERROR: {str(e)}'
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