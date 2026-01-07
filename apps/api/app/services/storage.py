import os
import shutil
from pathlib import Path
from typing import BinaryIO
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class StorageService:
    def __init__(self):
        self.mode = settings.storage_mode
        
        if self.mode == "local":
            self.base_path = Path(settings.local_storage_path)
            self.base_path.mkdir(parents=True, exist_ok=True)
        elif self.mode == "s3":
            # S3 setup would go here
            raise NotImplementedError("S3 storage not yet implemented")
    
    def save_upload(self, upload_id: int, filename: str, file_obj: BinaryIO) -> str:
        """Save uploaded file and return storage path"""
        if self.mode == "local":
            upload_dir = self.base_path / "uploads" / str(upload_id)
            upload_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = upload_dir / filename
            
            with open(file_path, "wb") as f:
                shutil.copyfileobj(file_obj, f)
            
            return str(file_path.relative_to(self.base_path))
        
        raise NotImplementedError(f"Storage mode {self.mode} not implemented")
    
    def get_full_path(self, storage_path: str) -> Path:
        """Get full filesystem path from storage path"""
        if self.mode == "local":
            return self.base_path / storage_path
        
        raise NotImplementedError(f"Storage mode {self.mode} not implemented")
    
    def save_transcript(self, job_id: int, transcript_text: str) -> str:
        """Save transcript text file and return path"""
        if self.mode == "local":
            transcript_dir = self.base_path / "transcripts"
            transcript_dir.mkdir(parents=True, exist_ok=True)
            
            transcript_file = transcript_dir / f"job_{job_id}.txt"
            
            with open(transcript_file, "w", encoding="utf-8") as f:
                f.write(transcript_text)
            
            return str(transcript_file.relative_to(self.base_path))
        
        raise NotImplementedError(f"Storage mode {self.mode} not implemented")
    
    def get_audio_path(self, job_id: int) -> Path:
        """Get path for converted audio file"""
        if self.mode == "local":
            audio_dir = self.base_path / "audio"
            audio_dir.mkdir(parents=True, exist_ok=True)
            return audio_dir / f"job_{job_id}.wav"
        
        raise NotImplementedError(f"Storage mode {self.mode} not implemented")


storage_service = StorageService()








