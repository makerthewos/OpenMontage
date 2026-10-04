"""Edge TTS — free high-quality online neural voices.

Microsoft's Edge read-aloud endpoint exposes the same neural voice family used by
Azure Speech, without an API key or an Azure subscription. For Chinese narration
this is a large quality jump over Piper: natural prosody, per-sentence pacing,
and selectable voices, at zero cost.

Tradeoff: it calls a network service, so it is not offline like Piper. Keep Piper
as the offline fallback.
"""

from __future__ import annotations

import asyncio
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from tools.base_tool import (
    BaseTool,
    Determinism,
    ExecutionMode,
    ResourceProfile,
    RetryPolicy,
    ToolResult,
    ToolRuntime,
    ToolStability,
    ToolStatus,
    ToolTier,
)

# Voices that read narration well. Xiaoxiao is warm and even; Yunxi is livelier;
# Yunyang is the most neutral "documentary" read.
RECOMMENDED_VOICES = {
    "zh-CN-XiaoxiaoNeural": "Warm female — general narration",
    "zh-CN-XiaoyiNeural": "Lively female — casual explainers",
    "zh-CN-YunxiNeural": "Lively male — friendly explainers",
    "zh-CN-YunyangNeural": "Neutral male — documentary / news",
    "zh-CN-YunjianNeural": "Passionate male — sports, promos",
}


class EdgeTTS(BaseTool):
    name = "edge_tts"
    version = "0.1.0"
    tier = ToolTier.VOICE
    capability = "tts"
    provider = "edge"
    stability = ToolStability.BETA
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.DETERMINISTIC
    runtime = ToolRuntime.API

    dependencies = ["python:edge_tts", "cmd:ffmpeg"]
    install_instructions = (
        "Install the client:\n"
        "  pip install edge-tts\n"
        "No API key is required. FFmpeg is used to convert the returned MP3 to WAV.\n"
        "Useful Chinese voices: "
        + ", ".join(RECOMMENDED_VOICES)
    )
    agent_skills = ["text-to-speech"]

    capabilities = ["text_to_speech", "multilingual"]
    supports = {
        "voice_cloning": False,
        "multilingual": True,
        "offline": False,
        "native_audio": True,
    }
    best_for = [
        "high-quality narration with no API key and no cost",
        "Chinese/Mandarin explainers where Piper sounds mechanical",
        "long-form narration with natural per-sentence pacing",
    ]
    not_good_for = [
        "fully offline pipelines",
        "voice cloning or brand-specific voice matching",
    ]

    input_schema = {
        "type": "object",
        "required": ["text"],
        "properties": {
            "text": {"type": "string"},
            "voice_id": {
                "type": "string",
                "default": "zh-CN-XiaoxiaoNeural",
                "description": "Edge neural voice name. See RECOMMENDED_VOICES.",
            },
            "rate": {
                "type": "string",
                "default": "+0%",
                "description": "Speaking-rate delta, e.g. '-10%' or '+15%'.",
            },
            "volume": {"type": "string", "default": "+0%"},
            "pitch": {"type": "string", "default": "+0Hz"},
            "output_path": {"type": "string"},
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=1, ram_mb=256, vram_mb=0, disk_mb=50, network_required=True
    )
    retry_policy = RetryPolicy(max_retries=2, retryable_errors=["Connection", "Timeout"])
    idempotency_key_fields = ["text", "voice_id", "rate", "pitch"]
    side_effects = ["writes audio file to output_path"]
    user_visible_verification = ["Listen to the narration for natural prosody"]

    def get_status(self) -> ToolStatus:
        try:
            import edge_tts  # noqa: F401
        except ImportError:
            return ToolStatus.UNAVAILABLE
        if not shutil.which("ffmpeg"):
            return ToolStatus.UNAVAILABLE
        return ToolStatus.AVAILABLE

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        return 0.0

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        if self.get_status() != ToolStatus.AVAILABLE:
            return ToolResult(
                success=False, error="Edge TTS not available. " + self.install_instructions
            )

        start = time.time()
        try:
            result = self._generate(inputs)
        except Exception as exc:
            return ToolResult(success=False, error=f"Edge TTS generation failed: {exc}")
        result.duration_seconds = round(time.time() - start, 2)
        return result

    def _generate(self, inputs: dict[str, Any]) -> ToolResult:
        import edge_tts

        text = inputs["text"]
        voice = inputs.get("voice_id") or "zh-CN-XiaoxiaoNeural"
        output_path = Path(inputs.get("output_path", "edge_tts_output.wav"))
        output_path.parent.mkdir(parents=True, exist_ok=True)

        mp3_path = output_path.with_suffix(".mp3")

        async def synth() -> None:
            communicate = edge_tts.Communicate(
                text,
                voice,
                rate=inputs.get("rate", "+0%"),
                volume=inputs.get("volume", "+0%"),
                pitch=inputs.get("pitch", "+0Hz"),
            )
            await communicate.save(str(mp3_path))

        asyncio.run(synth())

        if not mp3_path.exists() or mp3_path.stat().st_size == 0:
            return ToolResult(success=False, error="Edge TTS returned no audio")

        # WAV keeps the rest of the pipeline simple (Remotion mix, ffprobe).
        convert = subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-i", str(mp3_path),
             "-ar", "24000", "-ac", "1", str(output_path)],
            capture_output=True, text=True,
        )
        if convert.returncode != 0 or not output_path.exists():
            return ToolResult(
                success=False,
                error=f"ffmpeg conversion failed: {convert.stderr.strip()[:200]}",
            )
        mp3_path.unlink(missing_ok=True)

        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(output_path)],
            capture_output=True, text=True,
        )
        try:
            seconds = round(float(probe.stdout.strip()), 3)
        except (TypeError, ValueError):
            seconds = 0.0

        return ToolResult(
            success=True,
            data={
                "provider": self.provider,
                "voice_id": voice,
                "rate": inputs.get("rate", "+0%"),
                "text_length": len(text),
                "duration_seconds": seconds,
                "characters_per_second": round(len(text) / seconds, 2) if seconds else None,
                "output": str(output_path),
                "format": "wav",
                "cost_usd": 0.0,
            },
            artifacts=[str(output_path)],
            model=voice,
        )
