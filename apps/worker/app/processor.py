import subprocess
import json
from pathlib import Path
from typing import Dict, Any
import logging
import httpx
import asyncio

from app.config import settings

logger = logging.getLogger(__name__)


class CallProcessor:
    def __init__(self):
        self.storage_path = Path(settings.local_storage_path)
    
    def convert_to_audio(self, upload_storage_path: str, job_id: int) -> Path:
        """Convert uploaded file to wav 16kHz mono using ffmpeg"""
        # Build full path - storage_path should be /storage
        input_path = self.storage_path / upload_storage_path
        
        logger.info(f"Storage base path: {self.storage_path}")
        logger.info(f"Upload storage path: {upload_storage_path}")
        logger.info(f"Full input path: {input_path}")
        logger.info(f"File exists: {input_path.exists()}")
        
        if not input_path.exists():
            # List directory to debug
            parent_dir = input_path.parent
            if parent_dir.exists():
                logger.error(f"Parent directory contents: {list(parent_dir.iterdir())}")
            raise FileNotFoundError(f"Upload file not found: {input_path}")
        
        output_dir = self.storage_path / "audio"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"job_{job_id}.wav"
        
        # FFmpeg command: convert to 16kHz mono wav
        cmd = [
            "ffmpeg",
            "-i", str(input_path),
            "-ar", "16000",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            "-y",
            str(output_path)
        ]
        
        logger.info(f"Running ffmpeg: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"FFmpeg error: {result.stderr}")
            raise Exception(f"Audio conversion failed: {result.stderr}")
        
        logger.info(f"Audio converted successfully to {output_path}")
        return output_path
    
    def transcribe(self, audio_path: Path) -> Dict[str, Any]:
        """Transcribe audio using AssemblyAI"""
        if settings.transcribe_provider == "assemblyai":
            return self._transcribe_assemblyai(audio_path)
        else:
            raise ValueError(f"Unknown transcription provider: {settings.transcribe_provider}")
    
    def _transcribe_assemblyai(self, audio_path: Path) -> Dict[str, Any]:
        """Transcribe using AssemblyAI with speaker diarization"""
        import assemblyai as aai
        
        if not settings.assemblyai_api_key:
            raise ValueError("ASSEMBLYAI_API_KEY not configured")
        
        logger.info("Configuring AssemblyAI...")
        aai.settings.api_key = settings.assemblyai_api_key
        
        # Configure transcription with speaker diarization
        config = aai.TranscriptionConfig(
            speaker_labels=True,  # Enable speaker diarization
            speech_model=aai.SpeechModel.best,  # Use best quality model
        )
        
        transcriber = aai.Transcriber(config=config)
        
        logger.info(f"Uploading and transcribing {audio_path}...")
        transcript = transcriber.transcribe(str(audio_path))
        
        # Check for errors
        if transcript.status == aai.TranscriptStatus.error:
            raise RuntimeError(f"Transcription failed: {transcript.error}")
        
        logger.info("Transcription completed successfully")
        
        # Format segments with speaker labels
        segment_list = []
        
        logger.info(f"Has utterances: {bool(transcript.utterances)}")
        logger.info(f"Has words: {bool(transcript.words)}")
        
        if transcript.utterances:
            # Use utterances (speaker-aware segments)
            logger.info(f"Found {len(transcript.utterances)} utterances with speakers")
            for utterance in transcript.utterances:
                segment_list.append({
                    "start": utterance.start / 1000.0,  # Convert ms to seconds
                    "end": utterance.end / 1000.0,
                    "text": utterance.text.strip(),
                    "speaker": utterance.speaker  # Speaker A, Speaker B, etc.
                })
        elif transcript.words:
            # Fallback to words if utterances not available
            logger.warning("No utterances, falling back to words")
            current_speaker = None
            current_text = []
            current_start = None
            
            for word in transcript.words:
                speaker = getattr(word, 'speaker', None)
                
                if speaker and speaker != current_speaker:
                    # Save previous segment
                    if current_text:
                        segment_list.append({
                            "start": current_start / 1000.0,
                            "end": word.start / 1000.0,
                            "text": " ".join(current_text),
                            "speaker": current_speaker
                        })
                    # Start new segment
                    current_speaker = speaker
                    current_text = [word.text]
                    current_start = word.start
                else:
                    current_text.append(word.text)
            
            # Save last segment
            if current_text:
                segment_list.append({
                    "start": current_start / 1000.0,
                    "end": transcript.words[-1].end / 1000.0,
                    "text": " ".join(current_text),
                    "speaker": current_speaker
                })
        
        logger.info(f"Created {len(segment_list)} segments with speaker info")
        if segment_list:
            logger.info(f"Sample segment: {segment_list[0]}")
        
        return {
            "text": transcript.text.strip(),
            "segments": segment_list
        }
    
    def extract_insights(self, transcript: str) -> Dict[str, Any]:
        """Extract insights using LLM"""
        # Run async LLM call in sync context
        return asyncio.run(self._extract_insights_async(transcript))
    
    async def _extract_insights_async(self, transcript: str) -> Dict[str, Any]:
        """Extract insights using LLM (async)"""
        provider = settings.llm_provider
        
        prompt = self._build_extraction_prompt(transcript)
        
        if provider in ["openai", "generic"]:
            return await self._call_openai_llm(prompt)
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")
    
    def _build_extraction_prompt(self, transcript: str) -> str:
        """Build extraction prompt - Senior Sales Leader perspective"""
        return f"""You are a Senior Head of Sales with 15+ years of experience in B2B and high-ticket B2C sales.

Your task is NOT to summarize the call, but to DIAGNOSE it like a revenue leader reviewing a sales rep's performance.

Analyze the transcript below with extreme precision and skepticism.
Assume the deal can be lost unless clearly proven otherwise.

TRANSCRIPT:
{transcript}

=== ANALYSIS OBJECTIVES ===
1) IDENTIFY who is the Sales Rep and who is the Customer
2) Understand the CUSTOMER'S REAL BUYING INTENT (not surface politeness)
3) Identify TRUE DEAL BLOCKERS (not just surface questions)
4) Evaluate SALES REP'S PERFORMANCE and call control
5) Determine WHY the deal moved forward OR stalled
6) Recommend EXACT corrective actions

=== CRITICAL RULES ===
- Be concise but SHARP
- Do NOT repeat the transcript
- Do NOT hallucinate facts
- If unclear → mark explicitly as "unknown"
- Use direct quotes ONLY when proving a point
- Output valid JSON ONLY

---

### 0. SPEAKER IDENTIFICATION (CRITICAL - Must be first)
Analyze the conversation and identify who is the Sales Representative and who is the Customer.
Look for clues like:
- Who is ASKING questions vs ANSWERING them?
- Who is PITCHING/PRESENTING vs EVALUATING?
- Who mentions their COMPANY/PRODUCT vs their NEEDS/PROBLEMS?
- Who is LEADING the conversation vs RESPONDING?

Return mapping of Speaker labels to roles:
{{
  "speaker_roles": {{
    "Speaker A": "Sales Rep" | "Customer",
    "Speaker B": "Sales Rep" | "Customer",
    "Speaker C": "Sales Rep" | "Customer"  // if exists
  }}
}}

⚠️ If you cannot confidently determine roles, use "Unknown" for that speaker.
⚠️ Typically the FIRST speaker is the Sales Rep (they usually initiate), but verify from context.

---

### 1. CALL SUMMARY (Executive Briefing)
Provide 3-5 DIAGNOSTIC points (not a summary):
- What was the customer ACTUALLY trying to achieve? (not what sales rep pitched)
- What MOVED THE DEAL forward or backward?
- What is the REAL STATUS now?
- What's the BIGGEST RISK to closing?
- What's the ONE THING that must happen next?

### 2. DEAL BLOCKERS (CRITICAL - Only Real Blockers)
For each TRUE blocker that could kill the deal:
- type: pricing|trust|clarity|timing|authority|product_fit|execution|competition|other
- severity: 1-5 (4-5 = deal will NOT close unless fixed)
  * 1-2: Minor friction
  * 3: Needs addressing
  * 4: Major blocker
  * 5: Deal killer
- detail: WHY it matters in business terms (not just "customer concerned")
- evidence_quotes: Exact quotes proving this is a real blocker

⚠️ If no real blockers exist, return EMPTY array (don't invent problems)

### 3. NEXT STEPS (EXECUTABLE, NOT GENERIC)
For each action:
- action: Concrete, specific task (NOT "follow up" or "send info")
- owner: "sales_rep"|"customer"|"team"
- suggested_due_days: Realistic timeline
- why_critical: Why this step matters for closing (optional but recommended)

### 4. QUALIFICATION & DEAL READINESS
Evaluate with EXTREME skepticism:

- budget: "confirmed" (they have it) | "discussing" (unclear) | "unknown"
- timeline: Specific date/period OR "unknown" (not generic "soon")
- decision_maker: Name + Title OR "unknown" (who ACTUALLY signs?)
- need: What problem is customer solving? (in THEIR words, not yours)
- score: 0-100 (REAL buying readiness, not politeness)
  * 0-30: Just curious / exploring
  * 31-55: Interested but many unknowns
  * 56-75: Serious evaluation, comparing options
  * 76-90: Ready to buy with some fixes
  * 91-100: Buying NOW (contract/payment imminent)

### 5. CONFIDENCE
- confidence: 0.0-1.0
- reasoning: Why confident or not (e.g. "clear signals" vs "vague responses, missing info")

OUTPUT FORMAT (JSON only):
{{
  "speaker_roles": {{
    "Speaker A": "Sales Rep",
    "Speaker B": "Customer"
  }},
  "call_summary": [
    "Customer's REAL goal: Automate sales pipeline to hit Q1 targets (not generic 'increase efficiency')",
    "Deal MOVED FORWARD: Customer agreed to technical demo with VP Engineering next Tuesday",
    "Current STATUS: Warm lead (65/100) - serious but comparing 2 other vendors",
    "BIGGEST RISK: Price 20% higher than competitor + ROI justification unclear to CFO",
    "MUST HAPPEN NEXT: Send ROI calculator with 18-month payback analysis by Friday"
  ],
  "concerns": [
    {{
      "type": "pricing",
      "severity": 4,
      "detail": "DEAL KILLER if not fixed: Price is 20% above competitor. Customer must justify premium to CFO who is budget-conscious. No clear ROI shown yet. High risk of losing to cheaper option.",
      "evidence_quotes": [
        {{"text": "Your competitor is offering similar features at $8k/month", "timestamp": null}},
        {{"text": "I'll need to justify this to our CFO and honestly I'm not sure how", "timestamp": null}}
      ]
    }},
    {{
      "type": "trust",
      "severity": 3,
      "detail": "Customer skeptical about implementation success. Mentioned past vendor failure. Needs proof of similar successful deployments.",
      "evidence_quotes": [
        {{"text": "We tried something similar 2 years ago and it didn't work out", "timestamp": null}}
      ]
    }}
  ],
  "next_steps": [
    {{
      "action": "Send ROI calculator showing $450K savings over 18 months + 3 case studies from similar companies (include CFO testimonials)",
      "owner": "sales_rep",
      "suggested_due_days": 2
    }},
    {{
      "action": "Internal review: Share ROI analysis with technical team and schedule 30-min CFO briefing",
      "owner": "customer",
      "suggested_due_days": 5
    }},
    {{
      "action": "Schedule live technical demo with VP Engineering + Customer Success to address implementation concerns",
      "owner": "sales_rep",
      "suggested_due_days": 7
    }},
    {{
      "action": "Sales rep: Practice objection handling for 'why 20% premium' - prepare value differentiation points",
      "owner": "sales_rep",
      "suggested_due_days": 1
    }}
  ],
  "qualification": {{
    "budget": "discussing",
    "timeline": "Q1 2025 implementation - hard deadline due to fiscal year planning",
    "decision_maker": "VP Engineering (John Smith) recommends, but CFO (unknown name) must approve budget - TWO-PERSON sign-off",
    "need": "Automate manual sales pipeline to hit Q1 revenue targets - currently losing 30% of leads due to slow follow-up. Need 25% conversion lift.",
    "score": 68
  }},
  "confidence": 0.85
}}

=== CRITICAL REMINDERS ===
✓ Be SKEPTICAL - assume deal is at risk unless proven otherwise
✓ SEVERITY 4-5 is rare - only for true deal killers
✓ Scores 70+ mean customer is ACTIVELY comparing vendors and close to decision
✓ Scores 90+ mean contract/payment is imminent (very rare)
✓ "unknown" is better than guessing
✓ Quotes must PROVE the point, not just mention it
✓ Next steps must be SPECIFIC (not "send proposal" but "send ROI calculator with X, Y, Z")
✓ Call summary should DIAGNOSE, not narrate

Return ONLY valid JSON, no markdown, no explanations:"""
    
    async def _call_openai_llm(self, prompt: str) -> Dict[str, Any]:
        """Call OpenAI-compatible LLM API"""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{settings.llm_api_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.llm_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": settings.llm_model,
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
            
            return json.loads(content)
    
    def save_transcript(self, job_id: int, transcript_data: Dict[str, Any]) -> str:
        """Save transcript to file"""
        transcript_dir = self.storage_path / "transcripts"
        transcript_dir.mkdir(parents=True, exist_ok=True)
        
        transcript_file = transcript_dir / f"job_{job_id}.txt"
        
        with open(transcript_file, "w", encoding="utf-8") as f:
            f.write(transcript_data["text"])
        
        return f"transcripts/job_{job_id}.txt"
    
    def transcript_to_json(self, transcript_data: Dict[str, Any]) -> str:
        """Convert transcript data to JSON string"""
        return json.dumps({
            "segments": transcript_data.get("segments", [])
        })
    
    def extraction_to_json(self, extraction: Dict[str, Any]) -> str:
        """Convert extraction to JSON string"""
        return json.dumps(extraction)


