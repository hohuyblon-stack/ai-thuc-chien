#!/usr/bin/env python3
"""
Quality Agent Loop for AI Thực Chiến

Implements Karpathy's Autoresearch pattern:
  Human defines rules (program.md) → AI generates → AI evaluates → AI improves → repeat

Each pipeline step runs inside an agent loop:
  1. Generate output
  2. Evaluate against program.md criteria
  3. If score < threshold, feed evaluation back as improvement guidance
  4. Repeat until quality threshold met or budget exhausted

Usage:
    from quality_loop import AgentLoop, ScriptEvaluator

    loop = AgentLoop(max_retries=3, threshold=7.0)
    result = loop.run(generate_fn, evaluate_fn, context)
"""

import os
import json
import logging
import time
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Callable, Any, Optional, List, Dict

logger = logging.getLogger(__name__)

PROJECT_DIR = Path(__file__).parent.parent


# ============================================================================
# Data Types
# ============================================================================

@dataclass
class EvalResult:
    """Result of evaluating one output against program.md criteria."""
    score: float  # Weighted score 0-10
    passed: bool  # Whether it meets the threshold
    metrics: Dict[str, float] = field(default_factory=dict)  # Individual metric scores
    hard_fail_reasons: List[str] = field(default_factory=list)  # Hard constraint violations
    feedback: str = ""  # Natural language feedback for next attempt
    attempt: int = 0


@dataclass
class LoopResult:
    """Result of running an agent loop."""
    output: Any  # The best output produced
    final_score: float
    attempts: int
    accepted: bool  # True if threshold met, False if best-effort
    eval_history: List[EvalResult] = field(default_factory=list)
    total_time_seconds: float = 0.0


# ============================================================================
# Agent Loop Engine
# ============================================================================

class AgentLoop:
    """Generic agent loop: generate → evaluate → improve → repeat.

    This is the core primitive from Karpathy's Autoresearch concept.
    The human defines quality rules in program.md; this engine enforces them.
    """

    def __init__(
        self,
        max_retries: int = 3,
        threshold: float = 7.0,
        name: str = "agent_loop",
    ):
        self.max_retries = max_retries
        self.threshold = threshold
        self.name = name

    def run(
        self,
        generate_fn: Callable,
        evaluate_fn: Callable,
        context: dict,
    ) -> LoopResult:
        """Run the agent loop.

        Args:
            generate_fn(context, feedback=None) → output
            evaluate_fn(output, context) → EvalResult
            context: dict with input data for generation

        Returns:
            LoopResult with best output and evaluation history
        """
        start = time.time()
        best_output = None
        best_score = -1.0
        eval_history = []
        feedback = None

        for attempt in range(1, self.max_retries + 1):
            logger.info(f"[{self.name}] Attempt {attempt}/{self.max_retries}")

            # Generate
            output = generate_fn(context, feedback=feedback)

            # Evaluate
            eval_result = evaluate_fn(output, context)
            eval_result.attempt = attempt
            eval_history.append(eval_result)

            logger.info(
                f"[{self.name}] Score: {eval_result.score:.1f}/10 "
                f"(threshold: {self.threshold}) | "
                f"Hard fails: {len(eval_result.hard_fail_reasons)}"
            )

            # Track best
            if eval_result.score > best_score:
                best_score = eval_result.score
                best_output = output

            # Accept if meets threshold and no hard failures
            if eval_result.passed and not eval_result.hard_fail_reasons:
                logger.info(f"[{self.name}] Accepted on attempt {attempt}")
                return LoopResult(
                    output=best_output,
                    final_score=best_score,
                    attempts=attempt,
                    accepted=True,
                    eval_history=eval_history,
                    total_time_seconds=time.time() - start,
                )

            # Prepare feedback for next attempt
            feedback = eval_result.feedback
            if eval_result.hard_fail_reasons:
                feedback = (
                    "CRITICAL ISSUES (must fix):\n"
                    + "\n".join(f"- {r}" for r in eval_result.hard_fail_reasons)
                    + "\n\nAdditional feedback:\n"
                    + (eval_result.feedback or "Improve overall quality.")
                )

            logger.info(f"[{self.name}] Feedback: {feedback[:200]}...")

        # Exhausted retries — return best attempt
        logger.warning(
            f"[{self.name}] Threshold not met after {self.max_retries} attempts. "
            f"Best score: {best_score:.1f}. Accepting best-effort output."
        )
        return LoopResult(
            output=best_output,
            final_score=best_score,
            attempts=self.max_retries,
            accepted=False,
            eval_history=eval_history,
            total_time_seconds=time.time() - start,
        )


# ============================================================================
# Script Evaluator (evaluates video scripts against program.md rules)
# ============================================================================

