#!/usr/bin/env python3
"""
TTS Generator for AI Thực Chiến

Generates Vietnamese speech audio from text using Edge TTS (free).
Supports multiple voices, speed control, and subtitle generation.

Usage:
    python3 tts_generator.py --text "Xin chào các bạn" --output output.mp3
    python3 tts_generator.py --file script.txt --output output.mp3 --voice male
    python3 tts_generator.py --file script.txt --output output.mp3 --subtitles subs.srt
"""

import asyncio
import argparse
import json
import logging
import sys
import os
import base64
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

try:
    import edge_tts
except ImportError:
    print("WARNING: edge-tts not found. Install with: pip install edge-tts for fallback TTS")

try:
    from openai import OpenAI
except ImportError:
    print("ERROR: openai not found. Install with: pip install openai")
    sys.exit(1)


# ============================================================================
# Configuration
# ============================================================================

VIETNAMESE_VOICES = {
    "male": "vi-VN-NamMinhNeural",
    "female": "vi-VN-HoaiMyNeural",
}

DEFAULT_VOICE = "male"
DEFAULT_RATE = "+0%"
DEFAULT_VOLUME = "+0%"

logger = logging.getLogger(__name__)


@dataclass
class TTSResult:
    """Result of TTS generation"""
    audio_path: str
    subtitle_path: Optional[str]
    duration_seconds: float
    voice_id: str
    text_length: int


# ============================================================================
# TTS Generation
# ============================================================================

class PoeElevenLabsTTS:
    """Vietnamese Text-to-Speech using Poe API (ElevenLabs v3)"""

    def __init__(self, voice: str = "female"):
        self.api_key = os.getenv("POE_API_KEY")
        self.base_url = os.getenv("POE_BASE_URL", "https://api.poe.com/v1")

        if not self.api_key:
            raise ValueError("POE_API_KEY not set in environment")

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        self.model = "ElevenLabs-v3"
        self.voice = voice  # "female" or "male" — ElevenLabs has Vietnamese voices
        logger.info(f"PoeElevenLabsTTS initialized: voice={voice}")

    async def generate(
        self,
        text: str,
        output_path: str,
        subtitle_path: Optional[str] = None,
    ) -> "TTSResult":
        """Generate audio from Vietnamese text using Poe's ElevenLabs API."""
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Generating TTS audio via Poe ElevenLabs: {len(text)} chars")

        try:
            response = self.client.audio.speech.create(
                model=self.model,
                voice=self.voice,
                input=text,
            )

            # Write audio to file
            with open(output, "wb") as f:
                f.write(response.content)

            # Get duration
            duration = await self._get_duration(str(output))
            logger.info(f"Audio saved: {output} ({duration:.1f}s)")

            return TTSResult(
                audio_path=str(output),
                subtitle_path=subtitle_path,
                duration_seconds=duration,
                voice_id=self.voice,
                text_length=len(text),
            )
        except Exception as e:
            logger.error(f"Poe TTS failed: {e}")
            raise

    async def _get_duration(self, audio_path: str) -> float:
        """Get audio duration using ffprobe."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "ffprobe", "-v", "quiet", "-show_entries",
                "format=duration", "-of", "json", audio_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            data = json.loads(stdout)
            return float(data["format"]["duration"])
        except (KeyError, json.JSONDecodeError, FileNotFoundError):
            logger.warning("ffprobe failed, estimating duration from file size")
            # Rough estimate for MP3: ~128kbps = 16KB/s
            file_size = Path(audio_path).stat().st_size
            return file_size / 16000

    def generate_sync(
        self,
        text: str,
        output_path: str,
        subtitle_path: Optional[str] = None,
    ) -> "TTSResult":
        """Synchronous wrapper for generate()."""
        return asyncio.run(self.generate(text, output_path, subtitle_path))


class VietnameseTTS:
    """Vietnamese Text-to-Speech using Edge TTS (fallback)"""

    def __init__(self, voice: str = DEFAULT_VOICE, rate: str = DEFAULT_RATE):
        self.voice_id = VIETNAMESE_VOICES.get(voice, voice)
        self.rate = rate
        logger.info(f"TTS initialized: voice={self.voice_id}, rate={rate}")

    async def generate(
        self,
        text: str,
        output_path: str,
        subtitle_path: Optional[str] = None,
    ) -> TTSResult:
        """Generate audio and optional subtitles from Vietnamese text."""
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        communicate = edge_tts.Communicate(
            text=text,
            voice=self.voice_id,
            rate=self.rate,
            volume=DEFAULT_VOLUME,
        )

        # Generate with subtitles if requested
        if subtitle_path:
            sub_path = Path(subtitle_path)
            sub_path.parent.mkdir(parents=True, exist_ok=True)
            sub_maker = edge_tts.SubMaker()

            with open(output, "wb") as audio_file:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_file.write(chunk["data"])
                    elif chunk["type"] == "WordBoundary":
                        sub_maker.feed(chunk)

            srt_content = sub_maker.generate_subs()
            with open(sub_path, "w", encoding="utf-8") as f:
                f.write(srt_content)

            logger.info(f"Subtitles saved: {sub_path}")
        else:
            await communicate.save(str(output))

        # Get audio duration via ffprobe
        duration = await self._get_duration(str(output))

        logger.info(f"Audio saved: {output} ({duration:.1f}s)")

        return TTSResult(
            audio_path=str(output),
            subtitle_path=subtitle_path,
            duration_seconds=duration,
            voice_id=self.voice_id,
            text_length=len(text),
        )

    async def _get_duration(self, audio_path: str) -> float:
        """Get audio duration using ffprobe."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "ffprobe", "-v", "quiet", "-show_entries",
                "format=duration", "-of", "json", audio_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            data = json.loads(stdout)
            return float(data["format"]["duration"])
        except (KeyError, json.JSONDecodeError, FileNotFoundError):
            logger.warning("ffprobe failed, estimating duration from text length")
            # Rough estimate: ~3.5 chars/second for Vietnamese
            return len(open(audio_path, "rb").read()) / 16000  # rough fallback

    def generate_sync(
        self,
        text: str,
        output_path: str,
        subtitle_path: Optional[str] = None,
    ) -> TTSResult:
        """Synchronous wrapper for generate()."""
        return asyncio.run(self.generate(text, output_path, subtitle_path))


