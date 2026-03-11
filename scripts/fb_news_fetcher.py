"""
News fetcher for AI Thực Chiến - fetches AI news from multiple sources
"""
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime
import json
import requests

try:
    from tavily import TavilyClient
except ImportError:
    TavilyClient = None

try:
    import feedparser
except ImportError:
    feedparser = None

import config

logger = logging.getLogger(__name__)


@dataclass
class NewsItem:
    """Represents a news item for content generation"""
    title: str
    summary: str
    source: str
    url: str
    published_date: Optional[str] = None
    relevance_score: float = 0.8


class NewsFetcher:
    """Fetches AI news from Tavily API and RSS feeds"""

    def __init__(self, tavily_api_key: str):
        self.tavily_api_key = tavily_api_key
        self.tavily_client = None

        if TavilyClient:
            try:
                self.tavily_client = TavilyClient(api_key=tavily_api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize Tavily client: {e}")

    def fetch_tavily_news(self, query: str = "AI news automation") -> List[NewsItem]:
        """Fetch news from Tavily API"""
        if not self.tavily_client:
            logger.warning("Tavily client not available, skipping Tavily fetch")
            return []

        try:
            response = self.tavily_client.search(
                query=query,
                search_depth="basic",
                max_results=5,
                include_raw_content=False,
            )

            items = []
            for result in response.get("results", []):
                item = NewsItem(
                    title=result.get("title", ""),
                    summary=result.get("content", "")[:500],  # Truncate to 500 chars
                    source=result.get("source", "Unknown"),
                    url=result.get("url", ""),
                    published_date=datetime.now().isoformat(),
                    relevance_score=0.9,  # Tavily results are usually relevant
                )
                items.append(item)

            logger.info(f"✓ Fetched {len(items)} items from Tavily")
            return items

        except Exception as e:
            logger.error(f"Error fetching from Tavily: {e}")
            return []

    def fetch_rss_news(self, feeds: List[str]) -> List[NewsItem]:
        """Fetch news from RSS feeds"""
        if not feedparser:
            logger.warning("feedparser not available, skipping RSS fetch")
            return []

        items = []

        for feed_url in feeds:
            try:
                feed = feedparser.parse(feed_url)

                # Take only the 5 most recent entries
                for entry in feed.entries[:5]:
                    # Extract summary
                    summary = entry.get("summary", "") or entry.get("description", "")
                    if isinstance(summary, str):
                        summary = summary[:500]  # Truncate

                    item = NewsItem(
                        title=entry.get("title", ""),
                        summary=summary,
                        source=feed.feed.get("title", "Unknown Feed"),
                        url=entry.get("link", ""),
                        published_date=entry.get("published", datetime.now().isoformat()),
                        relevance_score=0.7,  # RSS feeds may be less targeted
                    )
                    items.append(item)

                logger.info(f"✓ Fetched entries from {feed_url}")

            except Exception as e:
                logger.error(f"Error fetching RSS from {feed_url}: {e}")
                continue

        logger.info(f"✓ Fetched {len(items)} items from RSS feeds")
        return items

    def fetch_all_news(self, tavily_query: str = "AI news automation") -> List[NewsItem]:
        """Fetch news from all sources"""
        logger.info("Fetching news from all sources...")

        all_items = []

        # Try Tavily first
        tavily_items = self.fetch_tavily_news(tavily_query)
        all_items.extend(tavily_items)

        # Fall back to RSS if Tavily is empty or fails
        if not all_items:
            logger.info("Tavily returned no results, using RSS feeds as fallback")
            rss_items = self.fetch_rss_news(config.RSS_FEEDS)
            all_items.extend(rss_items)

        # Remove duplicates by title
        seen_titles = set()
        unique_items = []
        for item in all_items:
            if item.title not in seen_titles:
                seen_titles.add(item.title)
                unique_items.append(item)

        logger.info(f"✓ Total unique items: {len(unique_items)}")
        return unique_items

    def filter_relevant_news(self, items: List[NewsItem], min_score: float = 0.6) -> List[NewsItem]:
        """Filter news by relevance score"""
        filtered = [item for item in items if item.relevance_score >= min_score]
        logger.info(f"✓ Filtered to {len(filtered)} relevant items (score >= {min_score})")
        return filtered

    def get_news_for_post(self) -> Optional[NewsItem]:
        """Get a single news item for posting"""
        all_news = self.fetch_all_news()

        if not all_news:
            logger.error("No news items found")
            return None

        # Return the first (most recent) item
        selected = all_news[0]
        logger.info(f"✓ Selected news: {selected.title}")
        return selected


def load_news_from_file(file_path: str) -> List[NewsItem]:
    """Load news from a JSON file (for testing)"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        items = [
            NewsItem(
                title=item["title"],
                summary=item["summary"],
                source=item["source"],
                url=item.get("url", ""),
                published_date=item.get("published_date"),
                relevance_score=item.get("relevance_score", 0.8),
            )
            for item in data
        ]
        return items
    except Exception as e:
        logger.error(f"Error loading news from file: {e}")
        return []


if __name__ == "__main__":
    # Test the fetcher
    logging.basicConfig(level=logging.INFO)

    fetcher = NewsFetcher(tavily_api_key=config.TAVILY_API_KEY)
    news = fetcher.get_news_for_post()

    if news:
        print("\n" + "=" * 60)
        print(f"Title: {news.title}")
        print(f"Source: {news.source}")
        print(f"Summary: {news.summary[:200]}...")
        print("=" * 60)
    else:
        print("No news found")
