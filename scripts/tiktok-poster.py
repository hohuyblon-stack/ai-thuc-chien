#!/usr/bin/env python3
"""
TikTok Content Poster
Automates scheduling and posting videos to TikTok using their Content Posting API.
Generates captions using Claude API and manages content queue.

Author: AI Thực Chiến
License: MIT
"""

import os
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List
import requests
import anthropic
from dotenv import load_dotenv

# ============================================================================
# CONFIGURATION & SETUP
# ============================================================================

# Load environment variables (explicit path for cron compatibility)
_env_path = Path(__file__).parent.parent / ".env"
load_dotenv(_env_path)

# Configure logging
_log_dir = Path(__file__).parent.parent / "logs"
_log_dir.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(_log_dir / 'tiktok_poster.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# API Configuration
TIKTOK_API_BASE = "https://open.tiktokapis.com/v2"
TIKTOK_ACCESS_TOKEN = os.getenv('TIKTOK_ACCESS_TOKEN')
TIKTOK_CLIENT_KEY = os.getenv('TIKTOK_CLIENT_KEY')
TIKTOK_CLIENT_SECRET = os.getenv('TIKTOK_CLIENT_SECRET')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY') or os.getenv('CLAUDE_API_KEY')

# Validation (lazy — don't exit at import time so pipeline can import selectively)
def _validate_tiktok_config():
    if not TIKTOK_ACCESS_TOKEN:
        raise RuntimeError("TIKTOK_ACCESS_TOKEN not found in environment variables")
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY (or CLAUDE_API_KEY) not found in environment variables")

# Initialize Claude client (lazy)
def _get_claude_client():
    _validate_tiktok_config()
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

claude_client = None  # initialized on first use

# Content queue file
QUEUE_FILE = Path(__file__).parent.parent / "content_queue.json"
POSTED_LOG = Path(__file__).parent.parent / "posted_videos.json"


# ============================================================================
# DATA MODELS
# ============================================================================

class ContentItem:
    """Represents a content item to be posted."""

    def __init__(
        self,
        video_path: str,
        title: str,
        category: str,  # "news", "tutorial", "case_study", "tool_review", "bts"
        hashtags: Optional[List[str]] = None,
        schedule_time: Optional[datetime] = None,
        status: str = "pending"
    ):
        self.video_path = video_path
        self.title = title
        self.category = category
        self.hashtags = hashtags or []
        self.schedule_time = schedule_time
        self.status = status  # pending, scheduled, posted, failed
        self.created_at = datetime.now()
        self.tiktok_video_id = None
        self.error_message = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'video_path': self.video_path,
            'title': self.title,
            'category': self.category,
            'hashtags': self.hashtags,
            'schedule_time': self.schedule_time.isoformat() if self.schedule_time else None,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'tiktok_video_id': self.tiktok_video_id,
            'error_message': self.error_message
        }

    @classmethod
    def from_dict(cls, data: Dict):
        """Create from dictionary."""
        item = cls(
            video_path=data['video_path'],
            title=data['title'],
            category=data['category'],
            hashtags=data.get('hashtags', []),
            schedule_time=datetime.fromisoformat(data['schedule_time']) if data.get('schedule_time') else None,
            status=data.get('status', 'pending')
        )
        item.tiktok_video_id = data.get('tiktok_video_id')
        item.error_message = data.get('error_message')
        return item


# ============================================================================
# CLAUDE API INTEGRATION
# ============================================================================

