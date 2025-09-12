"""
Upload data models
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class VideoUpload(BaseModel):
    id: str
    filename: str
    original_filename: str
    file_size: int
    content_type: str
    s3_key: str
    s3_bucket: str
    upload_status: str
    created_at: datetime
    user_id: Optional[str] = None


class UploadResponse(BaseModel):
    upload_id: str
    upload_url: str
    file_key: str
    expires_in: int


class UploadStatus(BaseModel):
    upload_id: str
    status: str
    progress: float
    error_message: Optional[str] = None
