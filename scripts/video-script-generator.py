#!/usr/bin/env python3
"""
Video Script Generator for AI Thực Chiến

Generates full video scripts in Vietnamese for both Shorts (60s) and long-form videos.
Includes script structure, talking points, transitions, and thumbnail suggestions.

Usage:
    python3 video-script-generator.py --topic "ChatGPT for e-commerce" --format short
    python3 video-script-generator.py --topic "AI trends March 2026" --format long
    python3 video-script-generator.py --file topics.json --batch
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict
from enum import Enum

try:
    from anthropic import Anthropic
except ImportError:
    print("ERROR: anthropic package not found. Install with: pip install anthropic")
    sys.exit(1)


# ============================================================================
# Configuration & Models
# ============================================================================

class VideoFormat(str, Enum):
    """Video format types"""
    SHORT = "short"  # 45-60 seconds
    LONG = "long"    # 5-12 minutes


@dataclass
class ScriptSegment:
    """Individual segment of a video script"""
    name: str
    duration_seconds: int
    content: str
    instructions: Optional[str] = None
    visual_notes: Optional[str] = None


@dataclass
class VideoScript:
    """Complete video script with all components"""
    topic: str
    format_type: VideoFormat
    total_duration: int
    title: str
    thumbnail_suggestions: List[Dict[str, str]]
    segments: List[ScriptSegment]
    key_talking_points: List[str]
    engagement_hooks: List[str]
    generated_at: str = None

    def __post_init__(self):
        if self.generated_at is None:
            self.generated_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "topic": self.topic,
            "format_type": self.format_type.value,
            "total_duration_seconds": self.total_duration,
            "title": self.title,
            "thumbnail_suggestions": self.thumbnail_suggestions,
            "segments": [asdict(seg) for seg in self.segments],
            "key_talking_points": self.key_talking_points,
            "engagement_hooks": self.engagement_hooks,
            "generated_at": self.generated_at
        }


# ============================================================================
# Logging
# ============================================================================

def setup_logging(log_file: Optional[str] = None) -> logging.Logger:
    """Configure logging"""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)

    return logger


logger = setup_logging("script_generator.log")


# ============================================================================
# Script Generation
# ============================================================================

class ScriptGenerator:
    """Generates video scripts using Claude API"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        self.client = Anthropic(api_key=self.api_key)
        logger.info("Initialized ScriptGenerator")

    def generate_short_form_script(self, topic: str) -> VideoScript:
        """Generate 45-60 second Short video script"""
        logger.info(f"Generating short-form script for: {topic}")

        prompt = f"""You are a professional video scriptwriter for AI Thực Chiến, a Vietnamese-language channel about AI automation for SMBs.

Create a COMPLETE 45-60 second video script for YouTube Shorts about: {topic}

REQUIREMENTS:
1. Vietnamese language only
2. Spoken script (natural, conversational tone)
3. Hook the viewer in first 2-3 seconds
4. Clear demonstration or benefit statement
5. Call-to-action at the end (Subscribe, Link in bio, etc)
6. Include [VISUAL] tags for visuals/graphics/B-roll needed
7. Include [TEXT OVERLAY] tags for text that appears on screen
8. Include [MUSIC] notes for pacing

Script format:
[0-3s] HOOK: [hook content]
[3-X] BODY: [main content with [VISUAL] tags]
[X-60s] CTA: [call-to-action]

Now generate the complete script below:
"""

        response = self.client.messages.create(
            model="claude-opus-4-1-20250805",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )

        script_content = response.content[0].text.strip()

        # Extract components
        title = self._extract_title_short(topic, script_content)
        segments = self._parse_short_segments(script_content)
        talking_points = self._extract_talking_points(script_content)
        hooks = self._extract_hooks(script_content)
        thumbnails = self._generate_thumbnail_suggestions(topic, "short")

        return VideoScript(
            topic=topic,
            format_type=VideoFormat.SHORT,
            total_duration=55,
            title=title,
            thumbnail_suggestions=thumbnails,
            segments=segments,
            key_talking_points=talking_points,
            engagement_hooks=hooks
        )

    def generate_long_form_script(self, topic: str) -> VideoScript:
        """Generate 8-10 minute long-form video script"""
        logger.info(f"Generating long-form script for: {topic}")

        prompt = f"""You are a professional video scriptwriter for AI Thực Chiến, a Vietnamese-language channel about AI automation for SMBs.

Create a COMPLETE 8-10 minute video script about: {topic}

REQUIREMENTS:
1. Vietnamese language only
2. Spoken script with natural, conversational tone (not reading)
3. Structure:
   - Intro Hook (0-30s): Why viewer should watch
   - Problem/Context (30s-2min): What problem this solves
   - Solution/Demo (2min-7min): Step-by-step walkthrough with demos
   - Results/Takeaway (7min-9min): What they've learned
   - CTA (9min-10min): Subscribe, next video, etc
4. Include [VISUAL] tags for demos, graphics, screenshots
5. Include [TEXT OVERLAY] tags for key points, numbers, tools
6. Include [B-ROLL] tags for supplementary footage
7. Include [MUSIC] notes for tone/pacing
8. Natural transitions between segments
9. Pause beats for comprehension
10. Engagement questions/calls to action throughout

Format your response as a detailed script with timestamps and visual notes.

Generate the complete script below:
"""

        response = self.client.messages.create(
            model="claude-opus-4-1-20250805",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )

        script_content = response.content[0].text.strip()

        # Extract components
        title = self._extract_title_long(topic, script_content)
        segments = self._parse_long_segments(script_content)
        talking_points = self._extract_talking_points(script_content)
        hooks = self._extract_hooks(script_content)
        thumbnails = self._generate_thumbnail_suggestions(topic, "long")

        return VideoScript(
            topic=topic,
            format_type=VideoFormat.LONG,
            total_duration=540,  # 9 minutes average
            title=title,
            thumbnail_suggestions=thumbnails,
            segments=segments,
            key_talking_points=talking_points,
            engagement_hooks=hooks
        )

    def _extract_title_short(self, topic: str, script: str) -> str:
        """Extract or generate Short title"""
        prompt = f"""Based on this short video script about "{topic}", generate a compelling YouTube Shorts title.
Requirements: Max 100 characters, includes power words, SEO-optimized for Vietnamese.

Script excerpt:
{script[:500]}

Return ONLY the title, no quotes."""

        response = self.client.messages.create(
            model="claude-opus-4-1-20250805",
            max_tokens=50,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text.strip()

    def _extract_title_long(self, topic: str, script: str) -> str:
        """Extract or generate long-form title"""
        prompt = f"""Based on this long video script about "{topic}", generate a compelling YouTube title.
Requirements: 50-100 characters, includes benefit statement, SEO-optimized for Vietnamese.

Script excerpt:
{script[:500]}

Return ONLY the title, no quotes."""

        response = self.client.messages.create(
            model="claude-opus-4-1-20250805",
            max_tokens=50,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text.strip()

    def _parse_short_segments(self, script: str) -> List[ScriptSegment]:
        """Parse short-form script into segments"""
        segments = []
        lines = script.split("\n")

        current_segment = None
        current_content = []

        for line in lines:
            if line.startswith("[") and "s]" in line:
                if current_segment:
                    segments.append(ScriptSegment(
                        name=current_segment,
                        duration_seconds=10,
                        content="\n".join(current_content).strip(),
                        visual_notes=self._extract_visual_notes("\n".join(current_content))
                    ))
                current_segment = line.split("]")[0] + "]"
                current_content = []
            else:
                current_content.append(line)

        if current_segment:
            segments.append(ScriptSegment(
                name=current_segment,
                duration_seconds=10,
                content="\n".join(current_content).strip(),
                visual_notes=self._extract_visual_notes("\n".join(current_content))
            ))

        return segments or [ScriptSegment("Full Script", 55, script)]

    def _parse_long_segments(self, script: str) -> List[ScriptSegment]:
        """Parse long-form script into segments by section"""
        segments = []
        lines = script.split("\n")

        current_section = None
        current_content = []
        section_starts = {
            "Intro": 0,
            "Problem": 30,
            "Solution": 120,
            "Results": 420,
            "CTA": 540
        }

        for line in lines:
            if any(section in line for section in section_starts.keys()):
                if current_section:
                    segments.append(ScriptSegment(
                        name=current_section,
                        duration_seconds=section_starts.get(current_section, 120),
                        content="\n".join(current_content).strip(),
                        visual_notes=self._extract_visual_notes("\n".join(current_content))
                    ))
                current_section = line.split(":")[0] if ":" in line else line
                current_content = []
            else:
                current_content.append(line)

        if current_section:
            segments.append(ScriptSegment(
                name=current_section,
                duration_seconds=section_starts.get(current_section, 120),
                content="\n".join(current_content).strip(),
                visual_notes=self._extract_visual_notes("\n".join(current_content))
            ))

        return segments or [ScriptSegment("Full Script", 540, script)]

    def _extract_visual_notes(self, content: str) -> str:
        """Extract [VISUAL] and [TEXT OVERLAY] tags from content"""
        visual_lines = []
        for line in content.split("\n"):
            if "[VISUAL]" in line or "[TEXT OVERLAY]" in line or "[B-ROLL]" in line:
                visual_lines.append(line)
        return "\n".join(visual_lines) if visual_lines else None

    def _extract_talking_points(self, script: str) -> List[str]:
        """Extract key talking points from script"""
        points = []
        for line in script.split("\n"):
            if "-" in line and len(line) < 150:
                clean = line.replace("-", "").replace("•", "").strip()
                if clean and len(clean) > 10:
                    points.append(clean)
        return list(set(points[:5]))  # Return unique, max 5

    def _extract_hooks(self, script: str) -> List[str]:
        """Extract engagement hooks from script"""
        hooks = []
        lines = script.split("\n")
        for i, line in enumerate(lines):
            if "HOOK" in line or "?" in line:
                if i + 1 < len(lines):
                    hooks.append(lines[i + 1].strip())
        return hooks[:3]

    def _generate_thumbnail_suggestions(self, topic: str, format_type: str) -> List[Dict[str, str]]:
        """Generate thumbnail design suggestions"""
        prompt = f"""Generate 2-3 YouTube thumbnail design suggestions for {format_type} video about: {topic}

For each thumbnail, specify:
1. Main text (max 3 words)
2. Color scheme (primary + accent color)
3. Visual element (what image/screenshot to include)
4. Target emotion (excited, surprised, curious, etc)

Format as JSON array with fields: text, colors, visual, emotion

Return ONLY the JSON."""

        response = self.client.messages.create(
            model="claude-opus-4-1-20250805",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )

        try:
            thumbnails = json.loads(response.content[0].text)
            return thumbnails if isinstance(thumbnails, list) else [thumbnails]
        except json.JSONDecodeError:
            logger.warning("Could not parse thumbnail suggestions")
            return [{"text": "Watch", "colors": "Teal + Orange", "visual": "Topic-relevant", "emotion": "curious"}]


# ============================================================================
# Output Formatting
# ============================================================================

def format_script_markdown(script: VideoScript) -> str:
    """Format script as readable Markdown"""
    output = []

    output.append(f"# {script.topic}")
    output.append("")
    output.append(f"**Format**: {script.format_type.value.upper()}")
    output.append(f"**Duration**: {script.total_duration // 60} min {script.total_duration % 60}s")
    output.append(f"**Title**: {script.title}")
    output.append("")

    # Thumbnail suggestions
    output.append("## Thumbnail Suggestions")
    output.append("")
    for i, thumb in enumerate(script.thumbnail_suggestions, 1):
        output.append(f"### Option {i}")
        for key, value in thumb.items():
            output.append(f"- **{key.title()}**: {value}")
        output.append("")

    # Script segments
    output.append("## Video Script")
    output.append("")
    for segment in script.segments:
        output.append(f"### {segment.name} ({segment.duration_seconds}s)")
        output.append("")
        output.append(segment.content)
        output.append("")
        if segment.visual_notes:
            output.append("**Visual Notes:**")
            output.append(segment.visual_notes)
            output.append("")

    # Key talking points
    output.append("## Key Talking Points")
    output.append("")
    for point in script.key_talking_points:
        output.append(f"- {point}")
    output.append("")

    # Engagement hooks
    output.append("## Engagement Hooks")
    output.append("")
    for hook in script.engagement_hooks:
        output.append(f"- {hook}")
    output.append("")

    output.append(f"*Generated: {script.generated_at}*")

    return "\n".join(output)


def format_script_json(script: VideoScript) -> str:
    """Format script as JSON"""
    return json.dumps(script.to_dict(), indent=2, ensure_ascii=False)


# ============================================================================
# File I/O
# ============================================================================

class ScriptLibrary:
    """Manages script storage and retrieval"""

    def __init__(self, library_dir: str = "scripts_library"):
        self.library_dir = Path(library_dir)
        self.library_dir.mkdir(exist_ok=True)
        logger.info(f"Using script library: {self.library_dir}")

    def save_script(self, script: VideoScript, format_output: str = "both") -> Dict[str, str]:
        """Save script in specified format(s)"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        topic_slug = script.topic[:30].replace(" ", "_").replace("/", "_")
        base_name = f"{timestamp}_{topic_slug}_{script.format_type.value}"

        saved_files = {}

        if format_output in ["json", "both"]:
            json_file = self.library_dir / f"{base_name}.json"
            with open(json_file, "w", encoding="utf-8") as f:
                f.write(format_script_json(script))
            saved_files["json"] = str(json_file)
            logger.info(f"Saved JSON: {json_file}")

        if format_output in ["markdown", "both"]:
            md_file = self.library_dir / f"{base_name}.md"
            with open(md_file, "w", encoding="utf-8") as f:
                f.write(format_script_markdown(script))
            saved_files["markdown"] = str(md_file)
            logger.info(f"Saved Markdown: {md_file}")

        return saved_files

    def list_scripts(self) -> List[Path]:
        """List all saved scripts"""
        return sorted(self.library_dir.glob("*.md"))


# ============================================================================
# Batch Processing
# ============================================================================

def process_batch(topics_file: str, output_dir: str = "scripts_library"):
    """Process multiple topics from JSON file"""
    logger.info(f"Starting batch processing from: {topics_file}")

    try:
        with open(topics_file, "r", encoding="utf-8") as f:
            topics_data = json.load(f)
    except FileNotFoundError:
        logger.error(f"Topics file not found: {topics_file}")
        return
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in: {topics_file}")
        return

    generator = ScriptGenerator()
    library = ScriptLibrary(output_dir)

    topics = topics_data if isinstance(topics_data, list) else topics_data.get("topics", [])

    for i, item in enumerate(topics, 1):
        try:
            topic = item if isinstance(item, str) else item.get("topic")
            format_type = item.get("format", "long") if isinstance(item, dict) else "long"

            logger.info(f"Processing {i}/{len(topics)}: {topic} ({format_type})")

            if format_type == "short":
                script = generator.generate_short_form_script(topic)
            else:
                script = generator.generate_long_form_script(topic)

            saved = library.save_script(script)
            print(f"✓ Generated: {topic}")
            for fmt, path in saved.items():
                print(f"  → {fmt}: {path}")

        except Exception as e:
            logger.error(f"Error processing {topic}: {e}")
            print(f"✗ Failed: {topic} - {e}")

    logger.info("Batch processing complete")


# ============================================================================
# CLI
# ============================================================================

def main():
    """Command-line interface"""
    parser = argparse.ArgumentParser(
        description="Video script generator for AI Thực Chiến",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate single Short script
  python3 video-script-generator.py --topic "ChatGPT tips" --format short

  # Generate long-form script
  python3 video-script-generator.py --topic "AI automation guide" --format long

  # Batch process from JSON file
  python3 video-script-generator.py --batch --file topics.json

  # Batch process with custom output
  python3 video-script-generator.py --batch --file topics.json --output my_scripts/

  # List generated scripts
  python3 video-script-generator.py --list

JSON file format for batch:
{
  "topics": [
    "ChatGPT for e-commerce",
    {"topic": "Zapier automation", "format": "long"},
    {"topic": "AI tips", "format": "short"}
  ]
}
        """
    )

    parser.add_argument("--topic", help="Video topic/title")
    parser.add_argument("--format", choices=["short", "long"], default="long",
                        help="Video format (default: long)")
    parser.add_argument("--batch", action="store_true",
                        help="Process batch from JSON file")
    parser.add_argument("--file", default="topics.json",
                        help="Topics JSON file for batch processing (default: topics.json)")
    parser.add_argument("--output", default="scripts_library",
                        help="Output directory for scripts (default: scripts_library)")
    parser.add_argument("--format-output", choices=["json", "markdown", "both"], default="both",
                        help="Output format(s) (default: both)")
    parser.add_argument("--list", action="store_true",
                        help="List all generated scripts")

    args = parser.parse_args()

    try:
        generator = ScriptGenerator()
        library = ScriptLibrary(args.output)

        if args.batch:
            process_batch(args.file, args.output)

        elif args.list:
            scripts = library.list_scripts()
            if scripts:
                print(f"\nFound {len(scripts)} scripts:\n")
                for script_file in scripts:
                    print(f"  {script_file.name}")
            else:
                print("No scripts found")

        elif args.topic:
            logger.info(f"Generating script: {args.topic} ({args.format})")

            if args.format == "short":
                script = generator.generate_short_form_script(args.topic)
            else:
                script = generator.generate_long_form_script(args.topic)

            saved = library.save_script(script, args.format_output)

            # Print to console
            if args.format_output in ["markdown", "both"]:
                print(format_script_markdown(script))
            else:
                print(format_script_json(script))

            # Print file paths
            print("\n" + "=" * 60)
            print("FILES SAVED:")
            for fmt, path in saved.items():
                print(f"  {fmt}: {path}")
            print("=" * 60)

        else:
            parser.print_help()

    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
