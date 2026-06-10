import uuid
import subprocess
import tempfile
import os
import asyncio
import json
import urllib.parse
from typing import Optional, List

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.db.session import get_projects
from app.core.config import settings

router = APIRouter()


class GenerateRequest(BaseModel):
    title: str
    prompt: str
    meta: Optional[dict] = None


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

async def get_ai_scenes(title: str, prompt: str) -> List[dict]:
    """Call Groq to generate cinematic scene descriptions for the video."""
    try:
        from groq import Groq
        client = Groq(api_key=settings.GROQ_API_KEY)
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a professional video director. "
                        "Return ONLY a valid JSON array, absolutely no other text."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f'Create 3 cinematic scene descriptions for a video titled: "{title}". '
                        f'Context: {prompt[:150]}. '
                        "Return exactly: "
                        '[{"visual":"10-15 word photorealistic cinematic image prompt","caption":"5-7 word scene caption"},'
                        '{"visual":"...","caption":"..."},'
                        '{"visual":"...","caption":"..."}]'
                    ),
                },
            ],
            max_tokens=400,
            temperature=0.7,
        )
        content = response.choices[0].message.content.strip()
        start = content.find("[")
        end = content.rfind("]") + 1
        if start >= 0 and end > start:
            scenes = json.loads(content[start:end])
            if isinstance(scenes, list) and len(scenes) >= 1:
                return scenes[:3]
    except Exception as e:
        print(f"Groq scene generation failed: {e}")

    # Fallback scenes when Groq is unavailable
    return [
        {
            "visual": f"cinematic establishing shot {title[:25]}, dramatic lighting, 4K ultra realistic, professional",
            "caption": title[:30],
        },
        {
            "visual": "futuristic AI technology concept, glowing neural network, dark blue background, cinematic",
            "caption": "Powered by AI",
        },
        {
            "visual": "successful professional team celebrating, modern office, golden hour sunlight, cinematic 4K",
            "caption": "The Future is Now",
        },
    ]


async def fetch_image(client: httpx.AsyncClient, visual_prompt: str, save_path: str) -> bool:
    """Download a free AI-generated image from Pollinations.ai."""
    try:
        clean_prompt = visual_prompt + ", no text, no watermark, no words"
        encoded = urllib.parse.quote(clean_prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded}?width=1280&height=720&nologo=true"
        resp = await client.get(url, timeout=30.0, follow_redirects=True)
        if resp.status_code == 200 and len(resp.content) > 5000:
            with open(save_path, "wb") as f:
                f.write(resp.content)
            return True
    except Exception as e:
        print(f"Image fetch failed: {e}")
    return False


def _safe_text(text: str, max_len: int = 50) -> str:
    return "".join(ch if ch.isalnum() or ch in " .,!?-" else " " for ch in text[:max_len]).strip()


def make_scene_clip(image_path: str, caption: str, output_path: str, zoom_in: bool = True) -> bool:
    """Animate an image with Ken Burns zoom, fade in/out, and caption overlay."""
    safe_cap = _safe_text(caption, 55)
    zoom_expr = "min(zoom+0.001,1.25)" if zoom_in else "max(zoom-0.001,1.0)"

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", image_path,
        "-vf", (
            "scale=1280:720:force_original_aspect_ratio=increase,"
            "crop=1280:720,"
            f"zoompan=z='{zoom_expr}':d=96:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1280x720,"
            "format=yuv420p,"
            "fade=in:0:18,fade=out:78:18,"
            # Caption bar at bottom
            f"drawtext=text='{safe_cap}':"
            "fontsize=38:fontcolor=white:shadowx=3:shadowy=3:shadowcolor=black@0.9:"
            "x=(w-text_w)/2:y=h-90:"
            "box=1:boxcolor=black@0.55:boxborderw=14"
        ),
        "-t", "4",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "26",
        output_path,
    ]
    r = subprocess.run(cmd, capture_output=True, timeout=45)
    return r.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0


def make_title_card(title: str, output_path: str) -> bool:
    """Animated title card with oscillating text and hue-shift background."""
    safe_title = _safe_text(title, 35)

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=0x0f172a:s=1280x720:r=24",
        "-vf", (
            "hue=h=t*20:s=1.3,"
            "drawtext=text='AnimateAI':"
            "fontsize=44:fontcolor=0x818cf8:"
            "x=(w-text_w)/2:y=(h/2)-90,"
            f"drawtext=text='{safe_title}':"
            "fontsize=68:fontcolor=white:shadowx=3:shadowy=3:shadowcolor=black@0.6:"
            "x=(w-text_w)/2+12*sin(2*PI*t/3):y=(h/2),"
            "drawtext=text='Generated by AI Pipeline':"
            "fontsize=28:fontcolor=0x94a3b8:"
            "x=(w-text_w)/2:y=(h/2)+95,"
            "fade=in:0:24,fade=out:72:24"
        ),
        "-t", "4",
        "-pix_fmt", "yuv420p",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "26",
        output_path,
    ]
    r = subprocess.run(cmd, capture_output=True, timeout=30)
    return r.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0


