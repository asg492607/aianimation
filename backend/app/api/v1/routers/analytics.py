from fastapi import APIRouter
from app.db.session import get_projects

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard_metrics():
    projects = get_projects()
    total_projects = len(projects)
    return {
        "metrics": {
            "total_projects": total_projects,
            "total_videos_generated": total_projects,
            "total_render_time_minutes": total_projects * 5,
            "estimated_ai_costs": f"${total_projects * 0.05:.2f}",
            "storage_usage_gb": f"{total_projects * 0.5:.1f} GB",
        }
    }
