#!/usr/bin/env python3
"""
AI Thực Chiến - Facebook Daily Posting Automation
Main automation script that orchestrates news fetching, content generation, and posting
"""
import logging
import json
import os
import sys
import time
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import hashlib

import requests
from dotenv import load_dotenv

import config
from fb_news_fetcher import NewsFetcher, NewsItem
from fb_content_generator import ContentGenerator, GeneratedPost
from quality_loop import AgentLoop, FacebookPostEvaluator

# ============================================================================
# SETUP
# ============================================================================
load_dotenv()

# Create directories
Path(config.LOG_DIR).mkdir(parents=True, exist_ok=True)
Path(config.DATA_DIR).mkdir(parents=True, exist_ok=True)

# Configure logging
log_file = os.path.join(config.LOG_DIR, f"autoposter_{datetime.now().strftime('%Y%m%d')}.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger(__name__)


# ============================================================================
# HISTORY MANAGEMENT
# ============================================================================
class PostHistory:
    """Manages post history to avoid duplicates"""

    def __init__(self, history_file: str):
        self.history_file = history_file
        self.posts = self._load_history()

    def _load_history(self) -> list:
        """Load history from file"""
        if not os.path.exists(self.history_file):
            return []

        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading history: {e}")
            return []

    def _save_history(self):
        """Save history to file"""
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(self.posts, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving history: {e}")

    def add_post(self, news_title: str, post_content: str, pillar: str, facebook_post_id: str):
        """Add a post to history"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "news_title": news_title,
            "pillar": pillar,
            "content_hash": hashlib.md5(post_content.encode()).hexdigest(),
            "facebook_post_id": facebook_post_id,
        }
        self.posts.append(entry)
        self._save_history()
        logger.info(f"✓ Added post to history (total: {len(self.posts)})")

    def has_similar_post(self, news_title: str, max_days: int = 7) -> bool:
        """Check if a similar post exists in recent history"""
        cutoff_date = datetime.now() - timedelta(days=max_days)

        for post in self.posts:
            try:
                post_date = datetime.fromisoformat(post["timestamp"])
                if post_date > cutoff_date and post["news_title"].lower() == news_title.lower():
                    logger.warning(f"Similar post found in history: {post['news_title']}")
                    return True
            except Exception as e:
                logger.error(f"Error checking history: {e}")

        return False

    def get_stats(self) -> dict:
        """Get history statistics"""
        total = len(self.posts)
        pillars = {}

        for post in self.posts:
            pillar = post.get("pillar", "unknown")
            pillars[pillar] = pillars.get(pillar, 0) + 1

        return {"total_posts": total, "by_pillar": pillars}


# ============================================================================
# FACEBOOK API
# ============================================================================
class FacebookPoster:
    """Posts content to Facebook Page"""

    def __init__(self, page_id: str, access_token: str):
        self.page_id = page_id
        self.access_token = access_token
        self.base_url = f"{config.FACEBOOK_GRAPH_URL}/{page_id}/feed"

    def post_with_retry(self, message: str, max_retries: int = config.MAX_RETRIES) -> Optional[str]:
        """Post message to Facebook with retry logic"""
        for attempt in range(max_retries):
            try:
                logger.info(f"Posting to Facebook (attempt {attempt + 1}/{max_retries})...")

                response = requests.post(
                    self.base_url,
                    params={
                        "message": message,
                        "access_token": self.access_token,
                    },
                    timeout=30,
                )

                if response.status_code == 200:
                    post_id = response.json().get("id")
                    logger.info(f"✓ Post published successfully: {post_id}")
                    return post_id

                elif response.status_code == 400:
                    error_data = response.json()
                    logger.error(f"Bad request: {error_data}")
                    return None

                elif response.status_code == 401:
                    logger.error("Authentication failed - check access token")
                    return None

                elif response.status_code == 429:
                    # Rate limited
                    wait_time = config.RETRY_DELAY_SECONDS * (2 ** attempt)
                    logger.warning(f"Rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue

                else:
                    logger.warning(
                        f"HTTP {response.status_code}: {response.text[:200]}. Retrying..."
                    )
                    time.sleep(config.RETRY_DELAY_SECONDS * (2 ** attempt))
                    continue

            except requests.exceptions.Timeout:
                logger.warning(f"Timeout on attempt {attempt + 1}, retrying...")
                time.sleep(config.RETRY_DELAY_SECONDS * (2 ** attempt))

            except Exception as e:
                logger.error(f"Error posting: {e}")
                time.sleep(config.RETRY_DELAY_SECONDS * (2 ** attempt))

        logger.error("Failed to post after all retries")
        return None


# ============================================================================
# MAIN AUTOMATION
# ============================================================================
class FacebookAutoPoster:
    """Main orchestrator for Facebook automation"""

    def __init__(self):
        # Validate configuration
        if not config.validate_config():
            raise ValueError("Configuration validation failed")

        self.news_fetcher = NewsFetcher(tavily_api_key=config.TAVILY_API_KEY)
        self.content_generator = ContentGenerator(api_key=config.CLAUDE_API_KEY)
        self.facebook_poster = FacebookPoster(
            page_id=config.FACEBOOK_PAGE_ID,
            access_token=config.FACEBOOK_ACCESS_TOKEN,
        )
        self.history = PostHistory(config.HISTORY_FILE)

        logger.info("✓ FacebookAutoPoster initialized")

    def select_content_pillar(self) -> str:
        """Randomly select content pillar based on weights"""
        pillars = list(config.CONTENT_PILLARS.keys())
        weights = [config.CONTENT_PILLARS[p] for p in pillars]
        selected = random.choices(pillars, weights=weights, k=1)[0]
        logger.info(f"✓ Selected pillar: {selected}")
        return selected

    def run(self) -> bool:
        """Run the full automation pipeline"""
        logger.info("=" * 80)
        logger.info("STARTING FACEBOOK AUTOPOSTER")
        logger.info("=" * 80)

        try:
            # Step 1: Fetch news
            logger.info("\n📰 FETCHING NEWS...")
            news_item = self.news_fetcher.get_news_for_post()

            if not news_item:
                logger.error("No news found, aborting")
                return False

            # Step 2: Check history to avoid duplicates
            logger.info("\n📚 CHECKING HISTORY...")
            if self.history.has_similar_post(news_item.title, max_days=7):
                logger.warning("Similar post found in recent history, skipping")
                return False

            # Step 3: Select content pillar
            logger.info("\n🎯 SELECTING CONTENT PILLAR...")
            pillar = self.select_content_pillar()

            # Step 4: Generate content (with agent loop quality evaluation)
            logger.info("\n GENERATING CONTENT (agent loop)...")

            fb_evaluator = FacebookPostEvaluator()

            def _generate_fb(ctx, feedback=None):
                return self.content_generator.generate_post(
                    ctx["news_item"], ctx["pillar"], feedback=feedback
                )

            def _evaluate_fb(output, ctx):
                if output is None:
                    from quality_loop import EvalResult
                    return EvalResult(score=0, passed=False,
                                      hard_fail_reasons=["Generation returned None"])
                return fb_evaluator.evaluate(output.content, {"pillar": ctx["pillar"]})

            fb_loop = AgentLoop(max_retries=3, threshold=7.0, name="fb_post_gen")
            fb_result = fb_loop.run(
                _generate_fb, _evaluate_fb,
                {"news_item": news_item, "pillar": pillar},
            )

            post = fb_result.output
            if not post:
                logger.error("Content generation failed on all attempts, aborting")
                return False

            logger.info(
                f"Post accepted: score={fb_result.final_score:.1f}/10, "
                f"attempts={fb_result.attempts}, accepted={fb_result.accepted}"
            )

            # Step 5: Display preview
            logger.info("\n POST PREVIEW:")
            logger.info("-" * 80)
            logger.info(post.content)
            logger.info("-" * 80)

            # Step 6: Post to Facebook
            logger.info("\n📤 POSTING TO FACEBOOK...")
            post_id = self.facebook_poster.post_with_retry(post.content)

            if not post_id:
                logger.error("Failed to post to Facebook")
                return False

            # Step 7: Record in history
            logger.info("\n📝 RECORDING HISTORY...")
            self.history.add_post(
                news_title=news_item.title,
                post_content=post.content,
                pillar=pillar,
                facebook_post_id=post_id,
            )

            # Step 8: Show stats
            logger.info("\n📊 HISTORY STATS:")
            stats = self.history.get_stats()
            logger.info(f"Total posts: {stats['total_posts']}")
            for pillar, count in stats["by_pillar"].items():
                logger.info(f"  {pillar}: {count}")

            logger.info("\n✓ AUTOPOSTER RUN COMPLETED SUCCESSFULLY")
            logger.info("=" * 80)

            return True

        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            return False

    def run_on_schedule(self):
        """Run on a schedule (for continuous operation)"""
        logger.info("Starting scheduled mode - will run once daily")

        while True:
            now = datetime.now()
            current_hour = now.hour

            # Check if we're in the posting window (1-4pm Vietnam time)
            if config.POST_WINDOW_START <= current_hour < config.POST_WINDOW_END:
                # Run with some randomness to avoid exact hour boundaries
                random_minute = random.randint(0, 59)

                if now.minute == random_minute:
                    logger.info(f"Posting time reached! Running at {now.strftime('%H:%M')}")
                    success = self.run()

                    if success:
                        logger.info("Post successful, sleeping until tomorrow")
                        # Sleep for 24 hours
                        time.sleep(86400)
                    else:
                        logger.warning("Post failed, will retry in 1 hour")
                        time.sleep(3600)

            # Check every minute
            time.sleep(60)


# ============================================================================
# CLI
# ============================================================================
def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="AI Thực Chiến Facebook Autoposter")
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="Run once and exit (default)",
    )
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Run on schedule (continuous operation)",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test mode - don't actually post to Facebook",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show post history stats",
    )

    args = parser.parse_args()

    try:
        autoposter = FacebookAutoPoster()

        if args.stats:
            stats = autoposter.history.get_stats()
            print("\n📊 POST HISTORY STATISTICS")
            print(f"Total posts: {stats['total_posts']}")
            print("\nBreakdown by pillar:")
            for pillar, count in stats["by_pillar"].items():
                print(f"  {pillar}: {count}")
            return 0

        if args.schedule:
            autoposter.run_on_schedule()
        else:
            # Default: run once
            success = autoposter.run()
            return 0 if success else 1

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        print("\n❌ Configuration error. Please set environment variables:")
        print("   - FACEBOOK_PAGE_ID")
        print("   - FACEBOOK_ACCESS_TOKEN")
        print("   - CLAUDE_API_KEY")
        print("   - TAVILY_API_KEY")
        return 1

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 0

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
