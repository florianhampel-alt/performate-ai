"""
Video processing utilities for frame extraction and analysis
"""

import cv2
import numpy as np
from typing import List, Tuple, Dict, Optional
import base64
from io import BytesIO
from PIL import Image
from app.utils.logger import get_logger

logger = get_logger(__name__)


class VideoProcessor:
    """Utility class for video processing operations"""

    def __init__(self):
        self.supported_formats = ['.mp4', '.avi', '.mov', '.mkv', '.wmv']

    async def extract_frames(self, video_path: str, max_frames: int = 30, interval: Optional[int] = None) -> List[np.ndarray]:
        """
        Extract frames from video file
        
        Args:
            video_path: Path to video file
            max_frames: Maximum number of frames to extract
            interval: Frame extraction interval (if None, evenly distributed)
            
        Returns:
            List of frame arrays
        """
        try:
            cap = cv2.VideoCapture(video_path)
            
            if not cap.isOpened():
                logger.error(f"Failed to open video: {video_path}")
                return []

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            duration = total_frames / fps if fps > 0 else 0

            logger.info(f"Video info: {total_frames} frames, {fps} FPS, {duration:.2f}s duration")

            # Calculate frame extraction strategy
            if interval is None:
                # Extract evenly distributed frames
                if total_frames <= max_frames:
                    frame_indices = list(range(total_frames))
                else:
                    step = total_frames // max_frames
                    frame_indices = list(range(0, total_frames, step))[:max_frames]
            else:
                # Extract frames at specified interval
                frame_indices = list(range(0, min(total_frames, max_frames * interval), interval))

            frames = []
            for frame_idx in frame_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                
                if ret:
                    frames.append(frame)
                else:
                    logger.warning(f"Failed to read frame {frame_idx}")

            cap.release()
            logger.info(f"Extracted {len(frames)} frames from video")
            return frames

        except Exception as e:
            logger.error(f"Error extracting frames: {str(e)}")
            return []

    async def frames_to_base64(self, frames: List[np.ndarray], quality: int = 85) -> List[str]:
        """
        Convert frames to base64 encoded strings
        
        Args:
            frames: List of frame arrays
            quality: JPEG quality (1-100)
            
        Returns:
            List of base64 encoded strings
        """
        base64_frames = []
        
        for i, frame in enumerate(frames):
            try:
                # Convert BGR to RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Convert to PIL Image
                pil_image = Image.fromarray(frame_rgb)
                
                # Save to bytes
                buffer = BytesIO()
                pil_image.save(buffer, format="JPEG", quality=quality)
                
                # Encode to base64
                base64_string = base64.b64encode(buffer.getvalue()).decode()
                base64_frames.append(f"data:image/jpeg;base64,{base64_string}")
                
            except Exception as e:
                logger.error(f"Error converting frame {i} to base64: {str(e)}")
                continue

        return base64_frames

    async def analyze_video_properties(self, video_path: str) -> Dict:
        """
        Analyze video properties and metadata
        
        Args:
            video_path: Path to video file
            
        Returns:
            Dictionary with video properties
        """
        try:
            cap = cv2.VideoCapture(video_path)
            
            if not cap.isOpened():
                return {"error": "Cannot open video file"}

            properties = {
                "frame_count": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
                "fps": cap.get(cv2.CAP_PROP_FPS),
                "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                "duration": 0,
                "bitrate": cap.get(cv2.CAP_PROP_BITRATE) if hasattr(cv2, 'CAP_PROP_BITRATE') else None
            }
            
            # Calculate duration
            if properties["fps"] > 0:
                properties["duration"] = properties["frame_count"] / properties["fps"]

            # Get codec information (if available)
            fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
            codec = "".join([chr((fourcc >> 8 * i) & 0xFF) for i in range(4)])
            properties["codec"] = codec

            cap.release()
            
            return properties

        except Exception as e:
            logger.error(f"Error analyzing video properties: {str(e)}")
            return {"error": str(e)}

    async def validate_video_file(self, video_path: str) -> Tuple[bool, str]:
        """
        Validate video file format and readability
        
        Args:
            video_path: Path to video file
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check file extension
            if not any(video_path.lower().endswith(fmt) for fmt in self.supported_formats):
                return False, f"Unsupported format. Supported: {', '.join(self.supported_formats)}"

            # Try to open video
            cap = cv2.VideoCapture(video_path)
            
            if not cap.isOpened():
                return False, "Cannot open video file"

            # Try to read first frame
            ret, frame = cap.read()
            cap.release()
            
            if not ret:
                return False, "Cannot read video frames"

            return True, "Video file is valid"

        except Exception as e:
            return False, f"Validation error: {str(e)}"

    async def resize_frames(self, frames: List[np.ndarray], target_size: Tuple[int, int] = (640, 480)) -> List[np.ndarray]:
        """
        Resize frames to target dimensions
        
        Args:
            frames: List of frame arrays
            target_size: Target (width, height)
            
        Returns:
            List of resized frames
        """
        resized_frames = []
        
        for frame in frames:
            try:
                resized_frame = cv2.resize(frame, target_size, interpolation=cv2.INTER_AREA)
                resized_frames.append(resized_frame)
            except Exception as e:
                logger.error(f"Error resizing frame: {str(e)}")
                continue

        return resized_frames

    async def apply_preprocessing(self, frames: List[np.ndarray], sport_type: str) -> List[np.ndarray]:
        """
        Apply sport-specific preprocessing to frames
        
        Args:
            frames: List of frame arrays
            sport_type: Type of sport for specialized preprocessing
            
        Returns:
            List of preprocessed frames
        """
        processed_frames = []
        
        for frame in frames:
            try:
                # Generic preprocessing
                processed_frame = frame.copy()
                
                # Sport-specific preprocessing
                if sport_type in ["climbing", "bouldering"]:
                    # Enhance contrast for better grip detection
                    processed_frame = cv2.convertScaleAbs(processed_frame, alpha=1.2, beta=10)
                elif sport_type == "skiing":
                    # Enhance edges for better movement tracking
                    processed_frame = cv2.bilateralFilter(processed_frame, 9, 75, 75)
                elif sport_type == "motocross":
                    # Noise reduction for dusty environments
                    processed_frame = cv2.medianBlur(processed_frame, 5)

                processed_frames.append(processed_frame)
                
            except Exception as e:
                logger.error(f"Error preprocessing frame: {str(e)}")
                processed_frames.append(frame)  # Use original frame if preprocessing fails

        return processed_frames


video_processor = VideoProcessor()

# Simple wrapper function for backward compatibility
def extract_frames_from_video(video_path: str, max_frames: int = 30) -> List[bytes]:
    """Simple wrapper to extract frames and convert to bytes"""
    import asyncio
    import cv2
    import io
    from PIL import Image
    
    try:
        # Use the processor class
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        frames_array = loop.run_until_complete(video_processor.extract_frames(video_path, max_frames))
        
        # Convert to bytes
        frame_bytes = []
        for frame in frames_array:
            try:
                # Convert BGR to RGB
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Convert to PIL Image
                pil_image = Image.fromarray(rgb_frame)
                
                # Resize for efficiency
                if pil_image.width > 800 or pil_image.height > 800:
                    pil_image.thumbnail((800, 800), Image.Resampling.LANCZOS)
                
                # Convert to JPEG bytes
                img_buffer = io.BytesIO()
                pil_image.save(img_buffer, format='JPEG', quality=85)
                frame_bytes.append(img_buffer.getvalue())
                
            except Exception as e:
                logger.error(f"Error converting frame to bytes: {e}")
                continue
        
        logger.info(f"Converted {len(frame_bytes)} frames to bytes")
        return frame_bytes
        
    except Exception as e:
        logger.error(f"Frame extraction wrapper failed: {str(e)}")
        # Return a simple test frame if extraction fails
        try:
            from PIL import Image
            import io
            test_img = Image.new('RGB', (400, 300), color='lightgray')
            img_buffer = io.BytesIO()
            test_img.save(img_buffer, format='JPEG')
            return [img_buffer.getvalue()]
        except:
            return []
