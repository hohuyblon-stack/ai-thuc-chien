#!/usr/bin/env python3
"""
Daily Video Pipeline for AI Thực Chiến

Orchestrates the full automated pipeline:
1. Fetch today's AI news (Tavily/RSS)
2. Generate Vietnamese video script (Claude API)
3. Generate Vietnamese speech audio (Edge TTS)
4. Generate talking-head avatar video (Replicate/SadTalker)
5. Compose final video with overlays + subtitles (FFmpeg)
6. Upload to YouTube (YouTube Data API v3)

Usage:
    python3 daily_pipeline.py                    # Full pipeline
    python3 daily_pipeline.py --step tts         # Run single step
    python3 daily_pipeline.py --dry-run          # Preview without uploading
    python3 daily_pipeline.py --format short     # Generate Short instead of long-form
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load environment
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# Local imports
from fb_news_fetcher import NewsFetcher
from tts_generator import VietnameseTTS, clean_script_for_tts
from avatar_generator import AvatarGenerator
from video_composer import VideoComposer

# ============================================================================
# Configuration
# ============================================================================

PROJECT_DIR = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_DIR / "output"
AVATAR_IMAGE = PROJECT_DIR / "assets" / "avatar.png"  # Reference face image
LOGS_DIR = PROJECT_DIR / "logs"

# Ensure directories exist
OUTPUT_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
(PROJECT_DIR / "assets").mkdir(exist_ok=True)

# ============================================================================
# Logging
# ============================================================================

def setup_logging() -> logging.Logger:
    log_file = LOGS_DIR / f"pipeline_{datetime.now().strftime('%Y%m%d')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(str(log_file)),
        ],
    )
    return logging.getLogger("pipeline")


logger = setup_logging()


# ============================================================================
# Script Generation (using Claude API)
# ============================================================================

def generate_script(news_summary: str, format_type: str = "long") -> dict:
    """Generate video script from news using Claude API."""
    from anthropic import Anthropic

    api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY or CLAUDE_API_KEY not set")

    client = Anthropic(api_key=api_key)

    if format_type == "short":
        duration_guide = "45-60 giây"
        structure = """
Cấu trúc (45-60 giây):
- [0-3s] HOOK: Câu gây sốc/tò mò
- [3-40s] NỘI DUNG: Giải thích ngắn gọn, 2-3 key points
- [40-55s] CTA: Kêu gọi subscribe + bấm chuông"""
    else:
        duration_guide = "5-8 phút"
        structure = """
Cấu trúc (5-8 phút):
- [0-30s] HOOK: Tại sao phải xem video này?
- [30s-1m] CONTEXT: Bối cảnh tin tức
- [1m-5m] NỘI DUNG CHÍNH: Phân tích chi tiết, ví dụ cụ thể, ảnh hưởng đến business VN
- [5m-6m] KẾT LUẬN: Tổng kết + lời khuyên thực tế
- [6m-7m] CTA: Subscribe, bấm chuông, comment"""

    prompt = f"""Bạn là scriptwriter cho kênh YouTube "AI Thực Chiến" — kênh tiếng Việt về AI & Automation cho chủ doanh nghiệp, bán hàng online, solopreneur.

Dựa trên tin tức AI hôm nay, viết một VIDEO SCRIPT hoàn chỉnh ({duration_guide}).

TIN TỨC HÔM NAY:
{news_summary}

{structure}

YÊU CẦU:
1. Viết TIẾNG VIỆT 100% — giọng nói tự nhiên, như đang nói chuyện
2. Tông giọng: thân thiết, hào hứng nhưng không quá lố
3. Luôn liên hệ: tin này ảnh hưởng gì đến business người Việt?
4. Dùng ví dụ cụ thể: "Ví dụ anh bán hàng Shopee, cái này giúp anh..."
5. KHÔNG dùng thuật ngữ kỹ thuật — giải thích đơn giản
6. Mở đầu: "Xin chào các bạn, mình là AI Thực Chiến..."

Trả về JSON:
{{
    "title": "Tiêu đề video (hấp dẫn, SEO, max 80 ký tự)",
    "description": "Mô tả YouTube (150-300 từ, có hashtags)",
    "tags": ["tag1", "tag2", "..."],
    "script": "Toàn bộ nội dung script để đọc (chỉ text thuần, không có stage directions)",
    "key_points": ["điểm 1", "điểm 2", "điểm 3"]
}}

CHỈ trả về JSON, không có text khác."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()

    # Parse JSON from response (handle markdown code blocks)
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

    return json.loads(raw)


# ============================================================================
# News Fetching
# ============================================================================

