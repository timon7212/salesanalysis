import httpx
import json
from typing import Dict, Any
from app.config import settings
from app.schemas import ExtractionResult
import logging

logger = logging.getLogger(__name__)


EXTRACTION_PROMPT = """You are analyzing a sales call transcript. Extract structured information in JSON format.

Transcript:
{transcript}

Extract the following information and return ONLY valid JSON:
{{
  "call_summary": ["bullet point 1", "bullet point 2", ...],
  "concerns": [
    {{
      "type": "pricing|technical|competition|timeline|other",
      "severity": 1-5,
      "detail": "description",
      "evidence_quotes": [
        {{"text": "quote from transcript", "timestamp": "MM:SS or null"}}
      ]
    }}
  ],
  "next_steps": [
    {{
      "action": "what needs to be done",
      "owner": "who should do it (sales rep, customer, team)",
      "suggested_due_days": 7
    }}
  ],
  "qualification": {{
    "budget": "confirmed|discussing|unknown",
    "timeline": "description or unknown",
    "decision_maker": "name or role or unknown",
    "need": "description of customer need",
    "score": 0-100
  }},
  "confidence": 0.0-1.0
}}

Return ONLY the JSON object, no other text."""


class LLMService:
    def __init__(self):
        self.provider = settings.llm_provider
        self.api_base = settings.llm_api_base_url
        self.api_key = settings.llm_api_key
        self.model = settings.llm_model
    
    async def extract_from_transcript(self, transcript: str) -> ExtractionResult:
        """Extract structured data from transcript using LLM"""
        
        if self.provider == "openai":
            result_json = await self._call_openai(transcript)
        elif self.provider == "generic":
            result_json = await self._call_generic(transcript)
        else:
            raise ValueError(f"Unknown LLM provider: {self.provider}")
        
        # Parse and validate with Pydantic
        return ExtractionResult(**result_json)
    
    async def _call_openai(self, transcript: str) -> Dict[str, Any]:
        """Call OpenAI API"""
        prompt = EXTRACTION_PROMPT.format(transcript=transcript)
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.api_base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "You are a sales call analyzer. Always return valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "response_format": {"type": "json_object"}
                }
            )
            response.raise_for_status()
            
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            
            # Parse JSON from response
            return json.loads(content)
    
    async def _call_generic(self, transcript: str) -> Dict[str, Any]:
        """Call generic LLM API (compatible with OpenAI format)"""
        return await self._call_openai(transcript)


llm_service = LLMService()








