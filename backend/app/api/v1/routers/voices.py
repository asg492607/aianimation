from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
import uuid

router = APIRouter()

@router.post("/clone")
async def clone_voice(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    # MVP: In a real environment, we'd send the wav/mp3 file to ElevenLabs API
    # POST https://api.elevenlabs.io/v1/voices/add
    # We would receive a voice_id back.
    
    # We will simulate a successful clone and return a mock custom Voice ID
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty file provided")
        
    custom_voice_id = f"cloned_{uuid.uuid4().hex[:8]}"
    
    return {
        "message": "Voice cloned successfully",
        "voice_id": custom_voice_id,
        "name": file.filename
    }
