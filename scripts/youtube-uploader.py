#!/usr/bin/env python3
"""
YouTube Content Uploader for AI Thực Chiến

Uploads video content to YouTube with AI-generated descriptions and SEO optimization.
Handles scheduling, metadata generation, and error recovery.

Usage:
    python3 youtube-uploader.py --video path/to/video.mp4 --topic "ChatGPT for e-commerce"
    python3 youtube-uploader.py --queue-dir ./pending_uploads/
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict

import google.auth.transport.requests
from google.auth.oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None


# ============================================================================
# Configuration
# ============================================================================

YOUTUBE_API_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
YOUTUBE_UPLOAD_TIMEOUT = 3600  # 1 hour timeout
SUPPORTED_VIDEO_FORMATS = {".mp4", ".mov", ".mkv", ".flv", ".avi", ".webm"}
MAX_TITLE_LENGTH = 100
MAX_DESCRIPTION_LENGTH = 5000


@dataclass
class VideoMetadata:
    """Represents video metadata for upload"""
    title: str
    description: str
    tags: List[str]
    category_id: str = "22"  # People & Blogs
    privacy_status: str = "private"  # Start with private, manual review before publish
    scheduled_time: Optional[str] = None  # ISO 8601 format for scheduled uploads
    language: str = "vi"  # Vietnamese


@dataclass
class UploadJob:
    """Represents a single upload job"""
    video_path: str
    topic: str
    format_type: str  # "short" or "long"
    series_name: Optional[str] = None
    upload_after: Optional[str] = None  # ISO 8601 timestamp
    retry_count: int = 0
    max_retries: int = 3


# ============================================================================
# Logging Setup
# ============================================================================

def setup_logging(log_file: Optional[str] = None) -> logging.Logger:
    """Configure logging for the application"""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)

    return logger


_log_dir = Path(__file__).parent.parent / "logs"
_log_dir.mkdir(exist_ok=True)
logger = setup_logging(str(_log_dir / "youtube_uploader.log"))


# ============================================================================
# YouTube API Authentication
# ============================================================================

class YouTubeAuthenticator:
    """Handles YouTube API authentication and token refresh"""

    def __init__(self, credentials_file: str = "credentials.json", token_file: str = "token.json"):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.credentials = None

    def authenticate(self) -> Any:
        """Authenticate with YouTube API, handling OAuth flow"""
        try:
            # Try to load existing token
            if os.path.exists(self.token_file):
                self.credentials = Credentials.from_authorized_user_file(
                    self.token_file, YOUTUBE_API_SCOPES
                )
                logger.info("Loaded existing credentials from token file")

            # If no valid credentials, start OAuth flow
            if not self.credentials or not self.credentials.valid:
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    logger.info("Refreshing expired credentials")
                    self.credentials.refresh(google.auth.transport.requests.Request())
                else:
                    logger.info("Starting new OAuth authentication flow")
                    if not os.path.exists(self.credentials_file):
                        raise FileNotFoundError(
                            f"Credentials file not found: {self.credentials_file}\n"
                            "Download OAuth credentials from Google Cloud Console"
                        )
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, YOUTUBE_API_SCOPES
                    )
                    self.credentials = flow.run_local_server(port=0)

                # Save credentials for next run
                with open(self.token_file, "w") as token:
                    token.write(self.credentials.to_json())
                logger.info("Saved credentials to token file")

            return self.credentials

        except FileNotFoundError as e:
            logger.error(f"Authentication failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during authentication: {e}")
            raise


# ============================================================================
# AI Content Generation
# ============================================================================

class ContentGenerator:
    """Uses Claude API to generate video metadata"""

    def __init__(self, api_key: Optional[str] = None):
        if Anthropic is None:
            raise ImportError("anthropic package not found. Install with: pip install anthropic")
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        self.client = Anthropic(api_key=self.api_key)

    def generate_description(
        self,
        topic: str,
        format_type: str = "long",
        language: str = "vi"
    ) -> str:
        """Generate YouTube description with SEO optimization"""
        logger.info(f"Generating description for: {topic}")

        prompt = f"""You are a YouTube content strategist for a Vietnamese AI automation channel.
Generate a compelling YouTube description for a video about: {topic}

Format: {'Short (max 200 words)' if format_type == 'short' else 'Long (max 500 words)'}
Language: {language}

