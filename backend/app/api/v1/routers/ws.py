from typing import Dict, List
import uuid
import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from app.core.security import verify_token
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        # project_id -> list of active connections
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, project_id: str):
        await websocket.accept()
        if project_id not in self.active_connections:
            self.active_connections[project_id] = []
        self.active_connections[project_id].append(websocket)
        logger.info("websocket_connected", project_id=project_id)

    def disconnect(self, websocket: WebSocket, project_id: str):
        if project_id in self.active_connections:
            self.active_connections[project_id].remove(websocket)
            if not self.active_connections[project_id]:
                del self.active_connections[project_id]
        logger.info("websocket_disconnected", project_id=project_id)

    async def broadcast_to_project(self, project_id: str, message: dict):
        if project_id in self.active_connections:
            for connection in self.active_connections[project_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error("websocket_send_error", project_id=project_id, error=str(e))

manager = ConnectionManager()

@router.websocket("/{project_id}")
async def websocket_endpoint(
    websocket: WebSocket, 
    project_id: str,
    token: str = Query(...)
):
    try:
        # Verify the JWT token
        user_id = verify_token(token, "access")
        # In a fully integrated flow, we would verify the user_id owns the project_id here.
    except Exception as e:
        logger.error("websocket_auth_failed", project_id=project_id, error=str(e))
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(websocket, project_id)
    try:
        while True:
            # We just keep the connection open to send unidirectional updates to client
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, project_id)

async def notify_project_progress(project_id: uuid.UUID, agent: str, status: str):
    """
    Helper function to be called by OrchestratorAgent or Celery tasks
    to broadcast progress. Since Celery runs in a separate process, 
    in a real production app this would use Redis Pub/Sub.
    For this MVP, if running synchronously or same process, it works directly.
    """
    await manager.broadcast_to_project(
        str(project_id), 
        {"event": "progress", "agent": agent, "status": status}
    )
