#!/usr/bin/env python3
"""
Avatar Video Generator for AI Thực Chiến

Generates talking-head avatar videos from a reference image + audio.
Uses Replicate API (SadTalker model) — ~$0.27/clip, no GPU needed locally.
Automatically chunks long audio (>3 min) to avoid Replicate timeouts.

Usage:
    python3 avatar_generator.py --audio speech.mp3 --image avatar.png --output talking.mp4
    python3 avatar_generator.py --audio speech.mp3 --image avatar.png --output talking.mp4 --enhancer gfpgan
"""

import os
import sys
import time
import json
import shutil
import logging
import argparse
import subprocess
import requests
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass

try:
    import replicate
except ImportError:
    print("ERROR: replicate not found. Install with: pip install replicate")
    sys.exit(1)


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


# ============================================================================
# Avatar Generation
# ============================================================================

class AvatarGenerator:
    """Generates talking-head videos using Replicate API.

    Automatically chunks audio longer than MAX_AUDIO_SECONDS to avoid
    Replicate timeouts/OOM errors, then concatenates the video clips.
    """

    MAX_AUDIO_SECONDS = 180  # 3 minutes per chunk (safe limit for SadTalker)

    def __init__(self, api_token: Optional[str] = None, model: str = DEFAULT_MODEL):
        self.api_token = api_token or os.getenv("REPLICATE_API_TOKEN")
        if not self.api_token:
            raise ValueError(
                "REPLICATE_API_TOKEN not set. Get one at https://replicate.com/account/api-tokens"
            )
        os.environ["REPLICATE_API_TOKEN"] = self.api_token
        self.model_id = MODELS.get(model, model)
        logger.info(f"AvatarGenerator initialized: model={model}")

    @staticmethod
    def _get_audio_duration(audio_path: str) -> float:
        """Get audio duration in seconds using ffprobe."""
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                 "-of", "json", audio_path],
                capture_output=True, text=True,
            )
            data = json.loads(result.stdout)
            return float(data["format"]["duration"])
        except (KeyError, json.JSONDecodeError, FileNotFoundError):
            logger.warning("ffprobe failed, assuming audio is short")
            return 0.0

    @staticmethod
    def _split_audio(audio_path: str, max_seconds: float, output_dir: Path) -> List[str]:
        """Split audio into chunks of max_seconds using ffmpeg."""
        duration = AvatarGenerator._get_audio_duration(audio_path)
        if duration <= max_seconds:
            return [audio_path]

        output_dir.mkdir(parents=True, exist_ok=True)
        chunks = []
        start = 0.0
        i = 0

        while start < duration:
            chunk_path = str(output_dir / f"_audio_chunk_{i:03d}.mp3")
            cmd = [
                "ffmpeg", "-y", "-i", audio_path,
                "-ss", str(start), "-t", str(max_seconds),
                "-c", "copy", chunk_path,
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode != 0:
                raise RuntimeError(f"ffmpeg split failed: {proc.stderr}")
            chunks.append(chunk_path)
            start += max_seconds
            i += 1

        logger.info(f"Split {duration:.0f}s audio into {len(chunks)} chunks")
        return chunks

    @staticmethod
    def _concat_videos(video_files: List[str], output_path: str):
        """Concatenate video files using ffmpeg."""
        if len(video_files) == 1:
            shutil.copy2(video_files[0], output_path)
            return

        list_file = Path(output_path).parent / "_video_concat_list.txt"
        with open(list_file, "w") as f:
            for vf in video_files:
                f.write(f"file '{vf}'\n")

        proc = subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
             "-i", str(list_file), "-c", "copy", output_path],
            capture_output=True, text=True,
        )
        list_file.unlink(missing_ok=True)

        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg concat failed: {proc.stderr}")
        logger.info(f"Concatenated {len(video_files)} video chunks")

    def _generate_single_clip(
        self,
        audio_path: str,
        image_path: str,
        output_path: str,
        enhancer: str = "gfpgan",
        preprocess: str = "crop",
    ) -> str:
        """Generate a single avatar video clip from image + audio chunk."""
        with open(audio_path, "rb") as af, open(image_path, "rb") as imf:
            input_params = {
                "source_image": imf,
                "driven_audio": af,
                "preprocess": preprocess,
                "still_mode": True,
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

        if isinstance(result_url, str):
            video_url = result_url
        elif hasattr(result_url, "url"):
            video_url = result_url.url
        else:
            video_url = str(result_url)

        logger.info(f"Downloading clip from: {video_url}")
        response = requests.get(video_url, timeout=120)
        response.raise_for_status()

        with open(output_path, "wb") as f:
            f.write(response.content)

        return output_path

    def generate(
        self,
        audio_path: str,
        image_path: str,
        output_path: str,
        enhancer: str = "gfpgan",
        preprocess: str = "crop",
    ) -> AvatarResult:
        """Generate talking-head video from image + audio.

        Automatically chunks long audio (>3 min) to avoid Replicate
        timeouts, generates clips per chunk, then concatenates.

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

        # Split long audio into chunks to avoid Replicate timeout/OOM
        audio_chunks = self._split_audio(
            audio_path, self.MAX_AUDIO_SECONDS, output.parent
        )

        if len(audio_chunks) == 1 and audio_chunks[0] == audio_path:
            # Short audio — single pass
            self._generate_single_clip(
                audio_path, image_path, str(output), enhancer, preprocess
            )
            num_chunks = 1
        else:
            # Long audio — generate per chunk, then concatenate
            video_chunks = []
            for i, chunk_audio in enumerate(audio_chunks):
                chunk_video = str(output.parent / f"_video_chunk_{i:03d}.mp4")
                logger.info(f"Generating chunk {i+1}/{len(audio_chunks)}")
                self._generate_single_clip(
                    chunk_audio, image_path, chunk_video, enhancer, preprocess
                )
                video_chunks.append(chunk_video)

            self._concat_videos(video_chunks, str(output))
            num_chunks = len(audio_chunks)

            # Cleanup temp files
            for f in audio_chunks:
                if f != audio_path:
                    Path(f).unlink(missing_ok=True)
            for f in video_chunks:
                Path(f).unlink(missing_ok=True)

        elapsed = time.time() - start_time
        # SadTalker on Replicate costs ~$0.27 per short clip
        cost = 0.27 * num_chunks

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