# ============================================================================
# Script Text Processing
# ============================================================================

def get_tts_engine() -> VietnameseTTS:
    """Factory function to get the best available TTS engine.

    Uses Poe ElevenLabs if POE_API_KEY is set, otherwise falls back to Edge TTS.
    """
    poe_key = os.getenv("POE_API_KEY")
    if poe_key:
        logger.info("Using Poe ElevenLabs TTS")
        return PoeElevenLabsTTS(voice="female")
    else:
        logger.info("Using Edge TTS (fallback)")
        return VietnameseTTS(voice="male")


def clean_script_for_tts(script_text: str) -> str:
    """Clean video script text for TTS — remove visual tags, timestamps, etc."""
    lines = []
    skip_prefixes = ("[VISUAL]", "[TEXT OVERLAY]", "[B-ROLL]", "[MUSIC]", "---")

    for line in script_text.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if any(stripped.startswith(prefix) for prefix in skip_prefixes):
            continue
        # Remove timestamp markers like [0-3s]
        if stripped.startswith("[") and "s]" in stripped[:10]:
            # Keep content after the timestamp
            parts = stripped.split("]", 1)
            if len(parts) > 1:
                stripped = parts[1].strip()
        # Remove section labels like "HOOK:", "BODY:", "CTA:"
        for label in ("HOOK:", "BODY:", "CTA:", "INTRO:", "OUTRO:"):
            if stripped.upper().startswith(label):
                stripped = stripped[len(label):].strip()
        if stripped:
            lines.append(stripped)

    return " ".join(lines)


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Vietnamese TTS for AI Thực Chiến")
    parser.add_argument("--text", help="Text to speak")
    parser.add_argument("--file", help="Text file to read")
    parser.add_argument("--output", "-o", required=True, help="Output audio file path")
    parser.add_argument("--voice", choices=["male", "female"], default="male",
                        help="Voice gender (default: male)")
    parser.add_argument("--rate", default="+0%",
                        help="Speech rate adjustment (e.g., '+10%%', '-5%%')")
    parser.add_argument("--subtitles", help="Output SRT subtitle file path")
    parser.add_argument("--clean", action="store_true",
                        help="Clean script tags before TTS")

    args = parser.parse_args()

    if not args.text and not args.file:
        parser.error("Either --text or --file is required")

    text = args.text
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            text = f.read()

    if args.clean:
        text = clean_script_for_tts(text)

    tts = VietnameseTTS(voice=args.voice, rate=args.rate)
    result = tts.generate_sync(text, args.output, args.subtitles)

    print(f"Audio: {result.audio_path}")
    print(f"Duration: {result.duration_seconds:.1f}s")
    print(f"Voice: {result.voice_id}")
    if result.subtitle_path:
        print(f"Subtitles: {result.subtitle_path}")


if __name__ == "__main__":
    main()
