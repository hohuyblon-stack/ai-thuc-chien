# AI Thuc Chien - Social Media Automation

Multi-platform social media automation for the "AI Thuc Chien" brand.
AI automation content for Vietnamese SMB owners.

## Project Structure

```
ai-thuc-chien/
  branding/         # Logo, cover photo, brand assets HTML
  scripts/          # Automation scripts (Facebook, YouTube, TikTok)
  strategy/         # Platform strategies, content calendars, setup guides
  assets/           # Avatar image for video generation
  output/           # Generated videos (daily output by date)
  logs/             # Pipeline logs
```

## Platforms

| Platform | Status | Pipeline |
|----------|--------|----------|
| Facebook Page | Created (Step 2/5) | Text post autoposter (daily) |
| YouTube | Strategy done | Full video pipeline: news → script → TTS → avatar → compose → upload |
| TikTok | Strategy done | Full video pipeline: news → script → TTS → avatar → vertical compose → upload |

## Daily Video Pipeline

The unified `daily_pipeline.py` handles both YouTube and TikTok:

```
News (Tavily/RSS) → Script (Claude) → TTS (Edge TTS) → Avatar (SadTalker/Replicate)
                                                             ↓
                                              ┌──────────────┴──────────────┐
                                              ↓                             ↓
                                     Landscape 1920x1080            Vertical 1080x1920
                                     (YouTube long-form)           (TikTok / YT Shorts)
                                              ↓                             ↓
                                     Upload to YouTube             Upload to TikTok
```

```bash
# Full pipeline (YouTube + TikTok)
python3 scripts/daily_pipeline.py

# YouTube only
python3 scripts/daily_pipeline.py --platform youtube

# TikTok only (short-form)
python3 scripts/daily_pipeline.py --platform tiktok --format short

# Dry run (no upload)
python3 scripts/daily_pipeline.py --dry-run
```

## Scripts

- `daily_pipeline.py` - Unified daily pipeline for YouTube + TikTok
- `facebook-autoposter.py` - Daily FB posting via Graph API
- `fb_content_generator.py` - Claude API Vietnamese copywriting
- `fb_news_fetcher.py` - Tavily/RSS AI news aggregation
- `youtube-uploader.py` - YouTube Data API upload automation
- `video-script-generator.py` - YouTube video script generation
- `tiktok-poster.py` - TikTok Content Posting API v2
- `tiktok-script-generator.py` - TikTok short-form script generation
- `tts_generator.py` - Vietnamese TTS (Edge TTS)
- `avatar_generator.py` - Talking-head avatar (SadTalker/Replicate)
- `video_composer.py` - FFmpeg composition (landscape + vertical)
- `setup-cron.sh` - Cron job scheduling for all platforms

## Required API Keys

Store in `.env` (copy from `.env.example`):
- `ANTHROPIC_API_KEY` - Claude API for content generation
- `TAVILY_API_KEY` - News fetching
- `REPLICATE_API_TOKEN` - Avatar video generation
- `FB_PAGE_ACCESS_TOKEN` - Facebook Graph API
- `YOUTUBE_CLIENT_ID/SECRET` - YouTube Data API (OAuth2)
- `TIKTOK_ACCESS_TOKEN` - TikTok Content Posting API v2

## Next Steps

See TODO.md for the prioritized task list.
