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
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

try:
    import edge_tts
except ImportError:
    print("ERROR: edge-tts not found. Install with: pip install edge-tts")
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

class VietnameseTTS:
    """Vietnamese Text-to-Speech using Edge TTS"""

    # Max chars per chunk to avoid Edge TTS truncation (safe limit)
    MAX_CHUNK_CHARS = 2500

    def __init__(self, voice: str = DEFAULT_VOICE, rate: str = DEFAULT_RATE):
        self.voice_id = VIETNAMESE_VOICES.get(voice, voice)
        self.rate = rate
        logger.info(f"TTS initialized: voice={self.voice_id}, rate={rate}")

    @staticmethod
    def _split_into_chunks(text: str, max_chars: int = 2500) -> list:
        """Split text into chunks at sentence boundaries to avoid truncation.

        Edge TTS silently truncates text longer than ~3000 chars.
        We split at sentence boundaries (. ! ?) to keep speech natural.
        """
        if len(text) <= max_chars:
            return [text]

        chunks = []
        current = ""

        # Split by sentences (Vietnamese uses . ! ? as sentence endings)
        sentences = []
        buf = ""
        for char in text:
            buf += char
            if char in ".!?\n" and len(buf.strip()) > 0:
                sentences.append(buf)
                buf = ""
        if buf.strip():
            sentences.append(buf)

        for sentence in sentences:
            if len(current) + len(sentence) > max_chars and current.strip():
                chunks.append(current.strip())
                current = sentence
            else:
                current += sentence

        if current.strip():
            chunks.append(current.strip())

        logger.info(f"Split {len(text)} chars into {len(chunks)} chunks")
        return chunks

    async def generate(
        self,
        text: str,
        output_path: str,
        subtitle_path: Optional[str] = None,
    ) -> TTSResult:
        """Generate audio and optional subtitles from Vietnamese text.

        Automatically chunks long texts to prevent Edge TTS truncation.
        """
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        chunks = self._split_into_chunks(text, self.MAX_CHUNK_CHARS)

        if len(chunks) == 1:
            # Short text — single pass (original behavior)
            await self._generate_single(chunks[0], output, subtitle_path)
        else:
            # Long text — generate per chunk, then concatenate with ffmpeg
            chunk_files = []
            chunk_subs = []
            for i, chunk_text in enumerate(chunks):
                chunk_audio = output.parent / f"_chunk_{i:03d}.mp3"
                chunk_sub = None
                if subtitle_path:
                    chunk_sub = str(output.parent / f"_chunk_{i:03d}.srt")
                await self._generate_single(chunk_text, chunk_audio, chunk_sub)
                chunk_files.append(str(chunk_audio))
                if chunk_sub:
                    chunk_subs.append(chunk_sub)

            # Concatenate audio with ffmpeg
            await self._concat_audio(chunk_files, str(output))

            # Concatenate subtitles if needed
            if subtitle_path and chunk_subs:
                self._concat_srt_files(chunk_subs, subtitle_path)

            # Cleanup chunk files
            for f in chunk_files:
                Path(f).unlink(missing_ok=True)
            for f in chunk_subs:
                Path(f).unlink(missing_ok=True)

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

    async def _generate_single(
        self,
        text: str,
        output: Path,
        subtitle_path: Optional[str] = None,
    ):
        """Generate a single chunk of audio."""
        communicate = edge_tts.Communicate(
            text=text,
            voice=self.voice_id,
            rate=self.rate,
            volume=DEFAULT_VOLUME,
        )

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
        else:
            await communicate.save(str(output))

    async def _concat_audio(self, chunk_files: list, output_path: str):
        """Concatenate multiple audio files using ffmpeg."""
        if len(chunk_files) == 1:
            import shutil
            shutil.copy2(chunk_files[0], output_path)
            return

        # Create ffmpeg concat list
        list_file = Path(output_path).parent / "_concat_list.txt"
        with open(list_file, "w") as f:
            for chunk_path in chunk_files:
                f.write(f"file '{chunk_path}'\n")

        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(list_file), "-c", "copy", output_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        list_file.unlink(missing_ok=True)

        if proc.returncode != 0:
            logger.error(f"ffmpeg concat failed: {stderr.decode()}")
            raise RuntimeError("Failed to concatenate audio chunks")

        logger.info(f"Concatenated {len(chunk_files)} audio chunks")

    @staticmethod
    def _concat_srt_files(srt_files: list, output_path: str):
        """Concatenate SRT subtitle files, adjusting timestamps."""
        import re

        time_pattern = re.compile(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})")
        combined = []
        time_offset_ms = 0
        counter = 1

        for srt_file in srt_files:
            content = Path(srt_file).read_text(encoding="utf-8")
            blocks = content.strip().split("\n\n")
            max_end_ms = 0

            for block in blocks:
                lines = block.strip().split("\n")
                if len(lines) < 3:
                    continue

                # Parse timestamps and offset
                ts_line = lines[1]
                def offset_time(match):
                    nonlocal max_end_ms
                    h, m, s, ms = int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4))
                    total_ms = h * 3600000 + m * 60000 + s * 1000 + ms + time_offset_ms
                    if total_ms > max_end_ms:
                        max_end_ms = total_ms
                    nh = total_ms // 3600000
                    nm = (total_ms % 3600000) // 60000
                    ns = (total_ms % 60000) // 1000
                    nms = total_ms % 1000
                    return f"{nh:02d}:{nm:02d}:{ns:02d},{nms:03d}"

                new_ts = time_pattern.sub(offset_time, ts_line)
                text = "\n".join(lines[2:])
                combined.append(f"{counter}\n{new_ts}\n{text}")
                counter += 1

            time_offset_ms = max_end_ms

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n\n".join(combined) + "\n")
        logger.info(f"Combined {len(srt_files)} subtitle files")

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
