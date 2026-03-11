#!/usr/bin/env python3
"""
TikTok Script Generator
Generates Vietnamese TikTok scripts optimized for 15-60 second format.
Includes hooks, structure, timing, and content recommendations.

Author: AI Thực Chiến
License: MIT
"""

import os
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
import anthropic
from dotenv import load_dotenv

# ============================================================================
# CONFIGURATION & SETUP
# ============================================================================

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tiktok_script_generator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# API Configuration
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY') or os.getenv('CLAUDE_API_KEY')

if not ANTHROPIC_API_KEY:
    logger.error("ANTHROPIC_API_KEY (or CLAUDE_API_KEY) not found in environment variables")
    sys.exit(1)

# Initialize Claude client
claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Script output directory
SCRIPTS_DIR = Path(__file__).parent.parent / "generated_scripts"
SCRIPTS_DIR.mkdir(exist_ok=True)


# ============================================================================
# DATA MODELS
# ============================================================================

class TikTokScript:
    """Represents a complete TikTok script with all components."""

    def __init__(
        self,
        topic: str,
        category: str,
        hook: str,
        hook_duration: int,
        setup: str,
        setup_duration: int,
        value: str,
        value_duration: int,
        cta: str,
        cta_duration: int,
        total_duration: int,
        caption: str,
        hashtags: List[str],
        trending_sounds: List[str],
        format_type: str,
        visual_notes: str,
        editing_tips: str
    ):
        self.topic = topic
        self.category = category
        self.hook = hook
        self.hook_duration = hook_duration
        self.setup = setup
        self.setup_duration = setup_duration
        self.value = value
        self.value_duration = value_duration
        self.cta = cta
        self.cta_duration = cta_duration
        self.total_duration = total_duration
        self.caption = caption
        self.hashtags = hashtags
        self.trending_sounds = trending_sounds
        self.format_type = format_type
        self.visual_notes = visual_notes
        self.editing_tips = editing_tips
        self.created_at = datetime.now()

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'topic': self.topic,
            'category': self.category,
            'hook': self.hook,
            'hook_duration_seconds': self.hook_duration,
            'setup': self.setup,
            'setup_duration_seconds': self.setup_duration,
            'value': self.value,
            'value_duration_seconds': self.value_duration,
            'cta': self.cta,
            'cta_duration_seconds': self.cta_duration,
            'total_duration_seconds': self.total_duration,
            'caption': self.caption,
            'hashtags': self.hashtags,
            'trending_sounds': self.trending_sounds,
            'format_type': self.format_type,
            'visual_notes': self.visual_notes,
            'editing_tips': self.editing_tips,
            'created_at': self.created_at.isoformat()
        }

    def to_markdown(self) -> str:
        """Convert to markdown format for easy reading."""
        markdown = f"""# TikTok Video Script: {self.topic}

## Metadata
- **Category**: {self.category}
- **Format**: {self.format_type}
- **Total Duration**: {self.total_duration} seconds
- **Created**: {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}

## Script Structure

### 🎯 Hook (0-{self.hook_duration}s)
**Duration**: {self.hook_duration} seconds
```
{self.hook}
```

### 📋 Setup ({self.hook_duration}-{self.hook_duration + self.setup_duration}s)
**Duration**: {self.setup_duration} seconds
```
{self.setup}
```

### 💡 Value Delivery ({self.hook_duration + self.setup_duration}-{self.hook_duration + self.setup_duration + self.value_duration}s)
**Duration**: {self.value_duration} seconds
```
{self.value}
```

### 🚀 Call-to-Action ({self.total_duration - self.cta_duration}-{self.total_duration}s)
**Duration**: {self.cta_duration} seconds
```
{self.cta}
```

## Caption
```
{self.caption}
```

## Hashtags ({len(self.hashtags)} total)
{' | '.join(self.hashtags)}

## Recommended Sounds/Music
{chr(10).join([f"- {sound}" for sound in self.trending_sounds])}

## Visual & Editing Notes
{self.visual_notes}

## Editing Tips
{self.editing_tips}

---
"""
        return markdown

    def save_to_file(self, filename: Optional[str] = None) -> Path:
        """Save script to file."""
        if not filename:
            sanitized_topic = "".join(c if c.isalnum() or c in (' ', '-', '_') else '' for c in self.topic)
            timestamp = self.created_at.strftime('%Y%m%d_%H%M%S')
            filename = f"{sanitized_topic}_{timestamp}.json"

        filepath = SCRIPTS_DIR / filename
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
            logger.info(f"Saved script to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Error saving script: {e}")
            raise

    def save_markdown(self, filename: Optional[str] = None) -> Path:
        """Save script as markdown."""
        if not filename:
            sanitized_topic = "".join(c if c.isalnum() or c in (' ', '-', '_') else '' for c in self.topic)
            timestamp = self.created_at.strftime('%Y%m%d_%H%M%S')
            filename = f"{sanitized_topic}_{timestamp}.md"

        filepath = SCRIPTS_DIR / filename
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(self.to_markdown())
            logger.info(f"Saved markdown script to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Error saving markdown: {e}")
            raise


