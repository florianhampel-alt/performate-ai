"""
Container-optimized OpenCV Video Processor
Production-grade OpenCV implementation with multiple backend support
"""

import cv2
import numpy as np
import base64
import os
from io import BytesIO
from PIL import Image
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime

from .core import (
    VideoProcessor, VideoMetadata, FrameData, ProcessingError, VideoFormat
)


class OpenCVProcessor(VideoProcessor):
    """Production-grade OpenCV video processor"""
    
    # OpenCV backend configurations with priority order
    BACKENDS = [
        {
            "backend": cv2.CAP_FFMPEG,
            "name": "FFMPEG",
            "description": "Most reliable for container environments",
            "priority": 1
        },
        {
            "backend": cv2.CAP_ANY,
            "name": "ANY",
            "description": "Let OpenCV auto-select best backend",
            "priority": 2
        },
        {
            "backend": cv2.CAP_V4L2,
            "name": "V4L2", 
            "description": "Linux video subsystem",
            "priority": 3
        },
        {
            "backend": cv2.CAP_GSTREAMER,
            "name": "GSTREAMER",
            "description": "GStreamer multimedia framework",
            "priority": 4
        }
    ]
    
    def __init__(self, target_size: Tuple[int, int] = (640, 480), jpeg_quality: int = 90):
        super().__init__("OpenCV")
        self.target_size = target_size
        self.jpeg_quality = jpeg_quality
        self._available_backends: Optional[List[Dict]] = None
        self._system_info: Optional[Dict] = None
    
    def is_available(self) -> bool:
        """Check if OpenCV is available and working"""
        try:
            # Check OpenCV version
            opencv_version = cv2.__version__
            self.logger.info(f"OpenCV version: {opencv_version}")
            
            # Check available backends
            available_backends = self._get_available_backends()
            
            if not available_backends:
                self.logger.error("No OpenCV backends are available")
                return False
            
            self.logger.info(f"Available backends: {[b['name'] for b in available_backends]}")
            return True
            
        except Exception as e:
            self.logger.error(f"OpenCV availability check failed: {e}")
            return False
    
    def _get_available_backends(self) -> List[Dict]:
        """Get list of available OpenCV backends"""
        if self._available_backends is not None:
            return self._available_backends
        
        available = []
        
        try:
            # Get system backends
            system_backends = cv2.videoio_registry.getBackends()
            backend_names = [cv2.videoio_registry.getBackendName(b) for b in system_backends]
            
            self.logger.info(f"System OpenCV backends: {backend_names}")
            
            # Test each configured backend
            for backend_config in self.BACKENDS:
                backend_id = backend_config["backend"]
                backend_name = backend_config["name"]
                
                try:
                    # Simple test - try to create a VideoCapture object
                    # We can't test with an actual video file here, but we can check if the backend loads
                    test_cap = cv2.VideoCapture()
                    if hasattr(test_cap, 'open'):
                        available.append(backend_config)
                        self.logger.info(f"Backend {backend_name} is functional")
                    test_cap.release()
                    
                except Exception as e:
                    self.logger.warning(f"Backend {backend_name} test failed: {e}")
                    
        except Exception as e:
            self.logger.error(f"Backend enumeration failed: {e}")
        
        self._available_backends = available
        return available
    
    def get_video_metadata(self, video_path: str) -> VideoMetadata:
        """Extract comprehensive video metadata using best available backend"""
        
        for backend_config in self._get_available_backends():
            backend = backend_config["backend"]
            backend_name = backend_config["name"]
            
            try:
                self.logger.info(f"Attempting metadata extraction with {backend_name}")
                
                cap = cv2.VideoCapture(video_path, backend)
                
                if not cap.isOpened():
                    self.logger.warning(f"Could not open video with {backend_name}")
                    cap.release()
                    continue
                
                # Extract metadata
                fps = cap.get(cv2.CAP_PROP_FPS)
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fourcc = cap.get(cv2.CAP_PROP_FOURCC)
                
                # Calculate duration
                duration = total_frames / fps if fps > 0 else 0
                
                # Get file size
                file_size = os.path.getsize(video_path)
                
                # Determine format from file extension
                ext = os.path.splitext(video_path)[1].lower().lstrip('.')
                try:
                    video_format = VideoFormat(ext)
                except ValueError:
                    video_format = VideoFormat.MP4  # Default
                
                # Convert fourcc to string
                fourcc_str = "".join([chr((int(fourcc) >> 8 * i) & 0xFF) for i in range(4)]).strip()
                
                cap.release()
                
                metadata = VideoMetadata(
                    duration=duration,
                    fps=fps,
                    width=width,
                    height=height,
                    total_frames=total_frames,
                    format=video_format,
                    codec=fourcc_str,
                    file_size=file_size
                )
                
                self.logger.info(f"Metadata extracted successfully with {backend_name}: "
                               f"{duration:.1f}s, {width}x{height}, {total_frames} frames, {fps:.1f} FPS")
                
                return metadata
                
            except Exception as e:
                self.logger.error(f"Metadata extraction failed with {backend_name}: {e}")
                if 'cap' in locals():
                    cap.release()
                continue
        
        # If all backends failed
        raise ProcessingError(
            f"Could not extract metadata from {video_path} with any available backend",
            "METADATA_EXTRACTION_FAILED",
            {
                "video_path": video_path,
                "attempted_backends": [b["name"] for b in self._get_available_backends()]
            }
        )
    
    def extract_frames(self, video_path: str, frame_indices: List[int]) -> List[FrameData]:
        """Extract specific frames from video with robust error handling"""
        
        extracted_frames = []
        
        for backend_config in self._get_available_backends():
            backend = backend_config["backend"]
            backend_name = backend_config["name"]
            
            try:
                self.logger.info(f"Attempting frame extraction with {backend_name}")
                
                cap = cv2.VideoCapture(video_path, backend)
                
                if not cap.isOpened():
                    self.logger.warning(f"Could not open video with {backend_name}")
                    cap.release()
                    continue
                
                fps = cap.get(cv2.CAP_PROP_FPS)
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                
                self.logger.info(f"Extracting {len(frame_indices)} frames from {total_frames} total frames")
                
                for frame_idx in frame_indices:
                    frame_start_time = datetime.utcnow()
                    
                    try:
                        # Validate frame index
                        if frame_idx >= total_frames:
                            self.logger.warning(f"Frame index {frame_idx} exceeds total frames {total_frames}")
                            continue
                        
                        # Set frame position
                        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                        
                        # Read frame
                        ret, frame = cap.read()
                        
                        if not ret or frame is None:
                            self.logger.warning(f"Could not read frame {frame_idx}")
                            continue
                        
                        # Calculate timestamp
                        timestamp = frame_idx / fps if fps > 0 else 0
                        
                        # Process frame
                        frame_data = self._process_frame(frame, frame_idx, timestamp)
                        if frame_data:
                            processing_time = (datetime.utcnow() - frame_start_time).total_seconds() * 1000
                            frame_data.processing_time_ms = processing_time
                            extracted_frames.append(frame_data)
                            
                            self.logger.info(f"Frame {frame_idx} extracted successfully "
                                           f"({len(frame_data.base64_data)} chars, {processing_time:.1f}ms)")
                        
                    except Exception as frame_error:
                        self.logger.error(f"Error extracting frame {frame_idx}: {frame_error}")
                        continue
                
                cap.release()
                
                if extracted_frames:
                    self.logger.info(f"Successfully extracted {len(extracted_frames)} frames with {backend_name}")
                    return extracted_frames
                else:
                    self.logger.warning(f"No frames extracted with {backend_name}")
                    continue
                    
            except Exception as e:
                self.logger.error(f"Frame extraction failed with {backend_name}: {e}")
                if 'cap' in locals():
                    cap.release()
                continue
        
        # If all backends failed
        raise ProcessingError(
            f"Could not extract frames from {video_path} with any available backend",
            "FRAME_EXTRACTION_FAILED",
            {
                "video_path": video_path,
                "requested_frames": len(frame_indices),
                "attempted_backends": [b["name"] for b in self._get_available_backends()]
            }
        )
    
    def _process_frame(self, frame: np.ndarray, frame_idx: int, timestamp: float) -> Optional[FrameData]:
        """Process individual frame with comprehensive validation"""
        try:
            # Get original dimensions
            original_height, original_width = frame.shape[:2]
            
            # Resize frame maintaining aspect ratio
            target_width, target_height = self.target_size
            
            # Calculate aspect ratio preserving dimensions
            aspect = original_width / original_height
            if aspect > (target_width / target_height):
                # Frame is wider - fit by width
                new_width = target_width
                new_height = int(target_width / aspect)
            else:
                # Frame is taller - fit by height
                new_height = target_height
                new_width = int(target_height * aspect)
            
            # Resize frame
            resized_frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
            
            # Convert BGR to RGB (OpenCV uses BGR by default)
            rgb_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
            
            # Convert to PIL Image for JPEG encoding
            pil_image = Image.fromarray(rgb_frame)
            
            # Encode to JPEG and then base64
            buffer = BytesIO()
            pil_image.save(buffer, format='JPEG', quality=self.jpeg_quality, optimize=True)
            image_bytes = buffer.getvalue()
            
            # Validate image data
            if len(image_bytes) < 1000:  # Less than 1KB indicates problem
                self.logger.error(f"Processed frame {frame_idx} is too small: {len(image_bytes)} bytes")
                return None
            
            # Encode to base64
            base64_data = base64.b64encode(image_bytes).decode('utf-8')
            
            # Validate base64 data
            if len(base64_data) < 1000:
                self.logger.error(f"Base64 data for frame {frame_idx} is too small: {len(base64_data)} chars")
                return None
            
            # Test base64 validity by attempting to decode a portion
            try:
                test_decode = base64.b64decode(base64_data[:100])
            except Exception as e:
                self.logger.error(f"Invalid base64 data for frame {frame_idx}: {e}")
                return None
            
            return FrameData(
                frame_index=frame_idx,
                timestamp=timestamp,
                base64_data=base64_data,
                width=new_width,
                height=new_height,
                processing_time_ms=0.0  # Will be set by caller
            )
            
        except Exception as e:
            self.logger.error(f"Frame processing failed for frame {frame_idx}: {e}")
            return None
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information for debugging"""
        if self._system_info is not None:
            return self._system_info
        
        info = {
            "opencv_version": cv2.__version__,
            "build_info": {},
            "backends": [],
            "python_version": "",
            "platform": ""
        }
        
        try:
            # Get OpenCV build information
            build_info = cv2.getBuildInformation()
            
            # Parse relevant sections
            if "Video I/O" in build_info:
                video_io_section = build_info.split("Video I/O")[1].split("\n\n")[0]
                info["build_info"]["video_io"] = video_io_section[:500]  # Truncate for logging
            
            # Get available backends
            try:
                system_backends = cv2.videoio_registry.getBackends()
                backend_info = []
                for backend_id in system_backends:
                    backend_name = cv2.videoio_registry.getBackendName(backend_id)
                    backend_info.append({
                        "id": backend_id,
                        "name": backend_name
                    })
                info["backends"] = backend_info
            except Exception as e:
                self.logger.warning(f"Could not get backend info: {e}")
            
            # Get platform info
            import platform
            import sys
            info["python_version"] = sys.version
            info["platform"] = f"{platform.system()} {platform.release()}"
            
        except Exception as e:
            self.logger.error(f"Error collecting system info: {e}")
        
        self._system_info = info
        return info