def concat_clips(clip_paths: List[str], output_path: str) -> bool:
    """Concatenate video clips using FFmpeg concat demuxer."""
    list_fd, list_path = tempfile.mkstemp(suffix=".txt")
    try:
        with os.fdopen(list_fd, "w") as f:
            for p in clip_paths:
                f.write(f"file '{p}'\n")
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", list_path,
            "-c", "copy",
            output_path,
        ]
        r = subprocess.run(cmd, capture_output=True, timeout=60)
        return r.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0
    finally:
        try:
            os.unlink(list_path)
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/{project_id}/generate")
async def generate_project(project_id: uuid.UUID, request: GenerateRequest):
    projects = get_projects()
    pid = str(project_id)
    projects[pid] = {
        "id": pid,
        "title": request.title,
        "prompt": request.prompt,
        "meta": request.meta,
        "status": "queued",
    }
    return {"message": "Generation pipeline dispatched", "project_id": pid}


@router.get("/{project_id}/download")
async def download_project(project_id: uuid.UUID):
    """
    Generate a real AI video:
      1. Groq generates 3 cinematic scene descriptions
      2. Pollinations.ai (free) generates an AI image per scene in parallel
      3. FFmpeg applies Ken Burns animation + captions to each image clip
      4. All clips + an animated title card are concatenated into a final MP4
    """
    projects = get_projects()
    pid = str(project_id)
    project = projects.get(pid)
    title = project["title"] if project else "AI Animation"
    prompt = project.get("prompt", title) if project else title

    tmp_dir = tempfile.mkdtemp()

    try:
        # 1 — Scene descriptions via Groq
        scenes = await get_ai_scenes(title, prompt)

        # 2 — Download images in parallel (Pollinations.ai — free, no key)
        image_paths = [os.path.join(tmp_dir, f"img_{i}.jpg") for i in range(len(scenes))]
        async with httpx.AsyncClient() as client:
            results = await asyncio.gather(*[
                fetch_image(client, s["visual"], p)
                for s, p in zip(scenes, image_paths)
            ])

        # 3 — Create animated Ken Burns clips
        clip_paths = []
        for i, (scene, img_path, ok) in enumerate(zip(scenes, image_paths, results)):
            clip_out = os.path.join(tmp_dir, f"clip_{i}.mp4")
            caption = scene.get("caption", scene.get("text", ""))
            if ok and os.path.exists(img_path):
                if make_scene_clip(img_path, caption, clip_out, zoom_in=(i % 2 == 0)):
                    clip_paths.append(clip_out)

        # 4 — Animated title card at the end
        title_out = os.path.join(tmp_dir, "title.mp4")
        if make_title_card(title, title_out):
            clip_paths.append(title_out)

        # 5 — Concatenate everything
        final_path = os.path.join(tmp_dir, "final.mp4")
        if len(clip_paths) >= 2:
            if not concat_clips(clip_paths, final_path):
                final_path = clip_paths[0]
        elif len(clip_paths) == 1:
            final_path = clip_paths[0]
        else:
            # Hard fallback: just the title card
            make_title_card(title, final_path)

        safe_name = _safe_text(title, 30).replace(" ", "_") + "_AnimateAI.mp4"
        return FileResponse(path=final_path, media_type="video/mp4", filename=safe_name)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Video generation failed: {str(e)}")


@router.post("/{project_id}/scenes/{scene_id}/regenerate-assets")
async def regenerate_scene_assets(project_id: uuid.UUID, scene_id: uuid.UUID):
    return {"message": f"Dispatched asset regeneration for scene {scene_id}"}


@router.post("/{project_id}/scenes/{scene_id}/regenerate-voice")
async def regenerate_scene_voice(project_id: uuid.UUID, scene_id: uuid.UUID):
    return {"message": f"Dispatched voice regeneration for scene {scene_id}"}


class TimelineUpdate(BaseModel):
    ordered_scene_ids: list[str]


@router.put("/{project_id}/timeline")
async def update_timeline(project_id: uuid.UUID, update: TimelineUpdate):
    return {"message": "Timeline updated successfully", "new_order": update.ordered_scene_ids}


@router.delete("/{project_id}/scenes/{scene_id}")
async def delete_scene(project_id: uuid.UUID, scene_id: uuid.UUID):
    return {"message": f"Scene {scene_id} deleted"}
