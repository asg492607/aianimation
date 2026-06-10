import asyncio
import json
import os
import tempfile
import uuid
from pathlib import Path
from typing import List, Optional, Callable

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class RenderConfig:
    def __init__(
        self,
        resolution: str = "1920x1080",
        fps: int = 30,
        format: str = "mp4",
        audio_bitrate: str = "128k",
        video_bitrate: str = "2000k",
        codec: str = "libx264",
    ):
        self.resolution = resolution
        self.fps = fps
        self.format = format
        self.audio_bitrate = audio_bitrate
        self.video_bitrate = video_bitrate
        self.codec = codec

    @property
    def width(self) -> int:
        return int(self.resolution.split("x")[0])

    @property
    def height(self) -> int:
        return int(self.resolution.split("x")[1])


class SceneFrame:
    def __init__(
        self,
        duration: float,
        background_color: str = "#000000",
        image_path: Optional[str] = None,
        audio_path: Optional[str] = None,
        text: Optional[str] = None,
        transition_in: str = "cut",
        transition_out: str = "cut",
    ):
        self.duration = duration
        self.background_color = background_color
        self.image_path = image_path
        self.audio_path = audio_path
        self.text = text
        self.transition_in = transition_in
        self.transition_out = transition_out


class FFmpegRenderEngine:
    def __init__(self, config: Optional[RenderConfig] = None):
        self.config = config or RenderConfig()
        self.ffmpeg = settings.FFMPEG_PATH

    async def render_scene_to_video(
        self,
        frame: SceneFrame,
        output_path: str,
    ) -> str:
        inputs = []
        filter_parts = []

        with tempfile.TemporaryDirectory() as tmpdir:
            if frame.image_path and os.path.exists(frame.image_path):
                inputs.extend(["-i", frame.image_path])
                filter_parts.append(
                    f"[0:v]scale={self.config.width}:{self.config.height},"
                    f"setsar=1,fps={self.config.fps}[v0]"
                )
                video_map = "[v0]"
            else:
                color = frame.background_color.lstrip("#")
                r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
                inputs.extend([
                    "-f", "lavfi",
                    "-i", f"color=c=0x{color}:size={self.config.width}x{self.config.height}:rate={self.config.fps}",
                ])
                filter_parts.append(f"[0:v]setsar=1[v0]")
                video_map = "[v0]"

            if frame.text:
                text_escaped = frame.text.replace("'", r"\'").replace(":", r"\:")
                filter_parts.append(
                    f"{video_map}drawtext=text='{text_escaped}'"
                    f":fontsize=36:fontcolor=white:x=(w-text_w)/2:y=h*0.85"
                    f":box=1:boxcolor=black@0.5:boxborderw=10[vtext]"
                )
                video_map = "[vtext]"

            cmd = [self.ffmpeg, "-y"]
            cmd.extend(inputs)
            if frame.audio_path and os.path.exists(frame.audio_path):
                cmd.extend(["-i", frame.audio_path])

            if filter_parts:
                cmd.extend(["-filter_complex", ";".join(filter_parts)])

            cmd.extend([
                "-map", video_map,
                "-t", str(frame.duration),
                "-c:v", self.config.codec,
                "-b:v", self.config.video_bitrate,
                "-r", str(self.config.fps),
                "-pix_fmt", "yuv420p",
            ])

            if frame.audio_path and os.path.exists(frame.audio_path):
                cmd.extend([
                    "-map", "1:a",
                    "-c:a", "aac",
                    "-b:a", self.config.audio_bitrate,
                    "-shortest",
                ])

            cmd.append(output_path)

            await self._run_ffmpeg(cmd)
            return output_path

    async def concatenate_videos(
        self,
        video_paths: List[str],
        output_path: str,
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> str:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            concat_file = f.name
            for path in video_paths:
                f.write(f"file '{path}'\n")

        try:
            cmd = [
                self.ffmpeg, "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file,
                "-c", "copy",
                output_path,
            ]
            await self._run_ffmpeg(cmd)
            if progress_callback:
                progress_callback(100)
            return output_path
        finally:
            if os.path.exists(concat_file):
                os.unlink(concat_file)

    async def create_color_frame(
        self,
        color: str,
        duration: float,
        output_path: str,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> str:
        w = width or self.config.width
        h = height or self.config.height
        hex_color = color.lstrip("#")

        cmd = [
            self.ffmpeg, "-y",
            "-f", "lavfi",
            "-i", f"color=c=0x{hex_color}:size={w}x{h}:rate={self.config.fps}",
            "-t", str(duration),
            "-c:v", self.config.codec,
            "-pix_fmt", "yuv420p",
            output_path,
        ]
        await self._run_ffmpeg(cmd)
        return output_path

    async def get_video_info(self, video_path: str) -> dict:
        cmd = [
            settings.FFPROBE_PATH,
            "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            "-show_format",
            video_path,
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        return json.loads(stdout)

    async def _run_ffmpeg(self, cmd: List[str]) -> None:
        logger.debug("ffmpeg_command", cmd=" ".join(cmd))
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            logger.error("ffmpeg_error", stderr=stderr.decode()[-2000:])
            raise RuntimeError(f"FFmpeg failed with code {proc.returncode}: {stderr.decode()[-1000:]}")
        logger.debug("ffmpeg_success")