# ============================================================================
# CLAUDE API INTEGRATION FOR SCRIPT GENERATION
# ============================================================================

def generate_tiktok_script(
    topic: str,
    category: str,
    duration: int = 30
) -> TikTokScript:
    """
    Generate a complete TikTok script using Claude API.

    Args:
        topic: Main topic/subject of the video
        category: Content category (news, tutorial, case_study, tool_review, bts)
        duration: Target duration in seconds (15-60)

    Returns:
        TikTokScript object with complete script
    """

    category_details = {
        "news": {
            "description": "AI news, product announcements, trending updates",
            "tone": "excited, informative, authority",
            "structure": "Hook with breaking news → Explain what happened → Impact/why it matters → Call to action"
        },
        "tutorial": {
            "description": "Step-by-step guides, how-to content, templates",
            "tone": "helpful, clear, energetic",
            "structure": "Hook with benefit → Setup/context → Step-by-step value → CTA to try it"
        },
        "case_study": {
            "description": "Real results, business transformations, success stories",
            "tone": "inspiring, credible, specific",
            "structure": "Hook with results → Problem statement → Solution applied → Results breakdown → CTA"
        },
        "tool_review": {
            "description": "Tool demonstrations, feature reviews, comparisons",
            "tone": "honest, practical, slightly casual",
            "structure": "Hook (what's new/impressive) → Demo/feature walkthrough → Pros/cons → Recommendation → Link"
        },
        "bts": {
            "description": "Behind-the-scenes, day-in-life, casual/funny content",
            "tone": "authentic, relatable, conversational",
            "structure": "Hook with relatable situation → Show reality → Lesson/insight → CTA (follow for more)"
        }
    }

    category_info = category_details.get(category, category_details['tutorial'])

    prompt = f"""Bạn là chuyên gia TikTok content creator cho thương hiệu AI Thực Chiến.

TASK: Tạo 1 kịch bản TikTok hoàn chỉnh (Vietnamese) cho video dài {duration} giây.

Video Topic: {topic}
Content Category: {category}
Category Description: {category_info['description']}
Tone: {category_info['tone']}

REQUIREMENTS:
1. Viết toàn bộ script bằng Tiếng Việt tự nhiên
2. Tối ưu cho format TikTok (16:9 vertical, muted viewing)
3. Hook trong 0-2 giây (CRITICAL - quyết định người xem stay hay skip)
4. Cấu trúc: Hook ({min(2, duration//15)}s) → Setup (3-5s) → Value Delivery (70% thời gian) → CTA (3-5s)
5. Phù hợp với {duration}s duration
6. Có text overlay suggestions (vì 60% viewers watch muted)
7. Lặp lại key points (người xem muted có thể miss audio)

OUTPUT FORMAT (JSON):
{{
  "hook": "Script cho 0-2s: Hook phrase gây sốc/tò mò",
  "hook_duration": 2,
  "setup": "Script cho setup phase (explain context quickly)",
  "setup_duration": 4,
  "value": "Script cho main value delivery (step-by-step, benefits, etc)",
  "value_duration": {duration - 11},
  "cta": "Script cho call-to-action cuối (follow, comment, save, visit link)",
  "cta_duration": 3,
  "caption": "Vietnamese caption (100-200 chars, có emoji, hook + benefit + CTA)",
  "hashtags": ["list 10-12 hashtags", "mix broad + niche", "#AIThựcChiến"],
  "trending_sounds": ["recommendation 1", "recommendation 2", "description"],
  "format_type": "description of trending format used (e.g. 'Before/After', 'Step-by-step tutorial')",
  "visual_notes": "Gợi ý visual/cinematography (colors, B-roll, text overlay placement)",
  "editing_tips": "Lời khuyên editing cụ thể (pacing, transitions, effects)"
}}

CRITICAL NOTES:
- Hook phải mạnh và grab attention trong 1-2 giây đầu
- Text overlay cho mỗi section (muted viewers)
- Pacing: Fast cuts (2-3 giây mỗi cut) phù hợp Vietnamese TikTok
- Lặp lại main benefit 2-3 lần (trong text + voiceover)
- Gọi CTA rõ ràng (Follow, Comment, Save, Link in bio)

Trả lời CHỈ JSON, không giải thích."""

    try:
        message = claude_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # Parse JSON response
        response_text = message.content[0].text.strip()

        # Try to extract JSON if wrapped in markdown code blocks
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        script_data = json.loads(response_text)

        # Create TikTokScript object
        script = TikTokScript(
            topic=topic,
            category=category,
            hook=script_data.get('hook', ''),
            hook_duration=script_data.get('hook_duration', 2),
            setup=script_data.get('setup', ''),
            setup_duration=script_data.get('setup_duration', 4),
            value=script_data.get('value', ''),
            value_duration=script_data.get('value_duration', duration - 11),
            cta=script_data.get('cta', ''),
            cta_duration=script_data.get('cta_duration', 3),
            total_duration=duration,
            caption=script_data.get('caption', ''),
            hashtags=script_data.get('hashtags', []),
            trending_sounds=script_data.get('trending_sounds', []),
            format_type=script_data.get('format_type', ''),
            visual_notes=script_data.get('visual_notes', ''),
            editing_tips=script_data.get('editing_tips', '')
        )

        logger.info(f"Generated script for '{topic}' ({duration}s, {category})")
        return script

    except json.JSONDecodeError as e:
        logger.error(f"Error parsing Claude response as JSON: {e}")
        raise
    except Exception as e:
        logger.error(f"Error generating script: {e}")
        raise


