from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_templates():
    return [
        {
            "id": "1",
            "name": "Legal Explainer",
            "category": "explainer",
            "description": "Professional 3D animation explaining a legal concept clearly.",
            "prompt_template": "Create a 60 second animation explaining {topic} to a layman...",
            "thumbnail_url": "https://picsum.photos/400/225",
        },
        {
            "id": "2",
            "name": "Startup Pitch",
            "category": "marketing",
            "description": "Energetic, fast-paced pitch deck replacement.",
            "prompt_template": "Create a dynamic 30 second startup pitch for {product_name}...",
            "thumbnail_url": "https://picsum.photos/400/226",
        },
        {
            "id": "3",
            "name": "Medical Education",
            "category": "educational",
            "description": "Clean, highly detailed anatomical or medical process explainer.",
            "prompt_template": "Create an educational animation about {medical_topic}...",
            "thumbnail_url": "https://picsum.photos/400/227",
        },
    ]
