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
        self.max_frames = 5  # Extract 5 frames across entire video for full route analysis
        self.frame_size = (640, 480)  # Higher resolution for better AI analysis
        self.min_interval = 3.0  # Minimum seconds between frames
        
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
                return {
                    'frames': [],
                    'video_duration': 0,
                    'total_frames': 0,
                    'fps': 0,
                    'success': False,
                    'error': 'Could not get video file'
                }
            
            # Extract frames using OpenCV
            extraction_result = self._extract_frames_opencv(temp_video_path)
            
            # Clean up temporary file
            if temp_video_path.startswith('/tmp'):
                try:
                    os.remove(temp_video_path)
                except:
                    pass
                    
            # extraction_result is now a dict with all metadata
            logger.warning(f"🎥 EXTRACTION COMPLETE: {len(extraction_result.get('frames', []))} frames from {extraction_result.get('video_duration', 0):.1f}s video")
            
            return extraction_result
            
        except Exception as e:
            logger.error(f"Frame extraction failed for {analysis_id}: {str(e)}")
            return {
                'frames': [],
                'video_duration': 0,
                'total_frames': 0,
                'fps': 0,
                'success': False,
                'error': str(e)
            }
    
    async def _get_video_file(self, video_path: str, analysis_id: str) -> Optional[str]:
        """Get video file path (download from S3 or memory storage if needed)"""
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
                logger.info(f"📦 Downloading video from S3: {s3_key} -> {temp_path}")
                success = await s3_service.download_file(s3_key, temp_path)
                if success:
                    file_size = os.path.getsize(temp_path) if os.path.exists(temp_path) else 0
                    logger.info(f"✅ S3 download successful: {file_size/(1024*1024):.1f}MB")
                    return temp_path
                else:
                    logger.error(f"❌ Failed to download video from S3: {s3_key}")
                    
                    # FALLBACK: Try memory storage if S3 fails
                    logger.warning(f"🔄 S3 failed, trying memory storage for {analysis_id}")
                    return await self._get_video_from_memory(analysis_id)
            else:
                # Local video path
                if os.path.exists(video_path):
                    return video_path
                else:
                    logger.error(f"Video file not found: {video_path}")
                    # FALLBACK: Try memory storage if local file not found
                    logger.warning(f"🔄 Local file not found, trying memory storage for {analysis_id}")
                    return await self._get_video_from_memory(analysis_id)
                    
        except Exception as e:
            logger.error(f"Error getting video file: {str(e)}")
            return None
    
    async def _get_video_from_memory(self, analysis_id: str) -> Optional[str]:
        """Try to get video from memory storage and write to temp file"""
        try:
            # Import video_storage from main module
            from app.main import video_storage
            
            if analysis_id in video_storage:
                video_info = video_storage[analysis_id]
                video_content = video_info.get('content')
                
                if video_content:
                    # Create temp file and write content
                    temp_fd, temp_path = tempfile.mkstemp(suffix='.mp4')
                    
                    with os.fdopen(temp_fd, 'wb') as temp_file:
                        temp_file.write(video_content)
                    
                    file_size = len(video_content)
                    logger.info(f"✅ Memory storage retrieval successful: {file_size/(1024*1024):.1f}MB -> {temp_path}")
                    return temp_path
                else:
                    logger.error(f"❌ Video content not found in memory storage for {analysis_id}")
                    return None
            else:
                logger.error(f"❌ Analysis ID {analysis_id} not found in memory storage")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving video from memory storage: {str(e)}")
            return None
    
    def _extract_frames_opencv(self, video_path: str) -> dict:
        """Extract frames using OpenCV and return metadata"""
        frames = []
        video_duration = 0
        total_frames = 0
        fps = 0
        
        try:
            # Open video
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logger.error(f"Could not open video: {video_path}")
                return {
                    'frames': frames,
                    'video_duration': 0,
                    'total_frames': 0,
                    'fps': 0,
                    'success': False,
                    'error': 'Could not open video with OpenCV'
                }
            
            # Get video properties
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            video_duration = total_frames / fps if fps > 0 else 0
            
            logger.warning(f"🎥 VIDEO ANALYSIS: {total_frames} frames, {fps:.2f} FPS, {video_duration:.1f}s duration")
            logger.warning(f"🎥 VIDEO SIZE: {os.path.getsize(video_path)/(1024*1024):.1f}MB")
            
            # Calculate frame indices to extract
            frame_indices = self._calculate_frame_indices(total_frames, video_duration)
            logger.warning(f"🎥 FRAME EXTRACTION: Will extract {len(frame_indices)} frames from {video_duration:.1f}s video")
            
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
                        logger.warning(f"✅ FRAME EXTRACTED: {len(frames)}/{len(frame_indices)} at {timestamp:.2f}s (frame {frame_idx}/{total_frames})")
                
            cap.release()
            
        except Exception as e:
            logger.error(f"OpenCV frame extraction error: {str(e)}")
            return {
                'frames': frames,
                'video_duration': video_duration,
                'total_frames': total_frames,
                'fps': fps,
                'success': False,
                'error': str(e)
            }
            
        # Return successful result with metadata
        return {
            'frames': frames,
            'video_duration': video_duration,
            'total_frames': total_frames, 
            'fps': fps,
            'success': len(frames) > 0
        }
    
    def _calculate_frame_indices(self, total_frames: int, duration: float) -> List[int]:
        """Calculate which frames to extract for complete route analysis"""
        indices = []
        
        if duration <= 10:  # Short videos - extract more frames
            # For short videos, extract frames every 2 seconds
            fps = total_frames / duration if duration > 0 else 24
            interval_frames = int(fps * 2)  # Every 2 seconds
            indices = list(range(0, total_frames, max(1, interval_frames)))
        else:
            # For longer videos, extract strategically across the entire duration
            # Start (0-10%), Early climb (20%), Mid climb (40%), Late climb (70%), Finish (90-100%)
            key_percentages = [0.05, 0.25, 0.45, 0.65, 0.85, 0.95]  # 6 strategic points
            
            for percentage in key_percentages:
                frame_idx = int(total_frames * percentage)
                indices.append(min(frame_idx, total_frames - 1))
        
        # Remove duplicates, sort, and limit to max_frames
        indices = sorted(set(indices))[:self.max_frames]
        
        # Ensure we always have at least start and end frames
        if len(indices) < 2 and total_frames > 1:
            indices = [0, total_frames - 1]
        
        logger.info(f"Selected frame indices for {duration:.1f}s video: {indices}")
        return indices
    
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
        """AI prompt focused on visual analysis to reduce hallucinations"""
        if sport_type in ['climbing', 'bouldering']:
            return """You are analyzing a climbing video frame. Please analyze what you can see and provide a structured assessment.

Please provide your analysis in this format:

1. TECHNIQUE RATING: [score]/10
2. ROUTE COLOR: [main color of holds being used]
3. VISIBLE MOVES IN FRAME: [number] moves
4. HOLD TYPES ON ROUTE: [types of holds visible]
5. VISUAL DIFFICULTY: [score]/10
6. MOVEMENT QUALITY: [brief assessment]

Example:
1. TECHNIQUE RATING: 7/10
2. ROUTE COLOR: white
3. VISIBLE MOVES IN FRAME: 3 moves
4. HOLD TYPES ON ROUTE: Large holds and smaller grips
5. VISUAL DIFFICULTY: 5/10
6. MOVEMENT QUALITY: Balanced positioning"""
        else:
            return f"Analyze {sport_type}: rate 1-10, count total moves as number, brief tip."


# Global service instance
frame_extraction_service = FrameExtractionService()