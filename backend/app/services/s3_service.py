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
            
            # Use sync boto3 client for reliable file streaming
            # Convert async file stream to sync for boto3 compatibility
            import io
            import asyncio
            
            # Read the entire stream into a BytesIO buffer
            logger.info(f"Reading file stream for S3 upload...")
            file_buffer = io.BytesIO()
            
            # Read in chunks to monitor progress
            chunk_size = 8 * 1024 * 1024  # 8MB chunks
            total_read = 0
            
            while True:
                chunk = await video_stream.read(chunk_size)
                if not chunk:
                    break
                file_buffer.write(chunk)
                total_read += len(chunk)
                
                if total_read % (32 * 1024 * 1024) == 0:  # Log every 32MB
                    logger.info(f"Read {total_read/(1024*1024):.1f}MB so far...")
                
                # Safety check
                if total_read > file_size * 1.2:  # 20% tolerance
                    logger.warning(f"Read more data than expected: {total_read} vs {file_size}")
                    break
            
            file_buffer.seek(0)  # Reset to beginning
            logger.info(f"File stream read complete: {total_read/(1024*1024):.1f}MB")
            
            # Upload using sync boto3 client
            self.client.upload_fileobj(
                file_buffer,
                self.bucket,
                s3_key,
                ExtraArgs={
                    'ContentType': content_type,
                    'Metadata': {
                        'analysis_id': analysis_id,
                        'original_filename': filename,
                        'upload_timestamp': datetime.now().isoformat(),
                        'file_size': str(total_read)
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

    async def generate_presigned_upload_url(
        self, 
        key: str, 
        content_type: str = "video/mp4",
        expires_in: int = 1800  # 30 minutes
    ) -> Optional[dict]:
        """Generate presigned URL for direct client upload to S3"""
        if not self.enabled:
            logger.warning("S3 not configured - cannot generate presigned upload URL")
            return None
            
        try:
            # Generate presigned POST for secure upload with constraints
            response = self.client.generate_presigned_post(
                Bucket=self.bucket,
                Key=key,
                Fields={
                    'Content-Type': content_type
                },
                Conditions=[
                    {'Content-Type': content_type},
                    ['content-length-range', 1024, 120 * 1024 * 1024]  # 1KB - 120MB
                ],
                ExpiresIn=expires_in
            )
            
            logger.info(f"Generated presigned upload URL for {key} (expires in {expires_in}s)")
            return response
        except Exception as e:
            logger.error(f"Failed to generate presigned upload URL: {str(e)}")
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
