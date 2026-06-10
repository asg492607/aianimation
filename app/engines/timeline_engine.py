from typing import List
import uuid
from app.models.script import Scene
from app.models.advanced import Timeline
from app.core.logging import get_logger

logger = get_logger(__name__)


class TimelineEngine:
    """
    TimelineEngine builds the absolute timeline for the Render Engine based on Scenes and Assets.
    """
    
    @staticmethod
    def generate_timeline_from_scenes(project_id: uuid.UUID, scenes: List[Scene]) -> List[Timeline]:
        timeline_entries = []
        current_time = 0.0

        for scene in sorted(scenes, key=lambda s: s.scene_number):
            duration = float(scene.duration_seconds)
            end_time = current_time + duration
            
            entry = Timeline(
                project_id=project_id,
                scene_id=scene.id,
                start_time=current_time,
                end_time=end_time,
                layer=0,
                meta={
                    "scene_number": scene.scene_number,
                    "transition_in": scene.transition_in.value if scene.transition_in else "cut",
                    "transition_out": scene.transition_out.value if scene.transition_out else "cut",
                }
            )
            timeline_entries.append(entry)
            current_time = end_time

        logger.info("timeline_engine_generated", project_id=str(project_id), total_duration=current_time)
        return timeline_entries