def fetch_news() -> str:
    """Fetch today's AI news and return as summary text."""
    tavily_key = os.getenv("TAVILY_API_KEY")

    if tavily_key:
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=tavily_key)
            results = client.search(
                query="AI news today artificial intelligence latest",
                search_depth="basic",
                max_results=5,
            )
            articles = []
            for r in results.get("results", []):
                articles.append(f"- {r['title']}: {r.get('content', '')[:200]}")
            return "\n".join(articles)
        except Exception as e:
            logger.warning(f"Tavily search failed: {e}, falling back to RSS")

    # Fallback: RSS feeds
    try:
        fetcher = NewsFetcher()
        news_items = fetcher.fetch_all()
        articles = []
        for item in news_items[:5]:
            articles.append(f"- {item.get('title', '')}: {item.get('summary', '')[:200]}")
        return "\n".join(articles) if articles else "Không có tin tức mới hôm nay."
    except Exception as e:
        logger.error(f"RSS fetch failed: {e}")
        return "Các tin tức AI nổi bật trong tuần: AI agents, automation tools, và AI trong e-commerce."


# ============================================================================
# YouTube Upload
# ============================================================================

def upload_to_youtube(
    video_path: str,
    title: str,
    description: str,
    tags: list,
    category_id: str = "28",  # Science & Technology
) -> Optional[str]:
    """Upload video to YouTube using Data API v3.

    Returns video ID if successful, None if failed.
    """
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except ImportError:
        logger.error("google-api-python-client not installed")
        return None

    token_path = PROJECT_DIR / "youtube_token.json"
    if not token_path.exists():
        logger.error(f"YouTube token not found: {token_path}")
        logger.info("Run 'python3 youtube-uploader.py --auth' to authenticate first")
        return None

    creds = Credentials.from_authorized_user_file(str(token_path))
    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": category_id,
            "defaultLanguage": "vi",
            "defaultAudioLanguage": "vi",
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        _, response = request.next_chunk()

    video_id = response["id"]
    logger.info(f"Uploaded to YouTube: https://youtube.com/watch?v={video_id}")
    return video_id


# ============================================================================
# Pipeline Steps
# ============================================================================

