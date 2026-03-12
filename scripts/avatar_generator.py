#!/usr/bin/env python3
"""
Avatar Video Generator for AI Thực Chiến

Generates talking-head avatar videos from a reference image + audio.
Uses Replicate API (SadTalker model) — ~$0.05/video, no GPU needed locally.

Usage:
    python3 avatar_generator.py --audio speech.mp3 --image avatar.png --output talking.mp4
    python3 avatar_generator.py --audio speech.mp3 --image avatar.png --output talking.mp4 --enhancer gfpgan
"""

import os
import sys
import time
import json
import logging
import argparse
import requests
import base64
import subprocess
import asyncio
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

try:
    from openai import OpenAI
except ImportError:
    print("ERROR: openai not found. Install with: pip install openai")
    sys.exit(1)

replicate = None  # Lazy import — only needed for SadTalker fallback


# ============================================================================
# Configuration
# ============================================================================

# SadTalker model on Replicate — best for still image → talking head
SADTALKER_MODEL = "cjwbw/sadtalker:a519cc0cfebaaeade068b23899165a11ec76aaa1e0c398a33d7d3a0c4e08e1f5"

# Alternative models (can swap in)
MODELS = {
    "sadtalker": SADTALKER_MODEL,
}

DEFAULT_MODEL = "sadtalker"

logger = logging.getLogger(__name__)


@dataclass
class AvatarResult:
    """Result of avatar video generation"""
    video_path: str
    model_used: str
    generation_time_seconds: float
    cost_estimate: float


@dataclass
class AudioChunk:
    """A chunk of audio for avatar generation"""
    path: str
    duration_seconds: float
    index: int


# ============================================================================
# Audio Chunking (for OmniHuman 30s limit)
# ============================================================================

