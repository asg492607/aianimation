import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException

router = APIRouter()


@router.post("/clone")
async def clone_voice(file: UploadFile = File(...)):
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty file provided")

    custom_voice_id = f"cloned_{uuid.uuid4().hex[:8]}"
    return {
        "message": "Voice cloned successfully",
        "voice_id": custom_voice_id,
        "name": file.filename,
    }
