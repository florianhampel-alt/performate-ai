"""
AWS S3 service for video storage and retrieval
"""

import boto3
import aioboto3
from typing import Optional, BinaryIO
from app.config.base import settings
from app.utils.logger import get_logger
from datetime import datetime
import uuid

logger = get_logger(__name__)


class S3Service:
    def __init__(self):
        # Check if S3 is configured
        if not all([settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY, settings.S3_BUCKET]):
            logger.warning("S3 credentials not configured - S3 functionality disabled")
            self.enabled = False
            return
            
        self.enabled = True
        self.bucket = settings.S3_BUCKET
        self.region = settings.AWS_REGION
        
        # Sync client for compatibility
        self.client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        
        logger.info(f"S3 service initialized for bucket: {self.bucket}")

    async def upload_file(self, file: BinaryIO, key: str) -> bool:
        """Upload file to S3"""
        if not self.enabled:
            logger.warning("S3 not configured - cannot upload file")
            return False
            
        try:
            self.client.upload_fileobj(file, self.bucket, key)
            logger.info(f"Successfully uploaded file to S3: {key}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload file to S3: {str(e)}")
            return False

    async def upload_video_stream(
        self, 
        video_stream, 
        filename: str, 
        analysis_id: str,
        content_type: str = "video/mp4",
        file_size: int = 0
    ) -> Optional[str]:
        """
        Upload video via streaming to S3 without loading into memory
        
        Args:
            video_stream: Streaming video data (FastAPI UploadFile)
            filename: Original filename
            analysis_id: Unique analysis ID
            content_type: MIME type
            file_size: File size for metadata
            
        Returns:
            S3 key if successful, None if failed
        """
        if not self.enabled:
            logger.warning("S3 not configured - cannot upload video")
            return None
            
        try:
            # Generate S3 key
            timestamp = datetime.now().strftime("%Y/%m/%d")
            file_extension = filename.split('.')[-1] if '.' in filename else 'mp4'
            s3_key = f"videos/{timestamp}/{analysis_id}.{file_extension}"
            
            # Upload to S3 using multipart upload for large files
            session = aioboto3.Session(
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=self.region
            )
            
            async with session.client('s3') as s3:
                # Use streaming upload - no memory loading
                await s3.upload_fileobj(
                    video_stream,
                    self.bucket,
                    s3_key,
                    ExtraArgs={
                        'ContentType': content_type,
                        'Metadata': {
                            'analysis_id': analysis_id,
                            'original_filename': filename,
                            'upload_timestamp': datetime.now().isoformat(),
                            'file_size': str(file_size)
                        }
                    }
                )
                
            logger.info(f"Successfully streamed video to S3: {s3_key} ({file_size/(1024*1024):.1f}MB)")
            return s3_key
            
        except Exception as e:
            logger.error(f"Failed to stream video to S3: {str(e)}")
            return None

    async def upload_video(
        self, 
        video_content: bytes, 
        filename: str, 
        analysis_id: str,
        content_type: str = "video/mp4"
    ) -> Optional[str]:
        """
        Upload video to S3 and return the S3 key
        
        Args:
            video_content: Raw video bytes
            filename: Original filename
            analysis_id: Unique analysis ID
            content_type: MIME type
            
        Returns:
            S3 key if successful, None if failed
        """
        if not self.enabled:
            logger.warning("S3 not configured - cannot upload video")
            return None
            
        try:
            # Generate S3 key
            timestamp = datetime.now().strftime("%Y/%m/%d")
            file_extension = filename.split('.')[-1] if '.' in filename else 'mp4'
            s3_key = f"videos/{timestamp}/{analysis_id}.{file_extension}"
            
            # Upload to S3 using async client
            session = aioboto3.Session(
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=self.region
            )
            
            async with session.client('s3') as s3:
                await s3.put_object(
                    Bucket=self.bucket,
                    Key=s3_key,
                    Body=video_content,
                    ContentType=content_type,
                    Metadata={
                        'analysis_id': analysis_id,
                        'original_filename': filename,
                        'upload_timestamp': datetime.now().isoformat(),
                        'file_size': str(len(video_content))
                    }
                )
                
            logger.info(f"Successfully uploaded video to S3: {s3_key} ({len(video_content)/(1024*1024):.1f}MB)")
            return s3_key
            
        except Exception as e:
            logger.error(f"Failed to upload video to S3: {str(e)}")
            return None

    async def generate_presigned_url(self, key: str, expires_in: int = 3600) -> Optional[str]:
        """Generate presigned URL for file access"""
        if not self.enabled:
            logger.warning("S3 not configured - cannot generate presigned URL")
            return None
            
        try:
            url = self.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': key},
                ExpiresIn=expires_in
            )
            logger.info(f"Generated presigned URL for {key} (expires in {expires_in}s)")
            return url
        except Exception as e:
            logger.error(f"Failed to generate presigned URL: {str(e)}")
            return None

    async def delete_file(self, key: str) -> bool:
        """Delete file from S3"""
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
            logger.info(f"Successfully deleted file from S3: {key}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete file from S3: {str(e)}")
            return False


s3_service = S3Service()
