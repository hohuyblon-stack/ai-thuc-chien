# AI Thuc Chien - Social Media Automation

Multi-platform social media automation for the "AI Thuc Chien" brand.
AI automation content for Vietnamese SMB owners.

## Project Structure

```
ai-thuc-chien/
  branding/         # Logo, cover photo, brand assets HTML
  scripts/          # Automation scripts (Facebook, YouTube, TikTok)
  strategy/         # Platform strategies, content calendars, setup guides
```

## Platforms

| Platform | Status | Notes |
|----------|--------|-------|
| Facebook Page | Created (Step 2/5) | Profile pic + cover not uploaded yet |
| YouTube | Strategy done | Need to create channel manually |
| TikTok | Strategy done | Need to create account manually |

## Scripts

- `facebook-autoposter.py` - Daily FB posting via Graph API
- `fb_content_generator.py` - Claude API Vietnamese copywriting
- `fb_news_fetcher.py` - Tavily/RSS AI news aggregation
- `youtube-uploader.py` - YouTube Data API upload automation
- `video-script-generator.py` - YouTube video script generation
- `tiktok-poster.py` - TikTok Content Posting API
- `tiktok-script-generator.py` - TikTok short-form script generation
- `setup-cron.sh` - Cron job scheduling for all platforms

## Required API Keys

Store in `~/.claude/secrets.env`:
- `ANTHROPIC_API_KEY` - Claude API for content generation
- `TAVILY_API_KEY` - News fetching
- `FB_PAGE_ACCESS_TOKEN` - Facebook Graph API
- `YOUTUBE_API_KEY` - YouTube Data API
- `TIKTOK_ACCESS_TOKEN` - TikTok API

## Next Steps

See TODO.md for the prioritized task list.
