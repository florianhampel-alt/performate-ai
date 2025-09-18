"""
Video Frame Extraction Service for AI Analysis
Extracts key frames from climbing videos for GPT-4 Vision analysis
"""

import cv2
import os
import tempfile
import base64
from io import BytesIO
from PIL import Image
from typing import List, Tuple, Optional
import numpy as np

from app.utils.logger import get_logger
from app.services.s3_service import s3_service

logger = get_logger(__name__)


class FrameExtractionService:
    def __init__(self):
        self.max_frames = 1  # ULTRA EFFICIENT: Single frame analysis only
        self.frame_size = (480, 320)  # ULTRA REDUCED: Smallest workable resolution
        
    async def extract_frames_from_video(
        self, 
        video_path: str, 
        analysis_id: str
    ) -> List[Tuple[str, float]]:
        """
        Extract key frames from video for AI analysis
        
        Args:
            video_path: Path to video (S3 key or local path)
            analysis_id: Analysis ID for temporary files
            
        Returns:
            List of (base64_image, timestamp) tuples
        """
        try:
            logger.info(f"Starting frame extraction for {analysis_id}")
            
            # Download video if it's from S3
            temp_video_path = await self._get_video_file(video_path, analysis_id)
            
            if not temp_video_path:
                logger.error(f"Could not get video file for {analysis_id}")
                return []
            
            # Extract frames using OpenCV
            frames = self._extract_frames_opencv(temp_video_path)
            
            # Clean up temporary file
            if temp_video_path.startswith('/tmp'):
                try:
                    os.remove(temp_video_path)
                except:
                    pass
                    
            logger.info(f"Extracted {len(frames)} frames for {analysis_id}")
            return frames
            
        except Exception as e:
            logger.error(f"Frame extraction failed for {analysis_id}: {str(e)}")
            return []
    
    async def _get_video_file(self, video_path: str, analysis_id: str) -> Optional[str]:
        """Get video file path (download from S3 if needed)"""
        try:
            # Check if this is an S3 key (starts with 'videos/' or '/videos/')
            if video_path.startswith('videos/') or video_path.startswith('/videos/'):
                # S3 video - download to temporary file
                s3_key = video_path.lstrip('/')  # Remove leading slash if present
                logger.info(f"Downloading video from S3 key: {s3_key}")
                
                # Create temp file
                temp_fd, temp_path = tempfile.mkstemp(suffix='.mp4')
                os.close(temp_fd)
                
                # Download from S3
                logger.info(f"📯 Downloading video from S3: {s3_key} -> {temp_path}")
                success = await s3_service.download_file(s3_key, temp_path)
                if success:
                    file_size = os.path.getsize(temp_path) if os.path.exists(temp_path) else 0
                    logger.info(f"✅ S3 download successful: {file_size/(1024*1024):.1f}MB")
                    return temp_path
                else:
                    logger.error(f"❌ Failed to download video from S3: {s3_key}")
                    # Check if S3 service is enabled
                    if not s3_service.enabled:
                        logger.error(f"⚠️ S3 service is disabled - check AWS credentials")
                    return None
            else:
                # Local video path
                if os.path.exists(video_path):
                    return video_path
                else:
                    logger.error(f"Video file not found: {video_path}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting video file: {str(e)}")
            return None
    
    def _extract_frames_opencv(self, video_path: str) -> List[Tuple[str, float]]:
        """Extract frames using OpenCV"""
        frames = []
        
        try:
            # Open video
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logger.error(f"Could not open video: {video_path}")
                return frames
            
            # Get video properties
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            duration = total_frames / fps if fps > 0 else 0
            
            logger.info(f"Video stats: {total_frames} frames, {fps:.2f} FPS, {duration:.1f}s")
            
            # Calculate frame indices to extract
            frame_indices = self._calculate_frame_indices(total_frames, duration)
            
            # Extract frames
            for frame_idx in frame_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                
                if ret:
                    timestamp = frame_idx / fps if fps > 0 else 0
                    
                    # Process and encode frame
                    base64_image = self._process_frame(frame)
                    if base64_image:
                        frames.append((base64_image, timestamp))
                        logger.debug(f"Extracted frame at {timestamp:.2f}s")
                
            cap.release()
            
        except Exception as e:
            logger.error(f"OpenCV frame extraction error: {str(e)}")
            
        return frames
    
    def _calculate_frame_indices(self, total_frames: int, duration: float) -> List[int]:
        """Calculate which frames to extract for analysis"""
        if total_frames <= self.max_frames:
            # Extract all frames if video is short
            return list(range(0, total_frames, max(1, total_frames // self.max_frames)))
        
        # For longer videos, extract frames at strategic points
        indices = []
        
        # Always include first frame
        indices.append(0)
        
        # Extract frames evenly distributed through the video
        step = total_frames // (self.max_frames - 2)
        for i in range(1, self.max_frames - 1):
            indices.append(min(i * step, total_frames - 1))
        
        # Always include last frame
        if total_frames > 1:
            indices.append(total_frames - 1)
        
        return sorted(set(indices))  # Remove duplicates and sort
    
    def _process_frame(self, frame) -> Optional[str]:
        """Process frame and convert to base64"""
        try:
            # Resize frame for consistent analysis
            height, width = frame.shape[:2]
            target_width, target_height = self.frame_size
            
            # Calculate aspect ratio preserving resize
            aspect = width / height
            if aspect > (target_width / target_height):
                # Video is wider - fit by width
                new_width = target_width
                new_height = int(target_width / aspect)
            else:
                # Video is taller - fit by height
                new_height = target_height
                new_width = int(target_height * aspect)
            
            # Resize frame
            resized = cv2.resize(frame, (new_width, new_height))
            
            # Convert BGR to RGB (OpenCV uses BGR)
            rgb_frame = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            
            # Convert to PIL Image
            pil_image = Image.fromarray(rgb_frame)
            
            # Convert to base64
            buffer = BytesIO()
            pil_image.save(buffer, format='JPEG', quality=90)
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            return image_base64
            
        except Exception as e:
            logger.error(f"Frame processing error: {str(e)}")
            return None
    
    def get_frame_analysis_prompt(self, sport_type: str = "climbing") -> str:
        """ULTRA EXPLICIT prompt for move counting"""
        if sport_type in ['climbing', 'bouldering']:
            return """Analyze this climbing/bouldering image. MUST answer with exact numbers:

1. Technique score: [give a number 1-10]
2. TOTAL MOVES IN ROUTE: [count every single hold from bottom to top - give exact number like "8 moves" or "12 moves"]
3. Hold analysis: [describe key holds visible]
4. Movement tip: [one specific improvement]

EXAMPLE RESPONSE:
1. Technique score: 7/10
2. TOTAL MOVES IN ROUTE: 11 moves
3. Hold analysis: Mix of jugs and crimps
4. Movement tip: Better hip positioning

Your response:"""
        else:
            return f"Analyze {sport_type}: rate 1-10, count total moves as number, brief tip."


# Global service instance
frame_extraction_service = FrameExtractionService()