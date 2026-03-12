#!/usr/bin/env python3
"""
Video Composer for AI Thực Chiến

Composes final YouTube video from components:
- Talking head avatar video
- Intro/outro bumpers
- Text overlays (title, key points)
- Subtitles (SRT → burned in)
- Background music (optional)

Uses FFmpeg for all compositing — no external dependencies needed.

Usage:
    python3 video_composer.py --avatar talking.mp4 --subtitles subs.srt --output final.mp4
    python3 video_composer.py --avatar talking.mp4 --title "AI News Hôm Nay" --output final.mp4
"""

import json
import logging
import argparse
import subprocess
import sys
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ============================================================================
# Configuration
# ============================================================================

# Brand colors
BRAND_PRIMARY = "#00D4AA"  # Teal
BRAND_DARK = "#0A0A0A"  # Near black
BRAND_ACCENT = "#FF6B35"  # Orange

# Video specs
OUTPUT_WIDTH = 1920
OUTPUT_HEIGHT = 1080
OUTPUT_FPS = 30
OUTPUT_BITRATE = "4M"

# Subtitle styling
SUB_FONT_SIZE = 24
SUB_FONT_COLOR = "white"
SUB_OUTLINE_COLOR = "black"
SUB_OUTLINE_WIDTH = 2
SUB_MARGIN_V = 60

# Assets directory
ASSETS_DIR = Path(__file__).parent.parent / "assets"


@dataclass
class ComposerResult:
    """Result of video composition"""
    output_path: str
    duration_seconds: float
    file_size_mb: float


# ============================================================================
# FFmpeg Helpers
# ============================================================================

def run_ffmpeg(args: List[str], description: str = "") -> subprocess.CompletedProcess:
    """Run ffmpeg command with error handling."""
    cmd = ["ffmpeg", "-y"] + args
    logger.info(f"FFmpeg: {description or ' '.join(cmd[:6])}...")

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"FFmpeg error: {result.stderr[-500:]}")
        raise RuntimeError(f"FFmpeg failed: {result.stderr[-200:]}")
    return result