def generate_multiple_scripts(
    topic: str,
    num_variations: int = 3,
    category: Optional[str] = None
) -> List[TikTokScript]:
    """
    Generate multiple script variations for the same topic.

    Args:
        topic: Main topic
        num_variations: Number of variations to generate
        category: Content category (optional, random if not specified)

    Returns:
        List of TikTokScript objects
    """

    categories = ['news', 'tutorial', 'case_study', 'tool_review', 'bts']

    scripts = []
    for i in range(num_variations):
        try:
            cat = category or categories[i % len(categories)]
            logger.info(f"Generating script {i+1}/{num_variations} for '{topic}' ({cat})")

            script = generate_tiktok_script(
                topic=topic,
                category=cat,
                duration=30
            )
            scripts.append(script)
        except Exception as e:
            logger.error(f"Failed to generate variation {i+1}: {e}")

    return scripts


# ============================================================================
# INTERACTIVE SCRIPT GENERATOR
# ============================================================================

def interactive_generate():
    """Interactive mode for generating scripts."""
    print("\n" + "="*60)
    print("TikTok Script Generator - Interactive Mode")
    print("="*60)

    # Get topic
    topic = input("\n📝 Enter video topic: ").strip()
    if not topic:
        print("Error: Topic is required")
        return

    # Get category
    print("\n📂 Select content category:")
    categories = ['news', 'tutorial', 'case_study', 'tool_review', 'bts']
    for i, cat in enumerate(categories, 1):
        print(f"  {i}. {cat.replace('_', ' ').title()}")

    category_choice = input("Choose (1-5): ").strip()
    try:
        category = categories[int(category_choice) - 1]
    except (ValueError, IndexError):
        print("Invalid choice")
        return

    # Get duration
    duration_str = input("\n⏱️  Duration in seconds (15-60, default 30): ").strip()
    duration = 30
    if duration_str:
        try:
            duration = int(duration_str)
            if duration < 15 or duration > 60:
                print("Invalid duration, using 30s")
                duration = 30
        except ValueError:
            print("Invalid duration, using 30s")

    # Generate script
    print(f"\n⏳ Generating script for '{topic}' ({duration}s, {category})...")

    try:
        script = generate_tiktok_script(topic, category, duration)

        # Display script
        print("\n" + script.to_markdown())

        # Save option
        save_choice = input("\n💾 Save script? (y/n): ").strip().lower()
        if save_choice == 'y':
            # Save as JSON
            json_path = script.save_to_file()
            # Save as Markdown
            md_path = script.save_markdown()
            print(f"✓ Saved to:")
            print(f"  - {json_path}")
            print(f"  - {md_path}")

    except Exception as e:
        print(f"Error: {e}")
        logger.error(f"Error in interactive generation: {e}")


# ============================================================================
# BATCH SCRIPT GENERATION
# ============================================================================