class ScriptEvaluator:
    """Evaluates generated video scripts against program.md criteria.

    Uses Claude to score quality metrics and check hard constraints.
    """

    METRIC_WEIGHTS = {
        "hook_strength": 0.20,
        "business_relevance": 0.20,
        "clarity": 0.15,
        "structure": 0.15,
        "engagement_cta": 0.10,
        "title_seo": 0.10,
        "uniqueness": 0.10,
    }

    WORD_COUNT_TARGETS = {
        "long": (800, 1200),
        "short": (100, 180),
    }

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            from anthropic import Anthropic
            api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY")
            if not api_key:
                raise RuntimeError("ANTHROPIC_API_KEY not set")
            self._client = Anthropic(api_key=api_key)
        return self._client

    def evaluate(self, script_data: dict, context: dict) -> EvalResult:
        """Evaluate a script against program.md rules.

        Args:
            script_data: dict with title, script, description, tags, etc.
            context: dict with format_type, recent_titles, etc.
        """
        hard_fails = self._check_hard_constraints(script_data, context)
        metrics, feedback = self._score_with_llm(script_data, context)

        # Calculate weighted score
        weighted_score = sum(
            metrics.get(m, 5.0) * w
            for m, w in self.METRIC_WEIGHTS.items()
        ) / sum(self.METRIC_WEIGHTS.values())

        # Hard failures cap score at 4.0
        if hard_fails:
            weighted_score = min(weighted_score, 4.0)

        passed = weighted_score >= 7.0 and not hard_fails

        return EvalResult(
            score=round(weighted_score, 1),
            passed=passed,
            metrics=metrics,
            hard_fail_reasons=hard_fails,
            feedback=feedback,
        )

    def _check_hard_constraints(self, script_data: dict, context: dict) -> List[str]:
        """Check hard constraints from program.md. Returns list of violations."""
        fails = []

        # Required fields
        required = ["title", "description", "tags", "script", "key_points",
                     "tiktok_caption", "tiktok_hashtags"]
        missing = [f for f in required if f not in script_data or not script_data[f]]
        if missing:
            fails.append(f"Missing required fields: {', '.join(missing)}")

        script_text = script_data.get("script", "")
        title = script_data.get("title", "")

        # Must contain Vietnamese greeting
        greetings = ["xin chào", "chào các bạn", "chào mọi người", "hello các bạn"]
        if not any(g in script_text.lower() for g in greetings):
            fails.append("Script missing Vietnamese greeting (Xin chào / Chào các bạn)")

        # Must contain business example
        biz_markers = ["ví dụ", "chẳng hạn", "shop", "bán hàng", "doanh nghiệp",
                        "business", "kinh doanh", "khách hàng", "doanh thu"]
        if not any(m in script_text.lower() for m in biz_markers):
            fails.append("Script missing specific business example")

        # Word count check
        format_type = context.get("format_type", "long")
        words = len(script_text.split())
        min_w, max_w = self.WORD_COUNT_TARGETS.get(format_type, (800, 1200))
        if words < min_w * 0.7:  # 30% tolerance
            fails.append(f"Script too short: {words} words (min ~{min_w})")
        if words > max_w * 1.5:  # 50% tolerance
            fails.append(f"Script too long: {words} words (max ~{max_w})")

        # Title length
        if len(title) > 100:
            fails.append(f"Title too long: {len(title)} chars (max 80)")

        return fails

    def _score_with_llm(self, script_data: dict, context: dict) -> tuple:
        """Use Claude to score quality metrics. Returns (metrics_dict, feedback_str)."""
        client = self._get_client()

        eval_prompt = f"""You are a content quality evaluator for a Vietnamese AI automation YouTube channel.

Evaluate this video script and return a JSON score card.

SCRIPT DATA:
- Title: {script_data.get('title', 'N/A')}
- Script (first 1500 chars): {script_data.get('script', '')[:1500]}
- Description (first 500 chars): {script_data.get('description', '')[:500]}
- Tags: {script_data.get('tags', [])}
- TikTok caption: {script_data.get('tiktok_caption', 'N/A')}
- Format: {context.get('format_type', 'long')}

Score each metric from 1-10:
1. hook_strength: Do the first 2 sentences grab attention? (curiosity, shock, FOMO)
2. business_relevance: Does it connect AI news to Vietnamese SMB/e-commerce owners?
3. clarity: Simple language, no unexplained jargon, easy to understand?
4. structure: Follows format template? (hook → context → content → CTA)
5. engagement_cta: Clear call-to-action at the end? (subscribe, comment, share)
6. title_seo: Is the title clickable, keyword-rich, under 80 chars?
7. uniqueness: Does it feel fresh, not generic/template-like?

Return ONLY this JSON:
{{
    "scores": {{
        "hook_strength": <1-10>,
        "business_relevance": <1-10>,
        "clarity": <1-10>,
        "structure": <1-10>,
        "engagement_cta": <1-10>,
        "title_seo": <1-10>,
        "uniqueness": <1-10>
    }},
    "feedback": "<2-3 sentences of specific improvement suggestions in Vietnamese>"
}}"""

        try:
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                messages=[{"role": "user", "content": eval_prompt}],
            )
            raw = response.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

            data = json.loads(raw)
            metrics = {k: float(v) for k, v in data.get("scores", {}).items()}
            feedback = data.get("feedback", "")
            return metrics, feedback

        except Exception as e:
            logger.warning(f"LLM evaluation failed: {e}. Using default scores.")
            return {m: 5.0 for m in self.METRIC_WEIGHTS}, "Evaluation failed, using defaults."