def generate_caption_with_claude(
    topic: str,
    category: str,
    video_title: str,
    context: str = ""
) -> str:
    """
    Generate Vietnamese TikTok caption using Claude API.

    Args:
        topic: Main topic of the video
        category: Content category (news, tutorial, case_study, etc.)
        video_title: Title of the video
        context: Additional context for caption generation

    Returns:
        Generated caption (Vietnamese)
    """

    category_prompts = {
        "news": "Tạo một caption TikTok ngắn gọn, hấp dẫn cho video tin tức AI. Bắt đầu bằng 1 câu gây sốc hoặc câu hỏi. Kết thúc bằng CTA (call-to-action) yêu cầu follow hoặc comment.",
        "tutorial": "Tạo caption cho video hướng dẫn. Bắt đầu bằng lợi ích (benefit). Kêu gọi người xem thử hoặc save video.",
        "case_study": "Tạo caption cho video case study. Bắt đầu bằng kết quả cụ thể (con số, %). Kêu gọi comment hoặc DM để learn thêm.",
        "tool_review": "Tạo caption review tool. Bắt đầu bằng tên tool + 1 cái khác biệt. Kêu gọi comment tool yêu thích của họ.",
        "bts": "Tạo caption behind-the-scenes. Bắt đầu bằng điều relatable hoặc funny. Kêu gọi follow để thấy more behind-the-scenes."
    }

    prompt = f"""Bạn là chuyên gia content TikTok cho thương hiệu AI Thực Chiến (Vietnamese AI automation brand).

Video title: {video_title}
Topic: {topic}
Category: {category}
{f"Additional context: {context}" if context else ""}

{category_prompts.get(category, "Tạo caption TikTok hấp dẫn.")}

Requirements:
- Viết tiếng Việt tự nhiên, không lạc lõng
- Độ dài: 100-200 ký tự (phù hợp TikTok)
- Gồm 1-2 emoji phù hợp
- Bắt đầu với hook mạnh (gây chú ý trong 1-2 giây)
- Kết thúc bằng CTA rõ ràng (follow, comment, save, etc.)
- Tự nhiên, không quá promotional

Chỉ trả lời caption, không giải thích."""

    try:
        global claude_client
        if claude_client is None:
            claude_client = _get_claude_client()
        message = claude_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=256,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        caption = message.content[0].text.strip()
        logger.info(f"Generated caption for '{video_title}'")
        return caption
    except Exception as e:
        logger.error(f"Error generating caption: {e}")
        raise


def generate_hashtags_with_claude(
    topic: str,
    category: str
) -> List[str]:
    """
    Generate relevant Vietnamese + English hashtags using Claude.

    Args:
        topic: Video topic
        category: Content category

    Returns:
        List of hashtags (with # prefix)
    """

    prompt = f"""Tạo danh sách hashtag cho video TikTok.

Topic: {topic}
Category: {category}

Hashtag strategy:
- 2-3 hashtag broad AI (Tier 1): #AI, #ChatGPT, #Automation
- 5-6 hashtag Vietnamese AI specific (Tier 2): #AIThựcChiến, #ChatGPTViệtNam, etc.
- 3-4 hashtag niche specific (Tier 3): depends on category

Total: 10-12 hashtags

Return ONLY hashtags in list format, mỗi dòng 1 hashtag (có # prefix)."""

    try:
        global claude_client
        if claude_client is None:
            claude_client = _get_claude_client()
        message = claude_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=256,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        hashtags_text = message.content[0].text.strip()
        hashtags = [h.strip() for h in hashtags_text.split('\n') if h.strip().startswith('#')]
        logger.info(f"Generated {len(hashtags)} hashtags for topic '{topic}'")
        return hashtags[:12]  # Limit to 12
    except Exception as e:
        logger.error(f"Error generating hashtags: {e}")
        raise


# ============================================================================
# TIKTOK API INTEGRATION
# ============================================================================

