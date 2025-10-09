"""
Enterprise Video Processing Core
Production-grade video processing with proper abstraction and error handling
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any, Protocol
from enum import Enum
import logging
from datetime import datetime

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
)
logger = logging.getLogger(__name__)


class ProcessingError(Exception):
    """Base exception for video processing errors"""
    def __init__(self, message: str, error_code: str, details: Dict[str, Any] = None):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}
        self.timestamp = datetime.utcnow().isoformat()


class VideoFormat(Enum):
    """Supported video formats"""
    MP4 = "mp4"
    AVI = "avi" 
    MOV = "mov"
    WEBM = "webm"
    MKV = "mkv"


@dataclass
class VideoMetadata:
    """Video metadata container"""
    duration: float
    fps: float
    width: int
    height: int
    total_frames: int
    format: VideoFormat
    codec: str
    file_size: int
    
    def is_valid(self) -> bool:
        """Validate video metadata"""
        return (
            self.duration > 0 and
            self.fps > 0 and
            self.width > 0 and
            self.height > 0 and
            self.total_frames > 0 and
            self.file_size > 1024  # At least 1KB
        )


@dataclass
class FrameData:
    """Individual frame data container"""
    frame_index: int
    timestamp: float
    base64_data: str
    width: int
    height: int
    processing_time_ms: float
    
    def is_valid(self) -> bool:
        """Validate frame data"""
        return (
            self.base64_data and
            len(self.base64_data) > 1000 and  # At least 1KB base64
            self.timestamp >= 0 and
            self.width > 0 and
            self.height > 0
        )


@dataclass
class ProcessingResult:
    """Video processing result container"""
    success: bool
    video_metadata: Optional[VideoMetadata]
    frames: List[FrameData]
    processing_time_ms: float
    processor_used: str
    error: Optional[ProcessingError]
    
    def get_summary(self) -> Dict[str, Any]:
        """Get processing summary"""
        return {
            "success": self.success,
            "processor": self.processor_used,
            "frames_extracted": len(self.frames) if self.frames else 0,
            "video_duration": self.video_metadata.duration if self.video_metadata else 0,
            "processing_time_ms": self.processing_time_ms,
            "error_code": self.error.error_code if self.error else None
        }


class VideoProcessor(ABC):
    """Abstract base class for video processors"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"{__name__}.{name}")
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this processor is available on the system"""
        pass
    
    @abstractmethod
    def get_video_metadata(self, video_path: str) -> VideoMetadata:
        """Extract video metadata"""
        pass
    
    @abstractmethod
    def extract_frames(self, video_path: str, frame_indices: List[int]) -> List[FrameData]:
        """Extract specific frames from video"""
        pass
    
    def validate_video_file(self, video_path: str) -> None:
        """Validate video file before processing"""
        import os
        
        if not os.path.exists(video_path):
            raise ProcessingError(
                f"Video file not found: {video_path}",
                "FILE_NOT_FOUND",
                {"path": video_path}
            )
        
        file_size = os.path.getsize(video_path)
        if file_size < 1024:  # Less than 1KB
            raise ProcessingError(
                f"Video file too small: {file_size} bytes",
                "FILE_TOO_SMALL", 
                {"path": video_path, "size": file_size}
            )
        
        self.logger.info(f"Video file validated: {video_path} ({file_size / (1024*1024):.2f}MB)")


class ProcessorFactory:
    """Factory for creating video processors"""
    
    def __init__(self):
        self._processors: List[VideoProcessor] = []
        self.logger = logging.getLogger(f"{__name__}.ProcessorFactory")
    
    def register_processor(self, processor: VideoProcessor) -> None:
        """Register a video processor"""
        self._processors.append(processor)
        self.logger.info(f"Registered processor: {processor.name}")
    
    def get_available_processors(self) -> List[VideoProcessor]:
        """Get all available processors"""
        available = []
        for processor in self._processors:
            try:
                if processor.is_available():
                    available.append(processor)
                    self.logger.info(f"Processor {processor.name} is available")
                else:
                    self.logger.warning(f"Processor {processor.name} is not available")
            except Exception as e:
                self.logger.error(f"Error checking processor {processor.name}: {e}")
        
        return available
    
    def get_best_processor(self) -> Optional[VideoProcessor]:
        """Get the best available processor"""
        available = self.get_available_processors()
        return available[0] if available else None


class VideoProcessingService:
    """Enterprise video processing service"""
    
    def __init__(self, factory: ProcessorFactory):
        self.factory = factory
        self.logger = logging.getLogger(f"{__name__}.VideoProcessingService")
    
    def process_video(
        self, 
        video_path: str, 
        max_frames: int = 5,
        target_size: Tuple[int, int] = (640, 480)
    ) -> ProcessingResult:
        """
        Process video with enterprise-grade error handling
        
        Args:
            video_path: Path to video file
            max_frames: Maximum number of frames to extract  
            target_size: Target frame size (width, height)
            
        Returns:
            ProcessingResult with metadata and frames
        """
        start_time = datetime.utcnow()
        
        try:
            # Get best available processor
            processor = self.factory.get_best_processor()
            if not processor:
                raise ProcessingError(
                    "No video processors available",
                    "NO_PROCESSORS_AVAILABLE"
                )
            
            self.logger.info(f"Using processor: {processor.name}")
            
            # Validate video file
            processor.validate_video_file(video_path)
            
            # Get video metadata
            metadata = processor.get_video_metadata(video_path)
            if not metadata.is_valid():
                raise ProcessingError(
                    "Invalid video metadata",
                    "INVALID_METADATA",
                    {"metadata": metadata.__dict__}
                )
            
            # Calculate frame indices to extract
            frame_indices = self._calculate_frame_indices(
                metadata.total_frames, 
                metadata.duration, 
                max_frames
            )
            
            # Extract frames
            frames = processor.extract_frames(video_path, frame_indices)
            
            # Validate extracted frames
            valid_frames = [f for f in frames if f.is_valid()]
            if not valid_frames:
                raise ProcessingError(
                    "No valid frames extracted",
                    "NO_VALID_FRAMES",
                    {"total_attempted": len(frames)}
                )
            
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            result = ProcessingResult(
                success=True,
                video_metadata=metadata,
                frames=valid_frames,
                processing_time_ms=processing_time,
                processor_used=processor.name,
                error=None
            )
            
            self.logger.info(f"Video processing successful: {result.get_summary()}")
            return result
            
        except ProcessingError as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            self.logger.error(f"Video processing failed: {e.error_code} - {e}")
            
            return ProcessingResult(
                success=False,
                video_metadata=None,
                frames=[],
                processing_time_ms=processing_time,
                processor_used=processor.name if 'processor' in locals() else "unknown",
                error=e
            )
            
        except Exception as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            self.logger.error(f"Unexpected error in video processing: {e}")
            
            error = ProcessingError(
                f"Unexpected error: {str(e)}",
                "UNEXPECTED_ERROR",
                {"exception_type": type(e).__name__}
            )
            
            return ProcessingResult(
                success=False,
                video_metadata=None,
                frames=[],
                processing_time_ms=processing_time,
                processor_used="unknown",
                error=error
            )
    
    def _calculate_frame_indices(
        self, 
        total_frames: int, 
        duration: float, 
        max_frames: int
    ) -> List[int]:
        """Calculate optimal frame indices for extraction"""
        if total_frames <= max_frames:
            return list(range(total_frames))
        
        # Distribute frames evenly across video duration
        step = total_frames // max_frames
        indices = []
        
        for i in range(max_frames):
            # Add some randomization to avoid repetitive frames
            base_index = i * step
            actual_index = min(base_index + (step // 4), total_frames - 1)
            indices.append(actual_index)
        
        return sorted(set(indices))  # Remove duplicates and sort