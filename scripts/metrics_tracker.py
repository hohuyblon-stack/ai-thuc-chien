#!/usr/bin/env python3
"""
Metrics Tracker for AI Thực Chiến

Tracks pipeline performance + engagement metrics to close the feedback loop.
This is the "learning" part of the agent loop — what worked? what didn't?

Feeds insights back into script generation via program.md rules.

Usage:
    # Record pipeline run metrics
    tracker = MetricsTracker()
    tracker.record_pipeline_run(pipeline_results)

    # Fetch YouTube engagement (run daily via cron)
    tracker.fetch_youtube_engagement()

    # Get insights for next generation
    insights = tracker.get_content_insights()
"""

import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

PROJECT_DIR = Path(__file__).parent.parent
METRICS_DIR = PROJECT_DIR / "data" / "metrics"
METRICS_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# Data Types
# ============================================================================

@dataclass
class PipelineMetrics:
    """Metrics from a single pipeline run."""
    date: str
    format_type: str
    platforms: List[str]
    status: str  # success / partial / failed

    # Quality scores from agent loop
    script_score: float = 0.0
    script_attempts: int = 1
    script_accepted: bool = True

    # Cost tracking
    cost_replicate: float = 0.0
    cost_claude_api: float = 0.0
    cost_total: float = 0.0

    # Timing
    duration_news_sec: float = 0.0
    duration_script_sec: float = 0.0
    duration_tts_sec: float = 0.0
    duration_avatar_sec: float = 0.0
    duration_compose_sec: float = 0.0
    duration_total_sec: float = 0.0

    # Output info
    video_duration_sec: float = 0.0
    script_word_count: int = 0
    title: str = ""
    youtube_id: Optional[str] = None
    tiktok_id: Optional[str] = None


@dataclass
class EngagementMetrics:
    """Engagement data for a published video."""
    date: str
    platform: str  # youtube / tiktok
    video_id: str
    title: str

    # Engagement numbers
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    watch_time_hours: float = 0.0
    avg_view_duration_sec: float = 0.0
    click_through_rate: float = 0.0

    # Derived
    engagement_rate: float = 0.0  # (likes + comments + shares) / views


# ============================================================================
# Metrics Tracker
# ============================================================================

