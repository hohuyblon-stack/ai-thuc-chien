# AI Thực Chiến — Project Context for Claude Cowork

## What This Is
Automated Vietnamese AI news YouTube channel. Fully automated pipeline: scrape AI news → generate Vietnamese script → TTS → talking-head avatar video → compose final video → upload to YouTube. Inspired by Julian Goldie SEO (347K subs, 100% AI avatar content).

## Project Root
`~/ai-thuc-chien/`

## Architecture

```
Tavily API (news) → Claude via Poe API (Vietnamese script)
  → ElevenLabs via Poe API (Vietnamese TTS, 30s chunks)
  → OmniHuman via Poe API (face image + audio → lip-synced talking head)
  → FFmpeg (stitch chunks + subtitles + overlays + intro/outro)
  → YouTube Data API v3 (auto-upload)
```

ALL AI API calls route through **Poe Premium** (user already pays) via OpenAI-compatible endpoint at `api.poe.com`. This eliminates separate Anthropic/Replicate/ElevenLabs costs.

Poe API key: stored in `~/ai-thuc-chien/.env` as `POE_API_KEY`

## Key Scripts (all in `scripts/`)

| File | Purpose | Status |
|------|---------|--------|
| `daily_pipeline.py` | Main orchestrator — runs full pipeline | NEEDS REWRITE for Poe API |
| `tts_generator.py` | Edge TTS → Vietnamese audio | Working, but should switch to ElevenLabs via Poe |
| `avatar_generator.py` | Replicate/SadTalker → talking head | NEEDS REWRITE for OmniHuman via Poe |
| `video_composer.py` | FFmpeg composition (subtitles, overlays, watermark) | Working |
| `video-script-generator.py` | Claude API → Vietnamese video script | Working, needs Poe base_url |
| `facebook-autoposter.py` | Facebook Graph API posting | Working |
| `youtube-uploader.py` | YouTube Data API v3 upload | Working |
| `tiktok-poster.py` | TikTok Content Posting API | Working |
| `fb_news_fetcher.py` | RSS/Tavily news fetching | Working |
| `config.py` | Shared config (API keys, content pillars, prompts) | Working |

## Pending Tasks (priority order)

1. **Rewrite pipeline for Poe API** — Replace separate API calls (Anthropic, Replicate, Edge TTS) with unified Poe API endpoint. Models: Claude (script), ElevenLabs-v3 (TTS), OmniHuman (avatar).
2. **Handle OmniHuman 30s limit** — Split audio into ≤30s chunks, generate avatar clips per chunk, FFmpeg concat.
3. **Place avatar reference image** at `assets/avatar.png` (512x512+, front-facing, neutral expression).
4. **Configure `.env`** with `POE_API_KEY` (already obtained: see `.env`).
5. **Test pipeline** with `--dry-run` flag.
6. **Create YouTube channel** + OAuth2 credentials for upload API.
7. **Set up cron job** for daily automated runs.

## Brand & Content

- **Name**: AI Thực Chiến
- **Language**: Vietnamese
- **Audience**: SMB owners, e-commerce sellers (Shopee/Lazada/TikTok Shop), solopreneurs in Vietnam (25-55 age)
- **Tone**: Practical, friendly, benefit-focused ("tiết kiệm 10 giờ/tuần"), never technical jargon
- **Content split**: 40% AI news, 30% automation case studies, 20% tool reviews, 10% behind-the-scenes

## Tech Stack

- Python 3.x, FFmpeg, edge-tts, anthropic SDK, replicate SDK, google-api-python-client
- Dependencies: `scripts/requirements.txt`
- Environment: macOS Apple Silicon
- Repo: https://github.com/hohuyblon-stack/ai-thuc-chien

## Important Constraints

- All video scripts must be 100% Vietnamese, natural conversational tone
- OmniHuman accepts max 30s audio per generation — must chunk
- Poe API uses OpenAI-compatible format: `base_url="https://api.poe.com/v1"`, model names like `"Claude-3.7-Sonnet"`, `"ElevenLabs-v3"`, `"OmniHuman"`
- FFmpeg handles all video post-processing (no paid video editing tools)
- YouTube upload requires OAuth2 token stored at `youtube_token.json`
