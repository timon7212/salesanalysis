from celery import Task
from app.celery_app import celery_app
from app.database import get_db, Job, Upload
from app.processor import CallProcessor
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name='app.tasks.process_call_task')
def process_call_task(self, job_id: int):
    """Process call recording: convert, transcribe, extract"""
    db = get_db()
    processor = CallProcessor()
    
    try:
        # Get job
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return
        
        # Get upload
        upload = db.query(Upload).filter(Upload.id == job.upload_id).first()
        if not upload:
            logger.error(f"Upload {job.upload_id} not found")
            job.status = "failed"
            job.last_error = "Upload not found"
            db.commit()
            return
        
        logger.info(f"Starting processing for job {job_id}")
        
        # Step 1: Convert to audio
        job.status = "converting"
        job.progress_step = "Converting to audio"
        db.commit()
        
        audio_path = processor.convert_to_audio(upload.storage_path, job.id)
        logger.info(f"Converted to audio: {audio_path}")
        
        # Step 2: Transcribe
        job.status = "transcribing"
        job.progress_step = "Transcribing audio"
        db.commit()
        
        transcript_data = processor.transcribe(audio_path)
        logger.info(f"Transcription complete: {len(transcript_data['text'])} chars")
        
        # Save transcript
        transcript_path = processor.save_transcript(job.id, transcript_data)
        job.transcript_path = transcript_path
        job.transcript_json = processor.transcript_to_json(transcript_data)
        db.commit()
        
        # Step 3: LLM Extraction
        job.status = "extracting"
        job.progress_step = "Extracting insights"
        db.commit()
        
        extraction = processor.extract_insights(transcript_data['text'])
        logger.info(f"Extraction complete with confidence {extraction['confidence']}")
        
        job.extraction_json = processor.extraction_to_json(extraction)
        job.confidence = extraction['confidence']
        db.commit()
        
        # Done
        job.status = "ready"
        job.progress_step = "Complete"
        job.updated_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"Job {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Job {job_id} failed: {str(e)}", exc_info=True)
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = "failed"
            job.last_error = str(e)
            job.updated_at = datetime.utcnow()
            db.commit()
    
    finally:
        db.close()