class MetricsTracker:
    """Tracks pipeline and engagement metrics over time."""

    def __init__(self):
        self.pipeline_file = METRICS_DIR / "pipeline_metrics.json"
        self.engagement_file = METRICS_DIR / "engagement_metrics.json"
        self.insights_file = METRICS_DIR / "content_insights.json"

    def _load_json(self, path: Path) -> list:
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return []
        return []

    def _save_json(self, path: Path, data: list):
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    # ---- Pipeline Metrics ----

    def record_pipeline_run(self, results: dict, script_data: dict = None):
        """Record metrics from a pipeline run."""
        metrics = PipelineMetrics(
            date=datetime.now().strftime("%Y-%m-%d"),
            format_type=results.get("format", "long"),
            platforms=results.get("platforms", []),
            status=results.get("status", "unknown"),
            title=script_data.get("title", "") if script_data else "",
            youtube_id=results.get("youtube_id"),
            tiktok_id=results.get("tiktok_publish_id"),
        )

        # Extract eval data if present
        if script_data and "_eval" in script_data:
            ev = script_data["_eval"]
            metrics.script_score = ev.get("score", 0)
            metrics.script_attempts = ev.get("attempts", 1)
            metrics.script_accepted = ev.get("accepted", True)

        # Word count
        if script_data and "script" in script_data:
            metrics.script_word_count = len(script_data["script"].split())

        history = self._load_json(self.pipeline_file)
        history.append(asdict(metrics))
        # Keep last 90 days
        history = history[-90:]
        self._save_json(self.pipeline_file, history)
        logger.info(f"Recorded pipeline metrics: {metrics.date} | score={metrics.script_score}")

    # ---- Engagement Metrics ----

    def fetch_youtube_engagement(self, days: int = 7) -> List[Dict]:
        """Fetch YouTube engagement metrics for recent videos.

        Requires YouTube Analytics API access (youtube.readonly scope).
        """
        try:
            import google.auth.transport.requests
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
        except ImportError:
            logger.warning("google-api-python-client not installed, skipping engagement fetch")
            return []

        token_path = PROJECT_DIR / "youtube_token.json"
        if not token_path.exists():
            logger.warning("YouTube token not found, skipping engagement fetch")
            return []

        try:
            creds = Credentials.from_authorized_user_file(
                str(token_path),
                scopes=["https://www.googleapis.com/auth/youtube.readonly"],
            )
            if creds.expired and creds.refresh_token:
                creds.refresh(google.auth.transport.requests.Request())

            youtube = build("youtube", "v3", credentials=creds)

            # Get recent uploads from pipeline history
            pipeline_history = self._load_json(self.pipeline_file)
            recent_ids = [
                h["youtube_id"] for h in pipeline_history[-days:]
                if h.get("youtube_id")
            ]

            if not recent_ids:
                logger.info("No recent YouTube uploads to check")
                return []

            # Fetch stats for each video
            engagement_data = []
            for video_id in recent_ids:
                try:
                    resp = youtube.videos().list(
                        part="statistics,snippet",
                        id=video_id,
                    ).execute()

                    if resp.get("items"):
                        item = resp["items"][0]
                        stats = item.get("statistics", {})
                        snippet = item.get("snippet", {})

                        em = EngagementMetrics(
                            date=datetime.now().strftime("%Y-%m-%d"),
                            platform="youtube",
                            video_id=video_id,
                            title=snippet.get("title", ""),
                            views=int(stats.get("viewCount", 0)),
                            likes=int(stats.get("likeCount", 0)),
                            comments=int(stats.get("commentCount", 0)),
                        )
                        if em.views > 0:
                            em.engagement_rate = (em.likes + em.comments) / em.views
                        engagement_data.append(asdict(em))

                except Exception as e:
                    logger.warning(f"Failed to fetch stats for {video_id}: {e}")

            # Save
            history = self._load_json(self.engagement_file)
            history.extend(engagement_data)
            history = history[-180:]  # Keep 6 months
            self._save_json(self.engagement_file, history)

            return engagement_data

        except Exception as e:
            logger.error(f"YouTube engagement fetch failed: {e}")
            return []

    # ---- Content Insights (feedback loop) ----

    def get_content_insights(self) -> dict:
        """Analyze metrics to generate insights for next content generation.

        This closes the agent loop — past performance feeds into future generation.
        """
        pipeline_history = self._load_json(self.pipeline_file)
        engagement_history = self._load_json(self.engagement_file)

        insights = {
            "generated_at": datetime.now().isoformat(),
            "pipeline_stats": {},
            "engagement_stats": {},
            "recommendations": [],
        }

        if not pipeline_history:
            insights["recommendations"].append("No pipeline history yet. Run the pipeline first.")
            return insights

        # Pipeline stats (last 30 days)
        recent = pipeline_history[-30:]
        scores = [h.get("script_score", 0) for h in recent if h.get("script_score")]
        attempts = [h.get("script_attempts", 1) for h in recent]

        insights["pipeline_stats"] = {
            "total_runs": len(recent),
            "success_rate": sum(1 for h in recent if h["status"] == "success") / max(len(recent), 1),
            "avg_script_score": sum(scores) / max(len(scores), 1) if scores else 0,
            "avg_attempts": sum(attempts) / max(len(attempts), 1),
            "total_cost": sum(h.get("cost_total", 0) for h in recent),
        }

        # Engagement stats
        if engagement_history:
            recent_eng = engagement_history[-30:]
            views = [h.get("views", 0) for h in recent_eng]
            eng_rates = [h.get("engagement_rate", 0) for h in recent_eng if h.get("views", 0) > 0]

            insights["engagement_stats"] = {
                "total_views": sum(views),
                "avg_views": sum(views) / max(len(views), 1),
                "avg_engagement_rate": sum(eng_rates) / max(len(eng_rates), 1),
                "best_video": max(recent_eng, key=lambda x: x.get("views", 0), default={}),
                "worst_video": min(
                    [h for h in recent_eng if h.get("views", 0) > 0],
                    key=lambda x: x.get("views", 0),
                    default={},
                ),
            }

            # Recommendations based on data
            avg_views = insights["engagement_stats"]["avg_views"]
            best = insights["engagement_stats"].get("best_video", {})
            if best.get("views", 0) > avg_views * 2:
                insights["recommendations"].append(
                    f"Video '{best.get('title', '')}' got {best['views']} views "
                    f"(2x+ average). Consider follow-up content on this topic."
                )

        # Quality recommendations
        avg_score = insights["pipeline_stats"].get("avg_script_score", 0)
        if avg_score < 7.0:
            insights["recommendations"].append(
                f"Average script score is {avg_score:.1f}/10. "
                "Consider adjusting prompts or adding more examples to program.md."
            )

        avg_att = insights["pipeline_stats"].get("avg_attempts", 1)
        if avg_att > 2.0:
            insights["recommendations"].append(
                f"Scripts need {avg_att:.1f} attempts on average. "
                "Consider relaxing thresholds or improving the base prompt."
            )

        self._save_json(self.insights_file, insights)
        return insights

    def get_feedback_for_generation(self) -> str:
        """Get a concise feedback string to inject into script generation.

        This is the key feedback loop: past engagement → future content.
        """
        insights = self.get_content_insights()
        parts = []

        # Best performing content
        best = insights.get("engagement_stats", {}).get("best_video", {})
        if best.get("title"):
            parts.append(f"Top performing video: '{best['title']}' ({best.get('views', 0)} views)")

        # Recommendations
        for rec in insights.get("recommendations", [])[:2]:
            parts.append(rec)

        return "\n".join(parts) if parts else ""


# ============================================================================
# CLI — run engagement fetch manually
# ============================================================================

if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    parser = argparse.ArgumentParser(description="Metrics tracker for AI Thực Chiến")
    parser.add_argument("--fetch-engagement", action="store_true",
                        help="Fetch YouTube engagement metrics")
    parser.add_argument("--insights", action="store_true",
                        help="Generate content insights report")
    parser.add_argument("--days", type=int, default=7,
                        help="Number of days to look back")
    args = parser.parse_args()

    tracker = MetricsTracker()

    if args.fetch_engagement:
        data = tracker.fetch_youtube_engagement(days=args.days)
        print(f"Fetched engagement for {len(data)} videos")
        for d in data:
            print(f"  {d['title']}: {d['views']} views, {d['engagement_rate']:.2%} engagement")

    if args.insights or not args.fetch_engagement:
        insights = tracker.get_content_insights()
        print(json.dumps(insights, indent=2, ensure_ascii=False, default=str))