Requirements:
1. Start with a hook line that summarizes the video
2. Include timestamps if applicable
3. Add 3-5 key takeaways in bullet format
4. Include tools/resources mentioned with links placeholder [LINK]
5. Add engagement question for comments
6. Include relevant Vietnamese hashtags (#AI #TựđộngHóa etc)
7. Use format: 📌 Nội dung chính:, 🎯 Bạn sẽ học được:, 🔗 Công cụ trong video:

Output ONLY the description, no additional text."""

        message = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        description = message.content[0].text.strip()
        logger.debug(f"Generated description length: {len(description)} chars")
        return description[:MAX_DESCRIPTION_LENGTH]

    def generate_title(
        self,
        topic: str,
        language: str = "vi",
        format_type: str = "long"
    ) -> str:
        """Generate SEO-optimized YouTube title"""
        logger.info(f"Generating title for: {topic}")

        prompt = f"""Generate a compelling YouTube title for a Vietnamese AI automation channel.
Topic: {topic}
Video Format: {format_type}

Requirements:
1. Max 100 characters (including spaces)
2. Include primary keyword at the beginning
3. Use power words (Tiết kiệm, Mới, Thực tế, Hướng dẫn, etc)
4. Include number if relevant (ví dụ: 5, 10, 90)
5. Optimize for Vietnamese SMB audience
6. Make it clickable but not clickbait

Output ONLY the title, no quotes, no explanation."""

        message = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=100,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        title = message.content[0].text.strip()
        if title.startswith('"') and title.endswith('"'):
            title = title[1:-1]
        logger.debug(f"Generated title: {title}")
        return title[:MAX_TITLE_LENGTH]

    def generate_tags(
        self,
        topic: str,
        language: str = "vi"
    ) -> List[str]:
        """Generate SEO-optimized tags"""
        logger.info(f"Generating tags for: {topic}")

        prompt = f"""Generate 10-15 YouTube tags for a Vietnamese AI automation video.
Topic: {topic}

Requirements:
1. Mix of broad and specific keywords
2. Include Vietnamese language tags
3. Include automation/AI related tags
4. Include SMB business tags
5. 1-3 words per tag
6. Focus on Vietnamese search behavior

Format: Return as comma-separated list, no quotes.

Output ONLY the tags."""

        message = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=200,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        tags_text = message.content[0].text.strip()
        tags = [tag.strip() for tag in tags_text.split(",") if tag.strip()]
        logger.debug(f"Generated {len(tags)} tags")
        return tags[:30]  # YouTube limit is 30 tags

    def generate_all_metadata(
        self,
        topic: str,
        format_type: str = "long"
    ) -> VideoMetadata:
        """Generate complete metadata for video"""
        logger.info(f"Generating all metadata for: {topic}")

        title = self.generate_title(topic, format_type=format_type)
        description = self.generate_description(topic, format_type=format_type)
        tags = self.generate_tags(topic)

        metadata = VideoMetadata(
            title=title,
            description=description,
            tags=tags,
            category_id="22",  # People & Blogs
            privacy_status="private"  # Always start private for review
        )

        logger.info(f"Generated metadata: title={title}, tags={len(tags)}")
        return metadata


# ============================================================================
# Video Upload
# ============================================================================

class YouTubeUploader:
    """Handles video upload to YouTube"""

    def __init__(self, credentials: Any):
        self.youtube = build("youtube", "v3", credentials=credentials)
        logger.info("Initialized YouTube API client")

    def upload_video(
        self,
        video_path: str,
        metadata: VideoMetadata,
        scheduled_time: Optional[str] = None
    ) -> Dict[str, Any]:
        """Upload video to YouTube with metadata"""
        try:
            # Validate video file
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"Video file not found: {video_path}")

            if Path(video_path).suffix.lower() not in SUPPORTED_VIDEO_FORMATS:
                raise ValueError(f"Unsupported video format. Supported: {SUPPORTED_VIDEO_FORMATS}")

            file_size = os.path.getsize(video_path)
            logger.info(f"Uploading video: {video_path} ({file_size / (1024**2):.1f}MB)")

            # Prepare request body
            request_body = {
                "snippet": {
                    "title": metadata.title,
                    "description": metadata.description,
                    "tags": metadata.tags,
                    "categoryId": metadata.category_id,
                    "defaultLanguage": metadata.language,
                    "defaultAudioLanguage": metadata.language
                },
                "status": {
                    "privacyStatus": metadata.privacy_status,
                    "madeForKids": False,
                }
            }

            # Add scheduled time if provided
            if scheduled_time:
                request_body["status"]["publishAt"] = scheduled_time
                request_body["status"]["privacyStatus"] = "private"
                logger.info(f"Scheduling video for: {scheduled_time}")

            # Build upload request
            media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
            request = self.youtube.videos().insert(
                part="snippet,status",
                body=request_body,
                media_body=media
            )

            # Execute upload with retry logic
            response = None
            retry_count = 0
            max_retries = 3

            while response is None:
                try:
                    status, response = request.next_chunk()
                    if status:
                        progress = int(status.progress() * 100)
                        logger.info(f"Upload progress: {progress}%")
                except HttpError as e:
                    if e.resp.status in [500, 502, 503, 504]:
                        retry_count += 1
                        if retry_count < max_retries:
                            logger.warning(f"Server error, retrying... ({retry_count}/{max_retries})")
                            continue
                    raise

            video_id = response.get("id")
            logger.info(f"Video uploaded successfully! ID: {video_id}")
            logger.info(f"URL: https://www.youtube.com/watch?v={video_id}")

            return {
                "video_id": video_id,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "title": metadata.title,
                "upload_time": datetime.now().isoformat(),
                "status": "scheduled" if scheduled_time else "uploaded"
            }

        except FileNotFoundError as e:
            logger.error(f"File error: {e}")
            raise
        except ValueError as e:
            logger.error(f"Validation error: {e}")
            raise
        except HttpError as e:
            logger.error(f"YouTube API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during upload: {e}")
            raise

    def schedule_upload(
        self,
        video_path: str,
        metadata: VideoMetadata,
        upload_datetime: datetime
    ) -> Dict[str, Any]:
        """Schedule video upload for specific time"""
        iso_time = upload_datetime.isoformat() + "Z"
        logger.info(f"Scheduling upload for: {iso_time}")
        return self.upload_video(video_path, metadata, scheduled_time=iso_time)


# ============================================================================
# Upload Queue Management
# ============================================================================

class UploadQueue:
    """Manages upload queue and retry logic"""

    def __init__(self, queue_file: str = "upload_queue.json"):
        self.queue_file = queue_file
        self.queue: List[UploadJob] = []
        self.load_queue()

    def load_queue(self):
        """Load queue from file"""
        if os.path.exists(self.queue_file):
            try:
                with open(self.queue_file, "r") as f:
                    data = json.load(f)
                    self.queue = [UploadJob(**job) for job in data]
                logger.info(f"Loaded {len(self.queue)} jobs from queue")
            except Exception as e:
                logger.error(f"Error loading queue: {e}")
                self.queue = []
        else:
            self.queue = []

    def save_queue(self):
        """Save queue to file"""
        try:
            with open(self.queue_file, "w") as f:
                json.dump([asdict(job) for job in self.queue], f, indent=2)
            logger.debug(f"Saved {len(self.queue)} jobs to queue")
        except Exception as e:
            logger.error(f"Error saving queue: {e}")

    def add_job(self, job: UploadJob):
        """Add job to queue"""
        self.queue.append(job)
        self.save_queue()
        logger.info(f"Added job: {job.video_path}")

    def get_ready_jobs(self) -> List[UploadJob]:
        """Get jobs ready for upload"""
        ready_jobs = []
        now = datetime.now().isoformat()

        for job in self.queue:
            if job.upload_after is None or job.upload_after <= now:
                if job.retry_count < job.max_retries:
                    ready_jobs.append(job)

        return ready_jobs

    def mark_complete(self, job: UploadJob):
        """Remove completed job from queue"""
        self.queue = [j for j in self.queue if j.video_path != job.video_path]
        self.save_queue()
        logger.info(f"Completed job: {job.video_path}")

    def mark_failed(self, job: UploadJob):
        """Mark job as failed and retry later"""
        for j in self.queue:
            if j.video_path == job.video_path:
                j.retry_count += 1
                if j.retry_count >= j.max_retries:
                    logger.error(f"Max retries exceeded: {job.video_path}")
                    self.mark_complete(job)
                else:
                    logger.warning(f"Marked for retry ({j.retry_count}/{j.max_retries}): {job.video_path}")
        self.save_queue()


# ============================================================================
# Main Upload Orchestration
# ============================================================================

class YouTubeContentManager:
    """Main orchestrator for YouTube content uploads"""

    def __init__(
        self,
        credentials_file: str = "credentials.json",
        token_file: str = "token.json"
    ):
        self.auth = YouTubeAuthenticator(credentials_file, token_file)
        self.credentials = self.auth.authenticate()
        self.uploader = YouTubeUploader(self.credentials)
        self.content_gen = ContentGenerator()
        self.queue = UploadQueue()

    def upload_single_video(
        self,
        video_path: str,
        topic: str,
        format_type: str = "long",
        scheduled_time: Optional[str] = None
    ) -> Dict[str, Any]:
        """Upload a single video with AI-generated metadata"""
        try:
            # Generate metadata
            logger.info(f"Processing video: {video_path}")
            metadata = self.content_gen.generate_all_metadata(topic, format_type)

            # Upload video
            if scheduled_time:
                upload_dt = datetime.fromisoformat(scheduled_time.replace("Z", "+00:00"))
                result = self.uploader.schedule_upload(video_path, metadata, upload_dt)
            else:
                result = self.uploader.upload_video(video_path, metadata)

            logger.info(f"Upload successful: {result['video_id']}")
            return result

        except Exception as e:
            logger.error(f"Upload failed: {e}")
            raise

    def process_upload_queue(self):
        """Process all pending uploads in queue"""
        ready_jobs = self.queue.get_ready_jobs()

        if not ready_jobs:
            logger.info("No jobs ready for upload")
            return

        logger.info(f"Processing {len(ready_jobs)} jobs from queue")

        for job in ready_jobs:
            try:
                logger.info(f"Processing: {job.topic}")
                result = self.upload_single_video(
                    job.video_path,
                    job.topic,
                    job.format_type,
                    job.upload_after
                )
                self.queue.mark_complete(job)
                logger.info(f"Job completed: {result['video_id']}")

            except Exception as e:
                logger.error(f"Job failed: {e}")
                self.queue.mark_failed(job)

    def add_to_queue(
        self,
        video_path: str,
        topic: str,
        format_type: str = "long",
        upload_after: Optional[str] = None,
        series_name: Optional[str] = None
    ):
        """Add video to upload queue"""
        job = UploadJob(
            video_path=video_path,
            topic=topic,
            format_type=format_type,
            series_name=series_name,
            upload_after=upload_after
        )
        self.queue.add_job(job)
        logger.info(f"Added to queue: {video_path}")


# ============================================================================
# CLI Interface
# ============================================================================

def main():
    """Command-line interface"""
    parser = argparse.ArgumentParser(
        description="YouTube uploader for AI Thực Chiến",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Upload single video
  python3 youtube-uploader.py --video video.mp4 --topic "ChatGPT for e-commerce"

  # Upload and schedule
  python3 youtube-uploader.py --video video.mp4 --topic "AI trends" --schedule "2026-03-15T10:00:00"

  # Add to queue for batch processing
  python3 youtube-uploader.py --queue-dir ./videos/ --format short

  # Process pending queue
  python3 youtube-uploader.py --process-queue
        """
    )

    parser.add_argument("--video", help="Path to video file for single upload")
    parser.add_argument("--topic", help="Video topic (required with --video)")
    parser.add_argument("--format", choices=["short", "long"], default="long",
                        help="Video format (default: long)")
    parser.add_argument("--schedule", help="Schedule upload time (ISO 8601 format)")
    parser.add_argument("--queue-dir", help="Add all videos in directory to queue")
    parser.add_argument("--process-queue", action="store_true",
                        help="Process pending uploads in queue")
    parser.add_argument("--credentials", default="credentials.json",
                        help="Path to Google credentials.json")
    parser.add_argument("--token", default="token.json",
                        help="Path to saved token.json")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be uploaded without actually uploading")

    args = parser.parse_args()

    # Initialize manager
    try:
        manager = YouTubeContentManager(args.credentials, args.token)
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        sys.exit(1)

    # Handle different modes
    try:
        if args.process_queue:
            manager.process_upload_queue()

        elif args.queue_dir:
            # Add all videos in directory to queue
            queue_path = Path(args.queue_dir)
            for video_file in queue_path.glob("*.*"):
                if video_file.suffix.lower() in SUPPORTED_VIDEO_FORMATS:
                    topic = video_file.stem  # Use filename as topic
                    manager.add_to_queue(
                        str(video_file),
                        topic,
                        format_type=args.format
                    )
            logger.info(f"Added videos from {args.queue_dir} to queue")

        elif args.video:
            if not args.topic:
                parser.error("--topic is required with --video")

            if args.dry_run:
                logger.info("DRY RUN MODE - not uploading")
                metadata = manager.content_gen.generate_all_metadata(args.topic, args.format)
                print("\n" + "=" * 60)
                print("GENERATED METADATA")
                print("=" * 60)
                print(f"Title: {metadata.title}")
                print(f"Tags: {', '.join(metadata.tags)}")
                print(f"\nDescription:\n{metadata.description}")
                print("=" * 60)
            else:
                result = manager.upload_single_video(
                    args.video,
                    args.topic,
                    args.format,
                    args.schedule
                )
                print("\n" + "=" * 60)
                print("UPLOAD SUCCESSFUL")
                print("=" * 60)
                print(f"Video ID: {result['video_id']}")
                print(f"URL: {result['url']}")
                print(f"Status: {result['status']}")
                print("=" * 60)
        else:
            parser.print_help()

    except KeyboardInterrupt:
        logger.warning("Upload interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