class AudioChunker:
    """Splits audio into ≤30s chunks for OmniHuman."""

    @staticmethod
    async def get_duration(audio_path: str) -> float:
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
        except Exception as e:
            logger.error(f"ffprobe failed: {e}")
            raise

    @staticmethod
    def chunk_audio(
        audio_path: str,
        output_dir: str,
        chunk_duration: int = 30,
    ) -> List[AudioChunk]:
        """Split audio file into ≤chunk_duration second chunks using ffmpeg."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            "ffmpeg", "-i", audio_path,
            "-f", "segment",
            "-segment_time", str(chunk_duration),
            "-c", "copy",
            str(output_dir / "chunk_%03d.mp3"),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg chunk failed: {result.stderr}")

        # Collect all chunks
        chunks = []
        for i, chunk_file in enumerate(sorted(output_dir.glob("chunk_*.mp3"))):
            # Get duration of each chunk
            proc = subprocess.run(
                [
                    "ffprobe", "-v", "quiet", "-show_entries",
                    "format=duration", "-of", "json", str(chunk_file),
                ],
                capture_output=True,
                text=True,
            )
            duration = float(json.loads(proc.stdout)["format"]["duration"])
            chunks.append(AudioChunk(path=str(chunk_file), duration_seconds=duration, index=i))

        logger.info(f"Audio chunked into {len(chunks)} chunks (≤{chunk_duration}s each)")
        return chunks


# ============================================================================
# Avatar Generation
# ============================================================================

class PoeOmniHumanGenerator:
    """Generates talking-head avatar videos using Poe API (OmniHuman)"""

    def __init__(self):
        self.api_key = os.getenv("POE_API_KEY")
        self.base_url = os.getenv("POE_BASE_URL", "https://api.poe.com/v1")

        if not self.api_key:
            raise ValueError("POE_API_KEY not set in environment")

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        self.model = "OmniHuman"
        self.max_audio_duration = 30  # OmniHuman supports up to 30s
        logger.info(f"PoeOmniHumanGenerator initialized")

    def _image_to_base64(self, image_path: str) -> str:
        """Convert image file to base64 string."""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _audio_to_base64(self, audio_path: str) -> str:
        """Convert audio file to base64 string."""
        with open(audio_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _generate_single_chunk(
        self,
        image_path: str,
        audio_path: str,
        output_path: str,
    ) -> str:
        """Generate avatar video for a single audio chunk."""
        logger.info(f"Generating OmniHuman video: image={image_path}, audio={audio_path}")

        image_b64 = self._image_to_base64(image_path)
        audio_b64 = self._audio_to_base64(audio_path)

        try:
            response = self.client.images.generate(
                model=self.model,
                prompt=f"face_image:data:image/png;base64,{image_b64}",
                style="professional",
                duration=30,  # Max duration
            )

            # Save the response
            with open(output_path, "wb") as f:
                f.write(response.content)

            logger.info(f"Avatar chunk saved: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"OmniHuman generation failed: {e}")
            raise

    def _concat_videos(self, video_paths: List[str], output_path: str) -> str:
        """Concatenate multiple video chunks into one using FFmpeg."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Create concat file for ffmpeg
        concat_file = output_path.parent / "concat.txt"
        with open(concat_file, "w") as f:
            for vpath in video_paths:
                f.write(f"file '{vpath}'\n")

        cmd = [
            "ffmpeg", "-f", "concat", "-safe", "0",
            "-i", str(concat_file),
            "-c", "copy", str(output_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg concat failed: {result.stderr}")

        concat_file.unlink()  # Clean up concat file
        logger.info(f"Videos concatenated: {output_path}")
        return str(output_path)

    def generate(
        self,
        audio_path: str,
        image_path: str,
        output_path: str,
    ) -> AvatarResult:
        """Generate talking-head video from image + audio.

        Handles audio >30s by splitting into chunks, generating per chunk, and concatenating.
        """
        audio_file = Path(audio_path)
        image_file = Path(image_path)

        if not audio_file.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        if not image_file.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Generating OmniHuman avatar: {image_path} + {audio_path}")
        start_time = time.time()

        # Get audio duration
        duration = asyncio.run(AudioChunker.get_duration(str(audio_file)))
        logger.info(f"Audio duration: {duration:.1f}s")

        # If audio is within limit, generate directly
        if duration <= self.max_audio_duration:
            self._generate_single_chunk(str(image_file), str(audio_file), str(output))
        else:
            # Chunk audio, generate per chunk, concatenate
            chunk_dir = output.parent / "chunks"
            chunks = AudioChunker.chunk_audio(str(audio_file), str(chunk_dir))
            logger.info(f"Generating {len(chunks)} avatar chunks...")

            video_chunks = []
            for chunk in chunks:
                chunk_output = chunk_dir / f"avatar_chunk_{chunk.index:03d}.mp4"
                self._generate_single_chunk(str(image_file), chunk.path, str(chunk_output))
                video_chunks.append(str(chunk_output))

            # Concatenate all chunks
            self._concat_videos(video_chunks, str(output))

        elapsed = time.time() - start_time
        # OmniHuman on Poe — estimate cost (check Poe pricing)
        cost = 0.10 * (duration / 30)  # Rough estimate: ~$0.10 per 30s

        logger.info(f"Avatar video saved: {output} ({elapsed:.1f}s, ~${cost:.2f})")

        return AvatarResult(
            video_path=str(output),
            model_used="OmniHuman",
            generation_time_seconds=elapsed,
            cost_estimate=cost,
        )


class AvatarGenerator:
    """Generates talking-head videos using Replicate API."""

    def __init__(self, api_token: Optional[str] = None, model: str = DEFAULT_MODEL):
        global replicate
        if replicate is None:
            import replicate as _replicate
            replicate = _replicate
        self.api_token = api_token or os.getenv("REPLICATE_API_TOKEN")
        if not self.api_token:
            raise ValueError(
                "REPLICATE_API_TOKEN not set. Get one at https://replicate.com/account/api-tokens"
            )
        os.environ["REPLICATE_API_TOKEN"] = self.api_token
        self.model_id = MODELS.get(model, model)
        logger.info(f"AvatarGenerator initialized: model={model}")

    def generate(
        self,
        audio_path: str,
        image_path: str,
        output_path: str,
        enhancer: str = "gfpgan",
        preprocess: str = "crop",
    ) -> AvatarResult:
        """Generate talking-head video from image + audio.

        Args:
            audio_path: Path to speech audio file (mp3/wav)
            image_path: Path to reference face image (png/jpg)
            output_path: Where to save the output video
            enhancer: Face enhancer ('gfpgan' for better quality, None for speed)
            preprocess: Face preprocessing ('crop', 'resize', 'full')
        """
        audio_file = Path(audio_path)
        image_file = Path(image_path)

        if not audio_file.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        if not image_file.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Generating avatar video: {image_path} + {audio_path}")
        start_time = time.time()

        # Run SadTalker on Replicate
        with open(audio_file, "rb") as af, open(image_file, "rb") as imf:
            input_params = {
                "source_image": imf,
                "driven_audio": af,
                "preprocess": preprocess,
                "still_mode": True,  # Less head movement for news presenter style
                "use_enhancer": enhancer is not None,
                "batch_size": 2,
                "size": 256,
                "pose_style": 0,
                "facerender": "facevid2vid",
                "exp_weight": 1,
                "use_ref_video": False,
                "use_idle_mode": False,
            }

            if enhancer:
                input_params["enhancer"] = enhancer

            result_url = replicate.run(self.model_id, input=input_params)

        # Download result video
        if isinstance(result_url, str):
            video_url = result_url
        elif hasattr(result_url, "url"):
            video_url = result_url.url
        else:
            # Replicate sometimes returns a FileOutput or iterator
            video_url = str(result_url)

        logger.info(f"Downloading result from: {video_url}")
        response = requests.get(video_url, timeout=120)
        response.raise_for_status()

        with open(output, "wb") as f:
            f.write(response.content)

        elapsed = time.time() - start_time
        # SadTalker on Replicate costs ~$0.05 per run
        cost = 0.05

        logger.info(f"Avatar video saved: {output} ({elapsed:.1f}s, ~${cost:.2f})")

        return AvatarResult(
            video_path=str(output),
            model_used=self.model_id.split(":")[0] if ":" in self.model_id else self.model_id,
            generation_time_seconds=elapsed,
            cost_estimate=cost,
        )


# ============================================================================
# Reference Image Preparation
# ============================================================================

class FFmpegStaticAvatarGenerator:
    """Generates video from static image + audio using FFmpeg.

    No lip-sync, but zero-cost and works immediately.
    Good enough to start publishing while researching better avatar APIs.
    """

    def __init__(self):
        self.model = "ffmpeg-static"
        logger.info("FFmpegStaticAvatarGenerator initialized (no lip-sync)")

    def generate(
        self,
        audio_path: str,
        image_path: str,
        output_path: str,
    ) -> AvatarResult:
        """Generate video from static image + audio overlay."""
        start_time = time.time()
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        # FFmpeg: loop image for audio duration, overlay audio
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", image_path,
            "-i", audio_path,
            "-c:v", "libx264", "-tune", "stillimage",
            "-c:a", "aac", "-b:a", "192k",
            "-vf", "scale=1080:1080:force_original_aspect_ratio=decrease,pad=1080:1080:(ow-iw)/2:(oh-ih)/2",
            "-pix_fmt", "yuv420p",
            "-shortest",
            str(output),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg static avatar failed: {result.stderr}")

        elapsed = time.time() - start_time
        logger.info(f"Static avatar video saved: {output} ({elapsed:.1f}s, $0.00)")

        return AvatarResult(
            video_path=str(output),
            model_used="ffmpeg-static",
            generation_time_seconds=elapsed,
            cost_estimate=0.0,
        )


def get_avatar_generator():
    """Factory function to get the best available avatar generator.

    Priority: Replicate SadTalker > FFmpeg static (free fallback).
    Poe OmniHuman is not available via API.
    """
    replicate_token = os.getenv("REPLICATE_API_TOKEN")
    if replicate_token:
        try:
            logger.info("Using Replicate SadTalker avatar generator")
            return AvatarGenerator(api_token=replicate_token)
        except Exception as e:
            logger.warning(f"Replicate init failed: {e}, falling back to FFmpeg static")

    logger.info("Using FFmpeg static avatar (free, no lip-sync)")
    return FFmpegStaticAvatarGenerator()


def prepare_reference_image(
    input_path: str,
    output_path: str,
    target_size: int = 512,
) -> str:
    """Prepare reference image for optimal SadTalker results.

    - Crops to square
    - Resizes to target size
    - Ensures face is centered and well-lit
    """
    import subprocess

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    # Use ffmpeg to crop center square and resize
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vf", f"crop='min(iw,ih)':'min(iw,ih)',scale={target_size}:{target_size}",
        "-frames:v", "1",
        str(output),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr}")

    logger.info(f"Reference image prepared: {output}")
    return str(output)


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Avatar video generator for AI Thực Chiến")
    parser.add_argument("--audio", "-a", required=True, help="Input audio file (mp3/wav)")
    parser.add_argument("--image", "-i", required=True, help="Reference face image (png/jpg)")
    parser.add_argument("--output", "-o", required=True, help="Output video file path")
    parser.add_argument("--enhancer", default="gfpgan",
                        choices=["gfpgan", "none"],
                        help="Face enhancer (default: gfpgan)")
    parser.add_argument("--preprocess", default="crop",
                        choices=["crop", "resize", "full"],
                        help="Face preprocessing (default: crop)")
    parser.add_argument("--model", default="sadtalker",
                        help="Model to use (default: sadtalker)")
    parser.add_argument("--prepare-image", metavar="INPUT",
                        help="Prepare reference image from INPUT path")

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    if args.prepare_image:
        prepared = prepare_reference_image(args.prepare_image, args.image)
        print(f"Prepared image: {prepared}")
        return

    enhancer = None if args.enhancer == "none" else args.enhancer

    generator = AvatarGenerator(model=args.model)
    result = generator.generate(
        audio_path=args.audio,
        image_path=args.image,
        output_path=args.output,
        enhancer=enhancer,
        preprocess=args.preprocess,
    )

    print(f"Video: {result.video_path}")
    print(f"Model: {result.model_used}")
    print(f"Time: {result.generation_time_seconds:.1f}s")
    print(f"Cost: ~${result.cost_estimate:.2f}")


if __name__ == "__main__":
    main()