class TikTokAPI:
    """Wrapper for TikTok Content Posting API v2.

    Uses the proper 3-step flow:
    1. Initialize upload → get upload_url
    2. Upload video file to upload_url
    3. Video is auto-published after upload completes
    """

    # Max file size for direct upload (50MB). Larger files use chunked upload.
    DIRECT_UPLOAD_MAX = 50 * 1024 * 1024

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json; charset=UTF-8',
        }

    def upload_video(
        self,
        video_path: str,
        caption: str,
        hashtags: List[str],
        scheduled_time: Optional[datetime] = None,
        privacy_level: str = "SELF_ONLY",
    ) -> Dict:
        """Upload video to TikTok using Content Posting API v2.

        Flow: init upload → upload file → auto-publish.

        Args:
            video_path: Path to video file
            caption: Video caption (Vietnamese)
            hashtags: List of hashtags
            scheduled_time: When to post (optional, Unix timestamp)
            privacy_level: SELF_ONLY, MUTUAL_FOLLOW_FRIENDS, FOLLOWER_OF_CREATOR, or PUBLIC_TO_EVERYONE

        Returns:
            Response dict with publish_id
        """
        video_file = Path(video_path)
        if not video_file.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        file_size = video_file.stat().st_size

        # Combine caption and hashtags
        full_caption = caption
        if hashtags:
            full_caption += "\n\n" + " ".join(hashtags)

        # Step 1: Initialize upload
        init_payload = {
            "post_info": {
                "title": full_caption[:150],
                "description": full_caption,
                "privacy_level": privacy_level,
                "disable_comment": False,
                "disable_duet": False,
                "disable_stitch": False,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": file_size,
            },
        }

        if scheduled_time:
            init_payload["post_info"]["schedule_time"] = int(scheduled_time.timestamp())

        logger.info(f"Initializing TikTok upload for: {video_path} ({file_size / (1024*1024):.1f}MB)")

        init_resp = requests.post(
            f"{TIKTOK_API_BASE}/post/publish/video/init/",
            headers=self.headers,
            json=init_payload,
            timeout=30,
        )

        if init_resp.status_code != 200:
            raise Exception(f"TikTok init failed: {init_resp.status_code} - {init_resp.text}")

        init_data = init_resp.json()
        if init_data.get("error", {}).get("code") != "ok":
            raise Exception(f"TikTok init error: {init_data}")

        upload_url = init_data["data"]["upload_url"]
        publish_id = init_data["data"].get("publish_id", "")
        logger.info(f"Got upload URL, publish_id={publish_id}")

        # Step 2: Upload video file (streamed to avoid loading into RAM)
        upload_headers = {
            'Content-Type': 'video/mp4',
            'Content-Length': str(file_size),
        }

        with open(video_path, 'rb') as f:
            upload_resp = requests.put(
                upload_url,
                headers=upload_headers,
                data=f,
                timeout=300,
            )

        if upload_resp.status_code not in [200, 201]:
            raise Exception(f"TikTok upload failed: {upload_resp.status_code} - {upload_resp.text}")

        logger.info(f"Successfully uploaded video to TikTok: {video_path}")

        return {
            "publish_id": publish_id,
            "status": "processing",
            "data": init_data.get("data", {}),
        }

    def check_publish_status(self, publish_id: str) -> Dict:
        """Check the status of a published video."""
        resp = requests.post(
            f"{TIKTOK_API_BASE}/post/publish/status/fetch/",
            headers=self.headers,
            json={"publish_id": publish_id},
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json()
        return {"error": resp.text}

    def get_video_analytics(self, video_id: str) -> Dict:
        """Get analytics for a specific video."""
        endpoint = f"{TIKTOK_API_BASE}/video/query/"
        params = {
            "video_id": video_id,
            "fields": "like_count,comment_count,share_count,view_count,download_count"
        }

        try:
            response = requests.get(
                endpoint,
                headers=self.headers,
                params=params,
                timeout=30,
            )

            if response.status_code == 200:
                logger.info(f"Retrieved analytics for video {video_id}")
                return response.json()
            else:
                logger.error(f"Failed to get analytics: {response.text}")
                return {}
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error getting analytics: {e}")
            return {}


# ============================================================================
# CONTENT QUEUE MANAGEMENT
# ============================================================================

class ContentQueue:
    """Manages content queue for scheduled posting."""

    def __init__(self, queue_file: Path = QUEUE_FILE):
        self.queue_file = queue_file
        self.items: List[ContentItem] = []
        self.load_queue()

    def load_queue(self):
        """Load content queue from JSON file."""
        if self.queue_file.exists():
            try:
                with open(self.queue_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.items = [ContentItem.from_dict(item) for item in data]
                logger.info(f"Loaded {len(self.items)} items from queue")
            except Exception as e:
                logger.error(f"Error loading queue: {e}")
                self.items = []
        else:
            self.items = []

    def save_queue(self):
        """Save content queue to JSON file."""
        try:
            with open(self.queue_file, 'w', encoding='utf-8') as f:
                json.dump([item.to_dict() for item in self.items], f, ensure_ascii=False, indent=2)
            logger.info(f"Saved {len(self.items)} items to queue")
        except Exception as e:
            logger.error(f"Error saving queue: {e}")

    def add_item(self, item: ContentItem):
        """Add item to queue."""
        self.items.append(item)
        self.save_queue()
        logger.info(f"Added '{item.title}' to queue")

    def get_pending_items(self) -> List[ContentItem]:
        """Get all pending items."""
        return [item for item in self.items if item.status == 'pending']

    def get_scheduled_items_due(self) -> List[ContentItem]:
        """Get scheduled items that are due to be posted."""
        now = datetime.now()
        return [
            item for item in self.items
            if item.status == 'scheduled' and item.schedule_time and item.schedule_time <= now
        ]

    def remove_item(self, video_path: str):
        """Remove item from queue by video path."""
        self.items = [item for item in self.items if item.video_path != video_path]
        self.save_queue()
        logger.info(f"Removed item with path: {video_path}")


# ============================================================================
# MAIN POSTER CLASS
# ============================================================================

class TikTokPoster:
    """Main class for posting TikTok content."""

    def __init__(self):
        _validate_tiktok_config()
        self.api = TikTokAPI(TIKTOK_ACCESS_TOKEN)
        self.queue = ContentQueue()
        self.posted_log: List[Dict] = self._load_posted_log()

    def _load_posted_log(self) -> List[Dict]:
        """Load log of posted videos."""
        if POSTED_LOG.exists():
            try:
                with open(POSTED_LOG, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading posted log: {e}")
                return []
        return []

    def _save_posted_log(self):
        """Save posted videos log."""
        try:
            with open(POSTED_LOG, 'w', encoding='utf-8') as f:
                json.dump(self.posted_log, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving posted log: {e}")

    def add_to_queue(
        self,
        video_path: str,
        title: str,
        category: str,
        schedule_time: Optional[datetime] = None,
        hashtags: Optional[List[str]] = None
    ):
        """Add video to queue."""
        item = ContentItem(
            video_path=video_path,
            title=title,
            category=category,
            hashtags=hashtags,
            schedule_time=schedule_time,
            status='scheduled' if schedule_time else 'pending'
        )
        self.queue.add_item(item)
        logger.info(f"Added '{title}' to queue (status: {item.status})")

    def post_video(self, item: ContentItem) -> bool:
        """
        Post a single video to TikTok.

        Args:
            item: ContentItem to post

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Posting video: {item.title}")

            # Generate caption if not provided
            caption = generate_caption_with_claude(
                topic=item.title,
                category=item.category,
                video_title=item.title
            )

            # Generate or use provided hashtags
            if not item.hashtags:
                item.hashtags = generate_hashtags_with_claude(
                    topic=item.title,
                    category=item.category
                )

            # Upload to TikTok
            response = self.api.upload_video(
                video_path=item.video_path,
                caption=caption,
                hashtags=item.hashtags
            )

            # Update item status
            item.status = 'posted'
            item.tiktok_video_id = response.get('data', {}).get('video_id')

            # Log posted video
            self.posted_log.append({
                'title': item.title,
                'video_path': item.video_path,
                'tiktok_video_id': item.tiktok_video_id,
                'category': item.category,
                'posted_at': datetime.now().isoformat(),
                'caption': caption,
                'hashtags': item.hashtags
            })
            self._save_posted_log()

            # Update queue
            self.queue.save_queue()

            logger.info(f"Successfully posted: {item.title}")
            return True

        except Exception as e:
            item.status = 'failed'
            item.error_message = str(e)
            self.queue.save_queue()
            logger.error(f"Failed to post '{item.title}': {e}")
            return False

    def process_queue(self) -> Dict:
        """
        Process all due items in queue.

        Returns:
            Summary of processing results
        """
        results = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'errors': []
        }

        # Process scheduled items that are due
        due_items = self.queue.get_scheduled_items_due()

        for item in due_items:
            results['total_processed'] += 1
            if self.post_video(item):
                results['successful'] += 1
            else:
                results['failed'] += 1
                results['errors'].append({
                    'title': item.title,
                    'error': item.error_message
                })

        logger.info(f"Queue processing complete. Successful: {results['successful']}, Failed: {results['failed']}")
        return results

    def get_queue_status(self) -> Dict:
        """Get current queue status."""
        return {
            'total_items': len(self.queue.items),
            'pending': len(self.queue.get_pending_items()),
            'scheduled': len([i for i in self.queue.items if i.status == 'scheduled']),
            'posted': len([i for i in self.queue.items if i.status == 'posted']),
            'failed': len([i for i in self.queue.items if i.status == 'failed']),
            'next_scheduled': min(
                [i.schedule_time for i in self.queue.items if i.schedule_time],
                default=None
            )
        }


# ============================================================================
# CLI COMMANDS
# ============================================================================

def cmd_add(args):
    """Add video to queue."""
    if not args.video or not args.title or not args.category:
        print("Error: --video, --title, and --category are required")
        sys.exit(1)

    poster = TikTokPoster()

    # Parse schedule time if provided
    schedule_time = None
    if args.schedule:
        try:
            schedule_time = datetime.fromisoformat(args.schedule)
        except ValueError:
            print("Error: Invalid datetime format. Use ISO format: YYYY-MM-DD HH:MM:SS")
            sys.exit(1)

    poster.add_to_queue(
        video_path=args.video,
        title=args.title,
        category=args.category,
        schedule_time=schedule_time
    )

    print(f"✓ Added '{args.title}' to queue")


def cmd_process(args):
    """Process queue and post due videos."""
    poster = TikTokPoster()
    results = poster.process_queue()

    print(f"\nQueue Processing Results:")
    print(f"  Total processed: {results['total_processed']}")
    print(f"  Successful: {results['successful']}")
    print(f"  Failed: {results['failed']}")

    if results['errors']:
        print(f"\nErrors:")
        for error in results['errors']:
            print(f"  - {error['title']}: {error['error']}")


def cmd_status(args):
    """Show queue status."""
    poster = TikTokPoster()
    status = poster.get_queue_status()

    print(f"\nQueue Status:")
    print(f"  Total items: {status['total_items']}")
    print(f"  Pending: {status['pending']}")
    print(f"  Scheduled: {status['scheduled']}")
    print(f"  Posted: {status['posted']}")
    print(f"  Failed: {status['failed']}")

    if status['next_scheduled']:
        print(f"  Next scheduled: {status['next_scheduled']}")


def cmd_generate_caption(args):
    """Generate caption for a video."""
    if not args.topic or not args.category:
        print("Error: --topic and --category are required")
        sys.exit(1)

    caption = generate_caption_with_claude(
        topic=args.topic,
        category=args.category,
        video_title=args.topic
    )

    print(f"\nGenerated Caption:")
    print(caption)


def cmd_generate_hashtags(args):
    """Generate hashtags for a video."""
    if not args.topic or not args.category:
        print("Error: --topic and --category are required")
        sys.exit(1)

    hashtags = generate_hashtags_with_claude(
        topic=args.topic,
        category=args.category
    )

    print(f"\nGenerated Hashtags ({len(hashtags)}):")
    for tag in hashtags:
        print(f"  {tag}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="TikTok Content Poster for AI Thực Chiến",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Add video to queue with schedule
  python tiktok-poster.py add \\
    --video /path/to/video.mp4 \\
    --title "ChatGPT tips for e-commerce" \\
    --category tutorial \\
    --schedule "2024-03-15 12:00:00"

  # Process queue and post due videos
  python tiktok-poster.py process

  # Check queue status
  python tiktok-poster.py status

  # Generate caption
  python tiktok-poster.py gen-caption \\
    --topic "ChatGPT for e-commerce" \\
    --category tutorial
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Add command
    add_parser = subparsers.add_parser('add', help='Add video to queue')
    add_parser.add_argument('--video', required=True, help='Path to video file')
    add_parser.add_argument('--title', required=True, help='Video title')
    add_parser.add_argument('--category', required=True,
                           choices=['news', 'tutorial', 'case_study', 'tool_review', 'bts'],
                           help='Content category')
    add_parser.add_argument('--schedule', help='Schedule time (ISO format: YYYY-MM-DD HH:MM:SS)')
    add_parser.set_defaults(func=cmd_add)

    # Process command
    process_parser = subparsers.add_parser('process', help='Process queue and post videos')
    process_parser.set_defaults(func=cmd_process)

    # Status command
    status_parser = subparsers.add_parser('status', help='Show queue status')
    status_parser.set_defaults(func=cmd_status)

    # Generate caption command
    caption_parser = subparsers.add_parser('gen-caption', help='Generate caption')
    caption_parser.add_argument('--topic', required=True, help='Video topic')
    caption_parser.add_argument('--category', required=True,
                               choices=['news', 'tutorial', 'case_study', 'tool_review', 'bts'],
                               help='Content category')
    caption_parser.set_defaults(func=cmd_generate_caption)

    # Generate hashtags command
    hashtags_parser = subparsers.add_parser('gen-hashtags', help='Generate hashtags')
    hashtags_parser.add_argument('--topic', required=True, help='Video topic')
    hashtags_parser.add_argument('--category', required=True,
                                choices=['news', 'tutorial', 'case_study', 'tool_review', 'bts'],
                                help='Content category')
    hashtags_parser.set_defaults(func=cmd_generate_hashtags)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == '__main__':
    main()
