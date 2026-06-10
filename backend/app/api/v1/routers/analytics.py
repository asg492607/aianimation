from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.session import get_db
from app.models.project import Project
from app.models.advanced import AIJob

router = APIRouter()

@router.get("/dashboard")
async def get_dashboard_metrics(db: AsyncSession = Depends(get_db)):
    # Total Projects
    stmt_projects = select(func.count(Project.id))
    result_projects = await db.execute(stmt_projects)
    total_projects = result_projects.scalar() or 0
    
    # Total AI Jobs (proxy for operations)
    stmt_ai_jobs = select(func.count(AIJob.id))
    result_ai_jobs = await db.execute(stmt_ai_jobs)
    total_ai_jobs = result_ai_jobs.scalar() or 0
    
    # Render time (we'd sum render job durations ideally, returning mock for MVP UI)
    total_render_time_mins = total_projects * 5 
    
    # AI Costs (Mock logic: groq tokens * price)
    estimated_cost = total_ai_jobs * 0.05
    
    return {
        "metrics": {
            "total_projects": total_projects,
            "total_videos_generated": total_projects, # Assuming 1:1 for MVP
            "total_render_time_minutes": total_render_time_mins,
            "estimated_ai_costs": f"${estimated_cost:.2f}",
            "storage_usage_gb": f"{(total_projects * 0.5):.1f} GB"
        }
    }
