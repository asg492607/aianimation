import uuid
from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.agents.avatar_agent import AvatarAgent

router = APIRouter()

@router.post("/upload")
async def upload_avatar(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    image_bytes = await file.read()
    agent = AvatarAgent(db)
    
    # Mock user ID
    user_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
    avatar_data = await agent.create_avatar_from_upload(user_id, image_bytes)
    
    return {"message": "Avatar created successfully", "avatar": avatar_data}
