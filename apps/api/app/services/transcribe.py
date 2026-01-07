import httpx
from pathlib import Path
from typing import Dict, Any, List, Optional
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class TranscriptionService:
    def __init__(self):
        self.provider = settings.transcribe_provider
    
    async def transcribe(self, audio_path: Path) -> Dict[str, Any]:
        """
        Transcribe audio file
        Returns: {
            "text": str,
            "segments": [{"start": float, "end": float, "text": str, "speaker": Optional[str]}]
        }
        """
        if self.provider == "whisper_local":
            # This will be handled by the worker with actual whisper
            raise NotImplementedError("Local whisper transcription handled by worker")
        
        elif self.provider == "api":
            return await self._transcribe_api(audio_path)
        
        else:
            raise ValueError(f"Unknown transcription provider: {self.provider}")
    
    async def _transcribe_api(self, audio_path: Path) -> Dict[str, Any]:
        """Transcribe using external API"""
        if not settings.transcribe_api_url:
            raise ValueError("TRANSCRIBE_API_URL not configured")
        
        async with httpx.AsyncClient(timeout=600.0) as client:
            with open(audio_path, "rb") as f:
                files = {"file": (audio_path.name, f, "audio/wav")}
                headers = {}
                
                if settings.transcribe_api_key:
                    headers["Authorization"] = f"Bearer {settings.transcribe_api_key}"
                
                response = await client.post(
                    settings.transcribe_api_url,
                    files=files,
                    headers=headers
                )
                response.raise_for_status()
                return response.json()


transcription_service = TranscriptionService()