# ============================================================================
# TTS Evaluator (checks audio output quality)
# ============================================================================

class TTSEvaluator:
    """Evaluates TTS audio output against program.md criteria."""

    @staticmethod
    def evaluate(audio_path: str, context: dict) -> EvalResult:
        """Check TTS output for common issues."""
        import subprocess

        fails = []
        metrics = {}
        audio_file = Path(audio_path)

        # Check file exists and has content
        if not audio_file.exists():
            return EvalResult(score=0, passed=False, hard_fail_reasons=["Audio file missing"])

        file_size = audio_file.stat().st_size
        if file_size < 100 * 1024:  # < 100KB
            fails.append(f"Audio file suspiciously small: {file_size/1024:.0f}KB")

        # Get duration via ffprobe
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                 "-of", "json", str(audio_file)],
                capture_output=True, text=True,
            )
            data = json.loads(result.stdout)
            duration = float(data["format"]["duration"])
        except (KeyError, json.JSONDecodeError, FileNotFoundError):
            duration = 0.0
            fails.append("Could not determine audio duration (ffprobe failed)")

        # Duration check against format targets
        format_type = context.get("format_type", "long")
        if format_type == "long":
            target_min, target_max = 180, 600  # 3-10 minutes
        else:
            target_min, target_max = 30, 90  # 30s-90s

        if duration > 0:
            if duration < target_min:
                fails.append(f"Audio too short: {duration:.0f}s (min {target_min}s)")
            elif duration > target_max:
                fails.append(f"Audio too long: {duration:.0f}s (max {target_max}s)")

            metrics["duration_score"] = 10.0 if target_min <= duration <= target_max else 4.0

        # Check for silent gaps (truncation indicator)
        try:
            silence_result = subprocess.run(
                ["ffmpeg", "-i", str(audio_file), "-af",
                 "silencedetect=noise=-40dB:d=2", "-f", "null", "-"],
                capture_output=True, text=True, timeout=30,
            )
            silence_count = silence_result.stderr.count("silence_end")
            if silence_count > 5:
                fails.append(f"Audio has {silence_count} silent gaps >2s (possible truncation)")
            metrics["silence_score"] = max(1.0, 10.0 - silence_count)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            metrics["silence_score"] = 5.0  # Unknown

        score = sum(metrics.values()) / max(len(metrics), 1)
        return EvalResult(
            score=round(score, 1),
            passed=score >= 7.0 and not fails,
            metrics=metrics,
            hard_fail_reasons=fails,
            feedback="; ".join(fails) if fails else "Audio quality acceptable.",
        )


# ============================================================================
# Script History (for uniqueness checking)
# ============================================================================

class ScriptHistory:
    """Tracks recent scripts for uniqueness comparison."""

    def __init__(self, history_file: Optional[str] = None):
        self.history_file = Path(history_file or PROJECT_DIR / "data" / "script_history.json")
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self._history = self._load()

    def _load(self) -> List[dict]:
        if self.history_file.exists():
            try:
                return json.loads(self.history_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return []
        return []

    def save(self):
        self.history_file.write_text(
            json.dumps(self._history, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def add(self, script_data: dict):
        """Add a script to history."""
        entry = {
            "date": time.strftime("%Y-%m-%d"),
            "title": script_data.get("title", ""),
            "key_points": script_data.get("key_points", []),
        }
        self._history.append(entry)
        # Keep last 30 days
        self._history = self._history[-30:]
        self.save()

    def get_recent_titles(self, days: int = 7) -> List[str]:
        """Get titles from recent N entries."""
        return [h["title"] for h in self._history[-days:]]


# ============================================================================
# Convenience: wrap generate_script with agent loop
# ============================================================================

def generate_script_with_loop(
    news_summary: str,
    format_type: str = "long",
    max_retries: int = 3,
    threshold: float = 7.0,
) -> tuple:
    """Generate a video script using the agent loop pattern.

    Returns (script_data, loop_result) where loop_result has evaluation history.
    """
    evaluator = ScriptEvaluator()
    history = ScriptHistory()

    context = {
        "news_summary": news_summary,
        "format_type": format_type,
        "recent_titles": history.get_recent_titles(),
    }

    def generate_fn(ctx, feedback=None):
        """Generate script, incorporating feedback if provided."""
        from daily_pipeline import generate_script as _gen

        if feedback:
            # Append feedback to news summary so it reaches the prompt
            augmented_news = (
                ctx["news_summary"]
                + f"\n\n--- QUALITY FEEDBACK (improve these) ---\n{feedback}"
            )
            return _gen(augmented_news, ctx["format_type"])
        return _gen(ctx["news_summary"], ctx["format_type"])

    def evaluate_fn(output, ctx):
        return evaluator.evaluate(output, ctx)

    loop = AgentLoop(max_retries=max_retries, threshold=threshold, name="script_gen")
    result = loop.run(generate_fn, evaluate_fn, context)

    # Record in history
    if result.output:
        history.add(result.output)

    return result.output, result
