import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException

router = APIRouter()


@router.post("/upload")
async def upload_avatar(file: UploadFile = File(...)):
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty file provided")

    avatar_id = str(uuid.uuid4())
    return {
        "message": "Avatar created successfully",
        "avatar": {
            "id": avatar_id,
            "filename": file.filename,
            "size_bytes": len(image_bytes),
        },
    }
