import asyncio
import subprocess
import tempfile
import os
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class TTSAdapter(ABC):
    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice_id: Optional[str] = None,
        speed: float = 1.0,
        language: str = "en",
    ) -> bytes:
        pass

    @abstractmethod
    def get_engine_name(self) -> str:
        pass


class PiperTTSAdapter(TTSAdapter):
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or "/usr/share/piper/models/en_US-lessac-medium.onnx"

    def get_engine_name(self) -> str:
        return "piper"

    async def synthesize(
        self,
        text: str,
        voice_id: Optional[str] = None,
        speed: float = 1.0,
        language: str = "en",
    ) -> bytes:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            model = voice_id or self.model_path
            cmd = [
                "piper",
                "--model", model,
                "--output_file", tmp_path,
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate(input=text.encode())

            if proc.returncode != 0:
                logger.error("piper_tts_error", stderr=stderr.decode())
                raise RuntimeError(f"Piper TTS failed: {stderr.decode()}")

            with open(tmp_path, "rb") as f:
                return f.read()
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


class CoquiTTSAdapter(TTSAdapter):
    def __init__(self, model_name: str = "tts_models/en/ljspeech/tacotron2-DDC"):
        self.model_name = model_name

    def get_engine_name(self) -> str:
        return "coqui"

    async def synthesize(
        self,
        text: str,
        voice_id: Optional[str] = None,
        speed: float = 1.0,
        language: str = "en",
    ) -> bytes:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            model = voice_id or self.model_name
            cmd = [
                "tts",
                "--text", text,
                "--model_name", model,
                "--out_path", tmp_path,
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                raise RuntimeError(f"Coqui TTS failed: {stderr.decode()}")

            with open(tmp_path, "rb") as f:
                return f.read()
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


class GenericTTSAdapter(TTSAdapter):
    """Fallback TTS using system espeak"""

    def get_engine_name(self) -> str:
        return "generic"

    async def synthesize(
        self,
        text: str,
        voice_id: Optional[str] = None,
        speed: float = 1.0,
        language: str = "en",
    ) -> bytes:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            cmd = [
                "espeak",
                "-v", language,
                "-s", str(int(150 * speed)),
                "-w", tmp_path,
                text,
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()

            if os.path.exists(tmp_path):
                with open(tmp_path, "rb") as f:
                    return f.read()
            return b""
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


class ElevenLabsAdapter(TTSAdapter):
    """
    Integrates with ElevenLabs API for Voice Cloning and high-fidelity TTS.
    """
    def __init__(self):
        self.api_key = settings.ELEVENLABS_API_KEY if hasattr(settings, 'ELEVENLABS_API_KEY') else None
        
    def get_engine_name(self) -> str:
        return "elevenlabs"

    async def synthesize(
        self,
        text: str,
        voice_id: Optional[str] = None,
        speed: float = 1.0,
        language: str = "en",
    ) -> bytes:
        if not self.api_key:
            logger.error("elevenlabs_missing_key")
            raise RuntimeError("ElevenLabs API Key is not configured.")
            
        import httpx
        # We assume voice_id is passed, else use a generic default like 'Rachel'
        vid = voice_id or "21m00Tcm4TlvDq8ikWAM" 
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{vid}"
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        data = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5
            }
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=data, headers=headers, timeout=60.0)
            resp.raise_for_status()
            return resp.content


class SubtitleGenerator:
    @staticmethod
    def generate_srt(text: str, start_time: float = 0.0, duration: float = 5.0) -> str:
        words = text.split()
        lines = []
        words_per_line = 8
        chunks = [words[i:i+words_per_line] for i in range(0, len(words), words_per_line)]

        time_per_chunk = duration / len(chunks) if chunks else duration
        current_time = start_time

        for i, chunk in enumerate(chunks):
            start = current_time
            end = current_time + time_per_chunk
            start_fmt = SubtitleGenerator._format_time(start)
            end_fmt = SubtitleGenerator._format_time(end)
            lines.append(f"{i+1}\n{start_fmt} --> {end_fmt}\n{' '.join(chunk)}\n")
            current_time = end

        return "\n".join(lines)

    @staticmethod
    def _format_time(seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


class VoiceEngine:
    def __init__(self, adapter: Optional[TTSAdapter] = None):
        self.adapter = adapter or GenericTTSAdapter()

    def use_piper(self, model_path: Optional[str] = None):
        self.adapter = PiperTTSAdapter(model_path)

    def use_coqui(self, model_name: Optional[str] = None):
        self.adapter = CoquiTTSAdapter(model_name or "tts_models/en/ljspeech/tacotron2-DDC")

    def use_elevenlabs(self):
        self.adapter = ElevenLabsAdapter()

    async def generate_voiceover(
        self,
        text: str,
        voice_id: Optional[str] = None,
        speed: float = 1.0,
        language: str = "en",
    ) -> tuple[bytes, float]:
        audio_data = await self.adapter.synthesize(text, voice_id, speed, language)
        duration = await self._get_audio_duration(audio_data)
        return audio_data, duration

    async def _get_audio_duration(self, audio_data: bytes) -> float:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name

        try:
            cmd = [
                settings.FFPROBE_PATH,
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                tmp_path,
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            import json
            data = json.loads(stdout)
            return float(data.get("format", {}).get("duration", 0.0))
        except Exception:
            return float(len(audio_data) / 32000)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