class DailyPipeline:
    """Orchestrates the full daily video pipeline."""

    def __init__(self, format_type: str = "long", dry_run: bool = False):
        self.format_type = format_type
        self.dry_run = dry_run
        self.today = datetime.now().strftime("%Y%m%d")
        self.work_dir = OUTPUT_DIR / self.today
        self.work_dir.mkdir(exist_ok=True)
        logger.info(f"Pipeline initialized: format={format_type}, dry_run={dry_run}")
        logger.info(f"Work directory: {self.work_dir}")

    def step_news(self) -> str:
        """Step 1: Fetch AI news."""
        logger.info("=== STEP 1: Fetching news ===")
        news = fetch_news()
        news_file = self.work_dir / "news.txt"
        news_file.write_text(news, encoding="utf-8")
        logger.info(f"News saved: {news_file} ({len(news)} chars)")
        return news

    def step_script(self, news: str) -> dict:
        """Step 2: Generate video script."""
        logger.info("=== STEP 2: Generating script ===")
        script_data = generate_script(news, self.format_type)
        script_file = self.work_dir / "script.json"
        script_file.write_text(json.dumps(script_data, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"Script saved: {script_file}")
        logger.info(f"Title: {script_data['title']}")
        return script_data

    def step_tts(self, script_text: str) -> str:
        """Step 3: Generate Vietnamese audio."""
        logger.info("=== STEP 3: Generating TTS audio ===")
        audio_path = str(self.work_dir / "speech.mp3")
        subtitle_path = str(self.work_dir / "subtitles.srt")

        tts = VietnameseTTS(voice="male", rate="+5%")
        clean_text = clean_script_for_tts(script_text)
        result = tts.generate_sync(clean_text, audio_path, subtitle_path)

        logger.info(f"Audio: {result.audio_path} ({result.duration_seconds:.1f}s)")
        return audio_path

    def step_avatar(self, audio_path: str) -> str:
        """Step 4: Generate talking-head avatar video."""
        logger.info("=== STEP 4: Generating avatar video ===")

        if not AVATAR_IMAGE.exists():
            raise FileNotFoundError(
                f"Avatar image not found: {AVATAR_IMAGE}\n"
                f"Please place your face photo at: {AVATAR_IMAGE}\n"
                f"Requirements: Clear front-facing photo, 512x512+ px, good lighting"
            )

        avatar_video = str(self.work_dir / "avatar.mp4")
        generator = AvatarGenerator()
        result = generator.generate(
            audio_path=audio_path,
            image_path=str(AVATAR_IMAGE),
            output_path=avatar_video,
            enhancer="gfpgan",
            preprocess="crop",
        )

        logger.info(f"Avatar video: {result.video_path} (~${result.cost_estimate:.2f})")
        return avatar_video

    def step_compose(
        self, avatar_video: str, title: str, subtitle_path: Optional[str] = None
    ) -> str:
        """Step 5: Compose final video."""
        logger.info("=== STEP 5: Composing final video ===")
        final_video = str(self.work_dir / "final.mp4")

        composer = VideoComposer()
        result = composer.compose(
            avatar_video=avatar_video,
            output_path=final_video,
            subtitles=subtitle_path,
            title_text=title,
        )

        logger.info(f"Final video: {result.output_path} ({result.duration_seconds:.1f}s, {result.file_size_mb:.1f}MB)")
        return final_video

    def step_upload(self, video_path: str, script_data: dict) -> Optional[str]:
        """Step 6: Upload to YouTube."""
        logger.info("=== STEP 6: Uploading to YouTube ===")

        if self.dry_run:
            logger.info("DRY RUN — skipping upload")
            return None

        video_id = upload_to_youtube(
            video_path=video_path,
            title=script_data["title"],
            description=script_data["description"],
            tags=script_data.get("tags", ["AI", "automation", "Vietnam"]),
        )
        return video_id

    def run(self, start_step: Optional[str] = None) -> dict:
        """Run the full pipeline (or from a specific step)."""
        logger.info(f"{'='*60}")
        logger.info(f"DAILY PIPELINE START: {self.today}")
        logger.info(f"{'='*60}")

        results = {}

        try:
            # Step 1: News
            if not start_step or start_step == "news":
                news = self.step_news()
                results["news"] = news
            else:
                news_file = self.work_dir / "news.txt"
                news = news_file.read_text(encoding="utf-8") if news_file.exists() else ""

            # Step 2: Script
            if not start_step or start_step in ("news", "script"):
                script_data = self.step_script(news)
                results["script"] = script_data
            else:
                script_file = self.work_dir / "script.json"
                script_data = json.loads(script_file.read_text(encoding="utf-8"))

            # Step 3: TTS
            if not start_step or start_step in ("news", "script", "tts"):
                audio_path = self.step_tts(script_data["script"])
                results["audio"] = audio_path
            else:
                audio_path = str(self.work_dir / "speech.mp3")

            # Step 4: Avatar
            if not start_step or start_step in ("news", "script", "tts", "avatar"):
                avatar_video = self.step_avatar(audio_path)
                results["avatar"] = avatar_video
            else:
                avatar_video = str(self.work_dir / "avatar.mp4")

            # Step 5: Compose
            if not start_step or start_step in ("news", "script", "tts", "avatar", "compose"):
                subtitle_path = str(self.work_dir / "subtitles.srt")
                final_video = self.step_compose(
                    avatar_video,
                    script_data["title"],
                    subtitle_path if Path(subtitle_path).exists() else None,
                )
                results["final_video"] = final_video
            else:
                final_video = str(self.work_dir / "final.mp4")

            # Step 6: Upload
            video_id = self.step_upload(final_video, script_data)
            results["youtube_id"] = video_id

            # Save pipeline results
            results["status"] = "success"
            results["timestamp"] = datetime.now().isoformat()
            results_file = self.work_dir / "pipeline_results.json"
            results_file.write_text(json.dumps(results, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

            logger.info(f"{'='*60}")
            logger.info(f"PIPELINE COMPLETE: {results.get('youtube_id', 'dry-run')}")
            logger.info(f"{'='*60}")

        except Exception as e:
            logger.error(f"Pipeline failed at step: {e}", exc_info=True)
            results["status"] = "failed"
            results["error"] = str(e)

        return results


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Daily video pipeline for AI Thực Chiến",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Steps (in order):
  news      Fetch AI news from Tavily/RSS
  script    Generate Vietnamese video script (Claude API)
  tts       Generate speech audio (Edge TTS)
  avatar    Generate talking-head video (Replicate/SadTalker)
  compose   Compose final video (FFmpeg)
  upload    Upload to YouTube

Examples:
  python3 daily_pipeline.py                     # Full pipeline
  python3 daily_pipeline.py --dry-run           # Preview, no upload
  python3 daily_pipeline.py --step tts          # Resume from TTS step
  python3 daily_pipeline.py --format short      # Generate Short video
        """,
    )
    parser.add_argument("--step", choices=["news", "script", "tts", "avatar", "compose", "upload"],
                        help="Start from specific step (uses cached data for earlier steps)")
    parser.add_argument("--format", choices=["short", "long"], default="long",
                        help="Video format (default: long)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Run pipeline without uploading")

    args = parser.parse_args()

    pipeline = DailyPipeline(format_type=args.format, dry_run=args.dry_run)
    results = pipeline.run(start_step=args.step)

    if results.get("status") == "success":
        print(f"\nPipeline completed successfully!")
        if results.get("youtube_id"):
            print(f"YouTube: https://youtube.com/watch?v={results['youtube_id']}")
        print(f"Output: {pipeline.work_dir}")
    else:
        print(f"\nPipeline failed: {results.get('error', 'unknown')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
