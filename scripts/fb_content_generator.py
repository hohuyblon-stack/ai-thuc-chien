"""
Content generator for AI Thực Chiến - generates Vietnamese Facebook posts using Claude
"""
import logging
import json
from typing import Optional
from dataclasses import dataclass

import anthropic

import config
from fb_news_fetcher import NewsItem

logger = logging.getLogger(__name__)


@dataclass
class GeneratedPost:
    """Represents a generated Facebook post"""
    content: str
    pillar: str
    news_title: Optional[str] = None
    image_prompt: Optional[str] = None


class ContentGenerator:
    """Generates Vietnamese Facebook posts using Claude API"""

    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-20250514"

    def generate_post(
        self,
        news_item: NewsItem,
        pillar: str,
        feedback: Optional[str] = None,
    ) -> Optional[GeneratedPost]:
        """
        Generate a Facebook post from a news item

        Args:
            news_item: The news item to generate content from
            pillar: Content pillar type (ai_news_hot_take, automation_wins, tool_reviews, behind_the_scenes)
            feedback: Optional quality feedback from previous attempt to improve on

        Returns:
            GeneratedPost object or None if generation fails
        """
        if pillar not in config.SYSTEM_PROMPTS:
            logger.error(f"Unknown content pillar: {pillar}")
            return None

        system_prompt = config.SYSTEM_PROMPTS[pillar]

        # Build the user message with context
        user_message = self._build_user_message(news_item, pillar)

        # Inject quality feedback if this is a retry
        if feedback:
            user_message += (
                f"\n\n--- QUALITY FEEDBACK (improve these) ---\n{feedback}"
            )

        try:
            logger.info(f"Generating {pillar} post from: {news_item.title[:60]}...")

            message = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": user_message,
                    }
                ],
            )

            post_content = message.content[0].text

            # Generate image prompt if needed
            image_prompt = self._generate_image_prompt(news_item, pillar)

            result = GeneratedPost(
                content=post_content,
                pillar=pillar,
                news_title=news_item.title,
                image_prompt=image_prompt,
            )

            logger.info(f"Generated {pillar} post ({len(post_content)} chars)")
            return result

        except anthropic.APIError as e:
            logger.error(f"Claude API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error generating post: {e}")
            return None

    def _build_user_message(self, news_item: NewsItem, pillar: str) -> str:
        """Build the user message for Claude"""
        if pillar == "ai_news_hot_take":
            return f"""Tin tức AI mới nhất:

Tiêu đề: {news_item.title}
Nguồn: {news_item.source}
Chi tiết: {news_item.summary}

Hãy viết bài post Facebook hấp dẫn dựa trên tin tức này, dành cho chủ doanh nghiệp Việt Nam."""

        elif pillar == "automation_wins":
            return f"""Thông tin về một success story automation:

Tiêu đề: {news_item.title}
Nguồn: {news_item.source}
Chi tiết: {news_item.summary}

Hãy viết bài post case study về thành công khi dùng AI/Automation."""

        elif pillar == "tool_reviews":
            return f"""Thông tin về một AI tool mới:

Tên tool: {news_item.title}
Nguồn: {news_item.source}
Chi tiết: {news_item.summary}

Hãy viết bài review tool này cho business owners Việt Nam."""

        else:  # behind_the_scenes
            return f"""Thông tin thú vị:

{news_item.title}
Nguồn: {news_item.source}
Chi tiết: {news_item.summary}

Hãy kể một câu chuyện behind-the-scenes thú vị dựa trên thông tin này, chia sẻ kinh nghiệm và bài học."""

    def _generate_image_prompt(self, news_item: NewsItem, pillar: str) -> str:
        """Generate a prompt for image creation (optional visual enhancement)"""
        base_topic = news_item.title[:50]

        if pillar == "ai_news_hot_take":
            return f"Modern, professional design: AI technology, innovation, Vietnamese business context. Topic: {base_topic}. Use blues, greens, whites. Vietnamese style."

        elif pillar == "automation_wins":
            return f"Success story visualization: growth chart, happy entrepreneur, automation workflow. Topic: {base_topic}. Use greens, golds. Vietnamese style."

        elif pillar == "tool_reviews":
            return f"Tool showcase: sleek interface, dashboard, Vietnamese e-commerce seller using it. Topic: {base_topic}. Modern, minimalist design."

        else:  # behind_the_scenes
            return f"Behind the scenes: office, team, process, authentic Vietnamese business environment. Topic: {base_topic}. Warm, inviting tone."

    def generate_multiple_variations(
        self,
        news_item: NewsItem,
        pillar: str,
        num_variations: int = 1,
    ) -> list:
        """Generate multiple variations of a post for A/B testing"""
        posts = []

        for i in range(num_variations):
            post = self.generate_post(news_item, pillar)
            if post:
                posts.append(post)

        logger.info(f"✓ Generated {len(posts)} variations")
        return posts


def load_post_from_file(file_path: str) -> Optional[GeneratedPost]:
    """Load a generated post from a JSON file (for testing)"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return GeneratedPost(
            content=data["content"],
            pillar=data["pillar"],
            news_title=data.get("news_title"),
            image_prompt=data.get("image_prompt"),
        )
    except Exception as e:
        logger.error(f"Error loading post from file: {e}")
        return None


if __name__ == "__main__":
    # Test the generator
    logging.basicConfig(level=logging.INFO)

    # Create a sample news item for testing
    sample_news = NewsItem(
        title="OpenAI Released GPT-5 - Game Changer for Vietnamese Businesses",
        summary="OpenAI announced GPT-5 with improved Vietnamese language support and better understanding of local business contexts. The model can now generate more accurate content for Vietnamese e-commerce sellers.",
        source="TechCrunch",
        url="https://example.com",
        relevance_score=0.95,
    )

    generator = ContentGenerator(api_key=config.CLAUDE_API_KEY)

    for pillar in config.CONTENT_PILLARS.keys():
        print(f"\n{'=' * 60}")
        print(f"Pillar: {pillar}")
        print("=" * 60)

        post = generator.generate_post(sample_news, pillar)
        if post:
            print(post.content)
            print(f"\n📸 Image Prompt: {post.image_prompt}")
        else:
            print("Failed to generate post")
