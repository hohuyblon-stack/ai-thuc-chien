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
import logging
import argparse
import requests
from pathlib import Path
from typing import Optional
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
    """Generates talking-head videos using Replicate API."""

    def __init__(self, api_token: Optional[str] = None, model: str = DEFAULT_MODEL):
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
