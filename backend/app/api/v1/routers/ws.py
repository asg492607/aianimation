from typing import Dict, List, Optional
import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, project_id: str):
        await websocket.accept()
        if project_id not in self.active_connections:
            self.active_connections[project_id] = []
        self.active_connections[project_id].append(websocket)
        logger.info("websocket_connected", project_id=project_id)

    def disconnect(self, websocket: WebSocket, project_id: str):
        if project_id in self.active_connections:
            try:
                self.active_connections[project_id].remove(websocket)
            except ValueError:
                pass
            if not self.active_connections[project_id]:
                del self.active_connections[project_id]
        logger.info("websocket_disconnected", project_id=project_id)

    async def broadcast_to_project(self, project_id: str, message: dict):
        if project_id in self.active_connections:
            dead = []
            for connection in self.active_connections[project_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    dead.append(connection)
            for c in dead:
                try:
                    self.active_connections[project_id].remove(c)
                except ValueError:
                    pass


manager = ConnectionManager()

PIPELINE_STEPS = [
    "DirectorAgent", "ScriptAgent", "CharacterAgent", "SceneAgent",
    "StoryboardAgent", "CameraAgent", "AssetAgent", "VoiceAgent",
    "MusicAgent", "TimelineAgent", "RenderAgent", "ExportAgent",
]


@router.websocket("/{project_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    project_id: str,
    token: Optional[str] = Query(default=None),
):
    """
    WebSocket endpoint for real-time project progress.
    Token auth is optional for the MVP — skip verification
    so users without a login can still see the progress simulation.
    """
    import asyncio

    await manager.connect(websocket, project_id)
    try:
        # Send a simulated pipeline progress so the monitor page works
        # even without a real Celery worker running the pipeline.
        await websocket.send_json({"event": "connected", "project_id": project_id})

        for i, agent in enumerate(PIPELINE_STEPS):
            await asyncio.sleep(1.5)
            await websocket.send_json({
                "event": "progress",
                "agent": agent,
                "status": "RUNNING",
                "step": i + 1,
                "total": len(PIPELINE_STEPS),
            })
            await asyncio.sleep(0.8)
            await websocket.send_json({
                "event": "progress",
                "agent": agent,
                "status": "COMPLETED",
                "step": i + 1,
                "total": len(PIPELINE_STEPS),
            })

        await websocket.send_json({"event": "done", "message": "Pipeline complete!"})

        # Keep the connection open until the client closes it
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        manager.disconnect(websocket, project_id)
    except Exception as e:
        logger.error("websocket_error", project_id=project_id, error=str(e))
        manager.disconnect(websocket, project_id)


async def notify_project_progress(project_id: uuid.UUID, agent: str, status: str):
    """Broadcast a progress update to all connected clients for a project."""
    await manager.broadcast_to_project(
        str(project_id),
        {"event": "progress", "agent": agent, "status": status},
    )