def get_video_info(video_path: str) -> dict:
    """Get video metadata via ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(result.stdout)


def get_duration(file_path: str) -> float:
    """Get media file duration in seconds."""
    info = get_video_info(file_path)
    return float(info["format"]["duration"])


# ============================================================================
# Video Composition
# ============================================================================

class VideoComposer:
    """Composes final video from components using FFmpeg."""

    def __init__(self, assets_dir: Optional[str] = None):
        self.assets_dir = Path(assets_dir) if assets_dir else ASSETS_DIR
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"VideoComposer initialized, assets: {self.assets_dir}")

    def compose(
        self,
        avatar_video: str,
        output_path: str,
        subtitles: Optional[str] = None,
        title_text: Optional[str] = None,
        background_music: Optional[str] = None,
        music_volume: float = 0.08,
        intro_seconds: float = 2.0,
        outro_seconds: float = 3.0,
    ) -> ComposerResult:
        """Compose final video from avatar + audio.

        Uses only basic FFmpeg filters (no drawtext/subtitles — requires ffmpeg-full).
        Subtitles are embedded as a soft subtitle track instead of burned in.
        """
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        # Scale avatar to output resolution with padding
        vf = (
            f"scale={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:force_original_aspect_ratio=decrease,"
            f"pad={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:(ow-iw)/2:(oh-ih)/2:color={BRAND_DARK[1:]},"
            f"fps={OUTPUT_FPS}"
        )

        args = ["-i", avatar_video]

        # Add subtitles as soft track if available
        if subtitles and Path(subtitles).exists():
            args += ["-i", subtitles]

        args += [
            "-vf", vf,
            "-c:v", "libx264", "-preset", "medium", "-b:v", OUTPUT_BITRATE,
            "-c:a", "aac", "-b:a", "128k",
        ]

        if subtitles and Path(subtitles).exists():
            args += [
                "-c:s", "mov_text",
                "-metadata:s:s:0", "language=vie",
            ]

        args += ["-movflags", "+faststart", str(output)]

        run_ffmpeg(args, f"Composing final video: {output.name}")

        # Get output info
        duration = get_duration(str(output))
        file_size_mb = output.stat().st_size / (1024 * 1024)

        logger.info(f"Final video: {output} ({duration:.1f}s, {file_size_mb:.1f}MB)")

        return ComposerResult(
            output_path=str(output),
            duration_seconds=duration,
            file_size_mb=file_size_mb,
        )

    def create_intro_bumper(
        self,
        output_path: str,
        duration: float = 3.0,
        text: str = "AI Thuc Chien",
    ) -> str:
        """Create a simple intro bumper with brand colors."""
        args = [
            "-f", "lavfi",
            "-i", f"color=c=0x0A0A0A:s={OUTPUT_WIDTH}x{OUTPUT_HEIGHT}:d={duration}:r={OUTPUT_FPS}",
            "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo",
            "-t", str(duration),
            "-vf", (
                f"drawtext=text='{text}':"
                f"fontsize=72:fontcolor={BRAND_PRIMARY[1:]}:"
                f"borderw=0:x=(w-text_w)/2:y=(h-text_h)/2:"
                f"alpha='if(lt(t,1),t,if(gt(t,{duration-1}),max(0,{duration}-t),1))'"
            ),
            "-c:v", "libx264", "-c:a", "aac",
            "-shortest",
            output_path,
        ]
        run_ffmpeg(args, "Creating intro bumper")
        return output_path

    def create_outro_bumper(
        self,
        output_path: str,
        duration: float = 4.0,
    ) -> str:
        """Create subscribe/follow outro bumper."""
        args = [
            "-f", "lavfi",
            "-i", f"color=c=0x0A0A0A:s={OUTPUT_WIDTH}x{OUTPUT_HEIGHT}:d={duration}:r={OUTPUT_FPS}",
            "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo",
            "-t", str(duration),
            "-vf", (
                f"drawtext=text='SUBSCRIBE \\& BAM CHUONG':"
                f"fontsize=56:fontcolor={BRAND_PRIMARY[1:]}:"
                f"x=(w-text_w)/2:y=(h-text_h)/2-40:"
                f"alpha='if(lt(t,0.5),t*2,1)',"
                f"drawtext=text='AI Thuc Chien':"
                f"fontsize=36:fontcolor=white:"
                f"x=(w-text_w)/2:y=(h-text_h)/2+40:"
                f"alpha='if(lt(t,1),0,if(lt(t,1.5),(t-1)*2,1))'"
            ),
            "-c:v", "libx264", "-c:a", "aac",
            "-shortest",
            output_path,
        ]
        run_ffmpeg(args, "Creating outro bumper")
        return output_path


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Video composer for AI Thực Chiến")
    parser.add_argument("--avatar", "-a", required=True, help="Talking head avatar video")
    parser.add_argument("--output", "-o", required=True, help="Output video path")
    parser.add_argument("--subtitles", "-s", help="SRT subtitle file")
    parser.add_argument("--title", "-t", help="Title text overlay")
    parser.add_argument("--music", help="Background music file")
    parser.add_argument("--music-volume", type=float, default=0.08,
                        help="Background music volume 0.0-1.0 (default: 0.08)")
    parser.add_argument("--create-intro", help="Create intro bumper at path")
    parser.add_argument("--create-outro", help="Create outro bumper at path")

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    composer = VideoComposer()

    if args.create_intro:
        composer.create_intro_bumper(args.create_intro)
        print(f"Intro: {args.create_intro}")
        return

    if args.create_outro:
        composer.create_outro_bumper(args.create_outro)
        print(f"Outro: {args.create_outro}")
        return

    result = composer.compose(
        avatar_video=args.avatar,
        output_path=args.output,
        subtitles=args.subtitles,
        title_text=args.title,
        background_music=args.music,
        music_volume=args.music_volume,
    )

    print(f"Output: {result.output_path}")
    print(f"Duration: {result.duration_seconds:.1f}s")
    print(f"Size: {result.file_size_mb:.1f}MB")


if __name__ == "__main__":
    main()
