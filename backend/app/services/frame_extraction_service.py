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

# Import imageio with error handling
try:
    import imageio
    import imageio.v3 as iio
    IMAGEIO_AVAILABLE = True
except ImportError:
    IMAGEIO_AVAILABLE = False
    imageio = None
    iio = None

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
            
            # Debug video file before extraction
            if os.path.exists(temp_video_path):
                file_size = os.path.getsize(temp_video_path)
                logger.warning(f"🎬 VIDEO FILE DEBUG: {temp_video_path}, Size: {file_size/(1024*1024):.2f}MB")
                
                # Additional file validation
                if file_size < 1024:  # Less than 1KB indicates corrupted download
                    logger.error(f"❌ VIDEO FILE TOO SMALL: {file_size} bytes - likely corrupted download")
                    raise Exception(f"Video file is too small ({file_size} bytes) - download likely failed")
                    
            else:
                logger.error(f"❌ VIDEO FILE NOT FOUND: {temp_video_path}")
                raise Exception(f"Video file not found after download: {temp_video_path}")
                
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
        
        # TRY IMAGEIO FIRST (more robust than OpenCV)
        try:
            logger.warning(f"🔍 TRYING IMAGEIO for video processing (more robust)")
            
            # Check imageio availability
            if not IMAGEIO_AVAILABLE:
                logger.error(f"❌ IMAGEIO NOT AVAILABLE - was not imported successfully")
                raise Exception(f"Imageio not installed - this should have been installed in build step")
            
            logger.warning(f"✅ IMAGEIO AVAILABLE: {imageio.__version__ if hasattr(imageio, '__version__') else 'version unknown'}")
            
            # Get video properties with imageio
            props = iio.improps(video_path)
            fps = props.get('fps', 24.0)
            total_frames = props.get('count', 0) 
            video_duration = total_frames / fps if fps > 0 and total_frames > 0 else 0
            
            logger.warning(f"🎬 IMAGEIO SUCCESS: {total_frames} frames, {fps:.2f} FPS, {video_duration:.1f}s")
            
            # Calculate frame indices to extract
            frame_indices = self._calculate_frame_indices(total_frames, video_duration)
            logger.warning(f"🎬 IMAGEIO EXTRACTION: Will extract {len(frame_indices)} frames")
            
            # Extract frames using imageio
            for i, frame_idx in enumerate(frame_indices):
                try:
                    # Read specific frame
                    frame = iio.imread(video_path, index=frame_idx)
                    timestamp = frame_idx / fps if fps > 0 else 0
                    
                    # Convert to PIL Image
                    pil_image = Image.fromarray(frame)
                    
                    # Process frame same as OpenCV method
                    base64_image = self._process_pil_image(pil_image)
                    if base64_image:
                        # Debug image data
                        img_size = len(base64_image)
                        img_preview = base64_image[:50] + "..." if len(base64_image) > 50 else base64_image
                        logger.warning(f"✅ IMAGEIO FRAME EXTRACTED: {len(frames)+1}/{len(frame_indices)} at {timestamp:.2f}s (frame {frame_idx}/{total_frames})")
                        logger.warning(f"   🖼️ Image size: {img_size} chars, Preview: {img_preview}")
                        frames.append((base64_image, timestamp))
                    else:
                        logger.error(f"❌ IMAGEIO FRAME PROCESSING FAILED at {timestamp:.2f}s (frame {frame_idx})")
                        
                except Exception as frame_err:
                    logger.error(f"Imageio frame {i} extraction failed: {frame_err}")
                    continue
            
            return {
                'frames': frames,
                'video_duration': video_duration,
                'total_frames': total_frames,
                'fps': fps,
                'success': len(frames) > 0,
                'extraction_method': 'imageio'
            }
            
        except Exception as imageio_err:
            logger.error(f"Imageio extraction failed: {imageio_err}")
            logger.warning(f"🔄 IMAGEIO FAILED - Trying OpenCV fallback")
            
        # FALLBACK TO OPENCV
        try:
            # Debug OpenCV version and capabilities
            logger.warning(f"🔍 OPENCV DEBUG: Version {cv2.__version__}")
            logger.warning(f"🔍 VIDEO CODECS: {cv2.getBuildInformation().split('Video I/O')[1][:500] if 'Video I/O' in cv2.getBuildInformation() else 'Info not available'}")
            
            # Open video
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logger.error(f"Could not open video: {video_path}")
                logger.error(f"🔍 OPENCV BACKENDS: {[cv2.videoio_registry.getBackendName(b) for b in cv2.videoio_registry.getBackends()]}")
                return {
                    'frames': frames,
                    'video_duration': 0,
                    'total_frames': 0,
                    'fps': 0,
                    'success': False,
                    'error': 'Both imageio and OpenCV failed to open video'
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
                        # Debug image data
                        img_size = len(base64_image)
                        img_preview = base64_image[:50] + "..." if len(base64_image) > 50 else base64_image
                        logger.warning(f"✅ FRAME EXTRACTED: {len(frames)+1}/{len(frame_indices)} at {timestamp:.2f}s (frame {frame_idx}/{total_frames})")
                        logger.warning(f"   🖼️ Image size: {img_size} chars, Preview: {img_preview}")
                        frames.append((base64_image, timestamp))
                    else:
                        logger.error(f"❌ FRAME PROCESSING FAILED at {timestamp:.2f}s (frame {frame_idx})")
                
            cap.release()
            
        except Exception as e:
            logger.error(f"OpenCV frame extraction error: {str(e)}")
            logger.error(f"📊 OPENCV TRACEBACK: {str(e)}")
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
        """Calculate strategic frame indices with performance optimization"""
        # Optimize for climbing videos: key positions in route progression
        if duration <= 15:
            # Short routes: focus on start, middle, end + 2 transition points
            percentages = [0.05, 0.3, 0.5, 0.7, 0.95]
        else:
            # Long routes: add more progression points
            percentages = [0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95]
        
        indices = []
        for pct in percentages[:self.max_frames]:
            frame_idx = min(int(total_frames * pct), total_frames - 1)
            indices.append(frame_idx)
        
        # Remove duplicates and ensure minimum spread
        indices = sorted(set(indices))
        
        # Ensure minimum frame spacing (avoid analyzing nearly identical frames)
        if len(indices) > 1:
            min_spacing = max(24, total_frames // 20)  # At least 1s spacing or 5% of video
            filtered_indices = [indices[0]]  # Always keep first frame
            
            for idx in indices[1:]:
                if idx - filtered_indices[-1] >= min_spacing:
                    filtered_indices.append(idx)
                elif len(filtered_indices) < 3:  # Ensure minimum 3 frames
                    filtered_indices.append(idx)
            
            indices = filtered_indices
        
        logger.info(f"Optimized frame selection for {duration:.1f}s: {len(indices)} frames at indices {indices}")
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
            image_bytes = buffer.getvalue()
            
            # Debug buffer content
            logger.warning(f"🖼️ BUFFER DEBUG: {len(image_bytes)} bytes before base64 encoding")
            
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # Validate base64
            if len(image_base64) < 1000:  # Very small images indicate problems
                logger.error(f"❌ BASE64 IMAGE TOO SMALL: {len(image_base64)} chars")
                return None
                
            # Test base64 validity
            try:
                decoded_test = base64.b64decode(image_base64[:100])  # Test first 100 chars
                logger.warning(f"✅ BASE64 VALIDATION: OK, {len(image_base64)} chars total")
            except Exception as b64_err:
                logger.error(f"❌ BASE64 INVALID: {b64_err}")
                return None
            
            return image_base64
            
        except Exception as e:
            logger.error(f"Frame processing error: {str(e)}")
            return None
    
    def _process_pil_image(self, pil_image: Image.Image) -> Optional[str]:
        """Process PIL Image and convert to base64 (for imageio compatibility)"""
        try:
            # Resize image for consistent analysis
            original_width, original_height = pil_image.size
            target_width, target_height = self.frame_size
            
            # Calculate aspect ratio preserving resize
            aspect = original_width / original_height
            if aspect > (target_width / target_height):
                # Image is wider - fit by width
                new_width = target_width
                new_height = int(target_width / aspect)
            else:
                # Image is taller - fit by height
                new_height = target_height
                new_width = int(target_height * aspect)
            
            # Resize image
            resized_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Convert to base64
            buffer = BytesIO()
            resized_image.save(buffer, format='JPEG', quality=90)
            image_bytes = buffer.getvalue()
            
            # Debug buffer content
            logger.warning(f"🖼️ PIL BUFFER DEBUG: {len(image_bytes)} bytes before base64 encoding")
            
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # Validate base64
            if len(image_base64) < 1000:  # Very small images indicate problems
                logger.error(f"❌ PIL BASE64 IMAGE TOO SMALL: {len(image_base64)} chars")
                return None
                
            # Test base64 validity
            try:
                decoded_test = base64.b64decode(image_base64[:100])  # Test first 100 chars
                logger.warning(f"✅ PIL BASE64 VALIDATION: OK, {len(image_base64)} chars total")
            except Exception as b64_err:
                logger.error(f"❌ PIL BASE64 INVALID: {b64_err}")
                return None
            
            return image_base64
            
        except Exception as e:
            logger.error(f"PIL image processing error: {str(e)}")
            return None
    
    def get_frame_analysis_prompt(self, sport_type: str = "climbing") -> str:
        """Enhanced AI prompt - memory-optimized for production deployment"""
        if sport_type in ['climbing', 'bouldering']:
            # Memory-optimized version for Render deployment
            return self._get_enhanced_climbing_prompt()
        else:
            return f"Analyze {sport_type}: rate technique 1-10, count moves, assess difficulty independent of colors."
    
    def _get_enhanced_climbing_prompt(self) -> str:
        """OpenAI-compliant enhanced climbing analysis prompt"""
        return """Du bist ein Kletter-Coach für Technikanalyse. Analysiere die sichtbaren Klettertechniken und Bewegungsmuster in diesem Bild.

WICHTIG: Konzentriere dich nur auf Klettertechniken, Körperpositionen und Bewegungen - NICHT auf die Identifikation von Personen.

# TECHNISCHE ANALYSE-BEREICHE

## KÖRPERPOSITION & TECHNIK
- Hüftposition zur Wand (optimal: nah an der Wand)
- Armposition (gestreckt vs. gebeugt)
- Fußplatzierung und Präzision
- Körperspannung und Balance
- Bewegungseffizienz

## GRIFFTECHNIKEN
- Grifftypen: Jug, Crimp, Sloper, Pinch, Pocket
- Griffgrößen: Large, Medium, Small, Tiny
- Hold-Qualität und Nutzung

## ROUTE-EIGENSCHAFTEN
- Wandwinkel: Vertical, Slab, Overhang, Roof
- Routenfarbe (für Orientierung)
- Schwierigkeitsbereich basierend auf sichtbaren Holds
- Bewegungssequenz-Typ

## LEISTUNGSEBENEN

**ANFÄNGER-MERKMALE:**
- Hauptsächlich Armkraft statt Beinarbeit
- Hüfte weit von Wand (30-50cm)
- Hektische, unkontrollierte Bewegungen
- Ungenaue Fußplatzierung

**FORTGESCHRITTENE-MERKMALE:**
- Balance zwischen Arm- und Beinarbeit
- Bewusste Fußplatzierung
- Effizienzorientierte Bewegungen
- Verwendung verschiedener Grifftechniken

**PROFI-MERKMALE:**
- Perfekte Bewegungseffizienz
- Innovative Beta-Lösungen
- Präzise Kraftdosierung
- Flüssige, ästhetische Bewegungen

---

# ANALYSE-FORMAT

Analysiere in dieser Struktur:

## Routenidentifikation
**Farbe:** [Sichtbare Routenfarbe]
**Schwierigkeitsgrad:** [Geschätzter Grad basierend auf Holds, z.B. "V4-V5"]
**Stil:** [Wandwinkel: Vertical/Slab/Overhang/Roof]

## Technische Bewertung
**Geschätztes Level:** [Anfänger/Fortgeschritten/Erfahren/Profi]
**Begründung:** [Basierend auf sichtbare Techniken]

## Positive Technische Aspekte (3-4 Punkte)
✅ [Gute Körperposition beobachtet]
✅ [Effiziente Bewegungstechnik]
✅ [Korrekte Griffnutzung]
✅ [Andere technische Stärken]

## Technische Verbesserungen (3-4 Punkte)
⚠️ [Körperposition optimierbar]
⚠️ [Bewegungseffizienz steigerbar]
⚠️ [Grifftechnik verbesserbar]
⚠️ [Andere technische Aspekte]

## Konkrete Technik-Tipps (4-6 Punkte)
💡 [Spezifische Körperposition-Übung]
💡 [Grifftechnik-Verbesserung]
💡 [Bewegungssequenz-Training]
💡 [Fußarbeit-Übung]
💡 [Kraft-/Technik-Training]
💡 [Weitere praktische Empfehlung]

---

# ANALYSE-PRINZIPIEN

1. **Fokus auf Technik:** Nur Bewegungen und Körperpositionen analysieren
2. **Konkrete Beobachtungen:** Spezifische technische Details
3. **Konstruktives Feedback:** Verbesserungsvorschläge mit Übungen
4. **Level-appropriate:** Tipps basierend auf erkanntem Können
5. **Messbare Aspekte:** Konkrete Distanzen, Winkel, Positionen

Analysiere nun die sichtbaren Klettertechniken in diesem Bild!"""


# Global service instance
frame_extraction_service = FrameExtractionService()
