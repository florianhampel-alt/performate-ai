"""
AWS S3 service for file upload/download operations
"""

import boto3
from typing import Optional, BinaryIO
from app.config.base import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class S3Service:
    def __init__(self):
        self.client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        self.bucket = settings.S3_BUCKET

    async def upload_file(self, file: BinaryIO, key: str) -> bool:
        """Upload file to S3"""
        try:
            self.client.upload_fileobj(file, self.bucket, key)
            logger.info(f"Successfully uploaded file to S3: {key}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload file to S3: {str(e)}")
            return False

    async def generate_presigned_url(self, key: str, expires_in: int = 3600) -> Optional[str]:
        """Generate presigned URL for file access"""
        try:
            url = self.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': key},
                ExpiresIn=expires_in
            )
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
