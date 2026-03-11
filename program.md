# program.md — AI Thực Chiến Content Pipeline Rules

> This file defines the quality criteria, metrics, and constraints for the
> automated content pipeline. The AI agent loops use these rules to
> self-evaluate and iteratively improve each output before moving on.
>
> **Philosophy (Karpathy's Autoresearch pattern):**
> The human defines *what good looks like*. The AI agent loops until it
> gets there — or runs out of budget.

---

## 1. Script Generation Rules

### Hard Constraints (MUST pass — reject if violated)
- Language: 100% Vietnamese (no English sentences, technical terms must be explained)
- Contains opening: "Xin chào" or similar Vietnamese greeting
- Contains at least one specific business example ("Ví dụ anh bán hàng...", "Chẳng hạn shop...")
- JSON output must be valid and contain ALL required fields:
  `title`, `description`, `tags`, `script`, `key_points`, `tiktok_caption`, `tiktok_hashtags`
- No hallucinated URLs or fake statistics

### Quality Metrics (scored 1-10)
| Metric | Weight | Description |
|--------|--------|-------------|
| hook_strength | 0.20 | First 2 sentences grab attention — curiosity, shock, or FOMO |
| business_relevance | 0.20 | Connects AI news to Vietnamese SMB/e-commerce/solopreneur |
| clarity | 0.15 | Simple language, no jargon, a 15-year-old could understand |
| structure | 0.15 | Follows the format template (hook → context → content → CTA) |
| engagement_cta | 0.10 | Ends with clear call-to-action (subscribe, comment, share) |
| title_seo | 0.10 | Title is clickable, contains keyword, under 80 chars |
| uniqueness | 0.10 | Not repetitive vs recent scripts (checked against history) |

### Thresholds
- **Minimum weighted score to accept**: 7.0 / 10
- **Maximum retry attempts**: 3
- **If all retries fail**: Accept best attempt, log warning

### Script Length Targets
| Format | Word Count (Vietnamese) | Duration Target |
|--------|------------------------|-----------------|
| long | 800–1200 words | 5–8 minutes |
| short | 100–180 words | 45–60 seconds |

---

## 2. Title & Metadata Rules

### Title
- Max 80 characters (Vietnamese)
- Must contain primary keyword in first 40 chars
- Use power words: Mới, Thực tế, Hướng dẫn, Tiết kiệm, Bí quyết, X cách
- No ALL CAPS (except acronyms like AI, ChatGPT)
- No clickbait that doesn't match content

### Description
- YouTube: 150–300 words, includes hashtags, timestamps placeholder
- TikTok caption: 100–200 characters, emoji + hook + CTA

### Tags
- 10–20 tags, mix of broad ("AI", "Automation") and specific ("ChatGPT cho bán hàng")
- Must include: #AIThựcChiến, #AI
- Vietnamese tags preferred

---

## 3. TTS Audio Rules

### Hard Constraints
- Audio duration within 15% of target for format type
- No silent gaps > 2 seconds (indicates truncation bug)
- Audio file size > 100KB (catches empty/corrupt files)

### Quality Targets
- Speech rate: natural Vietnamese cadence (+0% to +10% speed)
- Voice: consistent across episodes (male: vi-VN-NamMinhNeural)

---

## 4. Video Composition Rules

### Hard Constraints
- YouTube: 1920x1080 @ 30fps, H.264, < 500MB
- TikTok/Shorts: 1080x1920 @ 30fps, H.264, < 100MB
- Subtitles must be present and readable (font size ≥ 24)
- Watermark "AI Thực Chiến" visible

### Quality Targets
- Video duration matches audio duration (±2 seconds)
- No black frames at start/end (> 1 second)

---

## 5. Content Freshness Rules

- News must be from last 24 hours (prefer < 12 hours)
- Never repeat same news story within 7 days
- Minimum 3 unique news items per script

---

## 6. Cost Budget

| Resource | Budget per video | Notes |
|----------|-----------------|-------|
| Claude API (Sonnet) | < $0.05 | ~3 calls × 4K tokens |
| Replicate (SadTalker) | < $1.50 | ~$0.27 × chunks |
| Edge TTS | $0.00 | Free |
| Total per video | < $2.00 | Alert if exceeded |

---

## 7. Engagement Feedback Loop

### Metrics to Track (post-upload)
- YouTube: views (24h), watch time %, likes, comments
- TikTok: views (24h), shares, comments
- Facebook: impressions, engagement rate

### Feedback Rules
- If a topic gets >2x average views → generate follow-up content
- If a format consistently underperforms → reduce frequency
- Track which hooks/titles perform best → feed into prompt
- Weekly: summarize top/bottom performing content types

### History Window
- Keep last 30 days of scripts for uniqueness checking
- Keep last 90 days of engagement metrics for trend analysis

---

## 8. Agent Loop Configuration

```
MAX_RETRIES_PER_STEP = 3
QUALITY_THRESHOLD = 7.0
EVALUATION_MODEL = "claude-sonnet-4-20250514"  # Use Sonnet for eval (cheap)
GENERATION_MODEL = "claude-sonnet-4-20250514"  # Use Sonnet for generation
```

### Loop Pattern
```
for attempt in range(MAX_RETRIES):
    output = generate(input, feedback=previous_feedback)
    score, feedback = evaluate(output, rules=program.md)
    if score >= QUALITY_THRESHOLD:
        return output  # Accept
    previous_feedback = feedback  # Feed back for next attempt
return best_output  # Accept best if threshold never met
```
