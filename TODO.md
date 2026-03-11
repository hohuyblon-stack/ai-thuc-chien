# AI Thuc Chien - TODO

## Priority 1: Facebook Page Setup (incomplete)

- [ ] Upload profile picture to Facebook Page (image at branding/ai-thuc-chien-profile-360x360.png)
- [ ] Export cover photo from branding/index.html (html2canvas didn't save it last time)
- [ ] Upload cover photo to Facebook Page
- [ ] Complete Step 3-5 of Facebook Page creation wizard
- [ ] Create Meta Developer App (developers.facebook.com)
- [ ] Get Page Access Token with `pages_manage_posts` + `pages_read_engagement` permissions
- [ ] Test Facebook autoposter script with real token

## Priority 2: YouTube Setup

- [ ] Create YouTube channel manually (security restriction)
- [ ] Set up YouTube Data API credentials (Google Cloud Console)
- [ ] Download credentials.json → run `python3 scripts/youtube-uploader.py --auth`
- [ ] Place avatar image at `assets/avatar.png` (512x512+ clear face photo)
- [ ] Test pipeline: `python3 scripts/daily_pipeline.py --platform youtube --dry-run`
- [ ] Generate first batch of video scripts with video-script-generator.py

## Priority 3: TikTok Setup

- [ ] Create TikTok account manually (security restriction)
- [ ] Create TikTok Developer app (developers.tiktok.com)
- [ ] Apply for Content Posting API v2 access
- [ ] Get access token via OAuth2 flow
- [ ] Test pipeline: `python3 scripts/daily_pipeline.py --platform tiktok --format short --dry-run`
- [ ] Generate first batch of scripts with tiktok-script-generator.py

## Priority 4: Automation

- [ ] Configure .env file from .env.example
- [ ] Install Python dependencies: pip install -r requirements.txt
- [ ] Install FFmpeg (required for video composition)
- [ ] Run setup-cron.sh to schedule daily posts (Facebook + YouTube + TikTok)
- [ ] Monitor first week of automated posts
- [ ] Tune content generation prompts based on engagement

## Done

- [x] Market research on Vietnamese AI/automation Facebook landscape
- [x] Brand name chosen: "AI Thuc Chien"
- [x] Facebook Page created (name, category, bio filled)
- [x] Brand assets designed (profile pic + cover photo HTML)
- [x] Profile picture exported as PNG
- [x] YouTube strategy + content calendar written
- [x] TikTok strategy + content calendar written
- [x] Facebook autoposter scripts built
- [x] YouTube automation scripts built
- [x] TikTok automation scripts built
- [x] social-media-clip-creator agent installed
- [x] social-content skill updated with comprehensive guide
- [x] Video composer supports vertical format (1080x1920) for TikTok/Shorts
- [x] Unified daily pipeline supports YouTube + TikTok (daily_pipeline.py)
- [x] TikTok poster updated to Content Posting API v2
- [x] TikTok script generator updated with latest Claude model
- [x] Cron setup supports all 3 platforms (Facebook + YouTube + TikTok)
- [x] Environment variables standardized (ANTHROPIC_API_KEY)
- [x] .env.example updated with all required vars
- [x] requirements.txt updated for full pipeline