def generate_content_batch(topics_file: Path) -> List[TikTokScript]:
    """
    Generate scripts for multiple topics from a file.

    Args:
        topics_file: Path to JSON file with topics
                    Format: [{"topic": "...", "category": "...", "duration": 30}, ...]

    Returns:
        List of generated scripts
    """

    try:
        with open(topics_file, 'r', encoding='utf-8') as f:
            topics = json.load(f)
    except Exception as e:
        logger.error(f"Error loading topics file: {e}")
        return []

    scripts = []
    for i, topic_data in enumerate(topics, 1):
        try:
            topic = topic_data.get('topic')
            category = topic_data.get('category', 'tutorial')
            duration = topic_data.get('duration', 30)

            logger.info(f"Generating script {i}/{len(topics)}: {topic}")

            script = generate_tiktok_script(topic, category, duration)
            script.save_to_file()
            script.save_markdown()
            scripts.append(script)

        except Exception as e:
            logger.error(f"Failed to generate script for topic {i}: {e}")

    logger.info(f"Batch generation complete. Generated {len(scripts)}/{len(topics)} scripts")
    return scripts


# ============================================================================
# CLI COMMANDS
# ============================================================================

def cmd_generate(args):
    """Generate single script."""
    if not args.topic or not args.category:
        print("Error: --topic and --category are required")
        sys.exit(1)

    duration = args.duration or 30

    try:
        script = generate_tiktok_script(args.topic, args.category, duration)

        # Display
        print("\n" + script.to_markdown())

        # Save if requested
        if args.save:
            json_path = script.save_to_file()
            md_path = script.save_markdown()
            print(f"\n✓ Saved to:")
            print(f"  - {json_path}")
            print(f"  - {md_path}")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def cmd_interactive(args):
    """Run interactive generator."""
    interactive_generate()


def cmd_batch(args):
    """Generate from batch file."""
    if not args.file:
        print("Error: --file is required")
        sys.exit(1)

    topics_file = Path(args.file)
    if not topics_file.exists():
        print(f"Error: File not found: {args.file}")
        sys.exit(1)

    scripts = generate_content_batch(topics_file)
    print(f"\n✓ Generated {len(scripts)} scripts")


def cmd_variations(args):
    """Generate multiple variations."""
    if not args.topic:
        print("Error: --topic is required")
        sys.exit(1)

    num = args.count or 3

    try:
        scripts = generate_multiple_scripts(args.topic, num, args.category)

        for i, script in enumerate(scripts, 1):
            print(f"\n{'='*60}")
            print(f"Variation {i}/{len(scripts)}")
            print(f"{'='*60}")
            print(script.to_markdown())

        # Save if requested
        if args.save:
            for script in scripts:
                script.save_to_file()
                script.save_markdown()
            print(f"\n✓ Saved {len(scripts)} scripts")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="TikTok Script Generator for AI Thực Chiến",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python tiktok-script-generator.py interactive

  # Generate single script
  python tiktok-script-generator.py generate \\
    --topic "ChatGPT tips for e-commerce" \\
    --category tutorial \\
    --duration 30 \\
    --save

  # Generate multiple variations
  python tiktok-script-generator.py variations \\
    --topic "AI tools for business" \\
    --count 3 \\
    --save

  # Batch generate from file
  python tiktok-script-generator.py batch \\
    --file topics.json
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Interactive mode
    interactive_parser = subparsers.add_parser('interactive', help='Interactive script generation')
    interactive_parser.set_defaults(func=cmd_interactive)

    # Generate single script
    generate_parser = subparsers.add_parser('generate', help='Generate single script')
    generate_parser.add_argument('--topic', required=True, help='Video topic')
    generate_parser.add_argument('--category', required=True,
                                choices=['news', 'tutorial', 'case_study', 'tool_review', 'bts'],
                                help='Content category')
    generate_parser.add_argument('--duration', type=int, help='Duration in seconds (15-60, default 30)')
    generate_parser.add_argument('--save', action='store_true', help='Save generated script')
    generate_parser.set_defaults(func=cmd_generate)

    # Generate variations
    variations_parser = subparsers.add_parser('variations', help='Generate multiple variations')
    variations_parser.add_argument('--topic', required=True, help='Video topic')
    variations_parser.add_argument('--category', help='Force category (optional)')
    variations_parser.add_argument('--count', type=int, help='Number of variations (default 3)')
    variations_parser.add_argument('--save', action='store_true', help='Save generated scripts')
    variations_parser.set_defaults(func=cmd_variations)

    # Batch generate
    batch_parser = subparsers.add_parser('batch', help='Batch generate from file')
    batch_parser.add_argument('--file', required=True, help='JSON file with topics')
    batch_parser.set_defaults(func=cmd_batch)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == '__main__':
    main()
