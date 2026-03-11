# AI Thực Chiến TikTok Automation — Setup Guide

## Overview
This automation suite includes:
1. **TikTok Strategy Document** — Comprehensive strategy & best practices
2. **Content Calendar** — 20 video ideas for Month 1
3. **TikTok Poster** — Python script to automate posting + caption/hashtag generation
4. **Script Generator** — Python script to generate TikTok video scripts in Vietnamese

---

## Prerequisites

### System Requirements
- Python 3.8 or higher
- macOS, Linux, or Windows
- 2GB RAM minimum
- Internet connection

### Accounts & API Keys Required
1. **TikTok Developer Account** (for posting API)
2. **Anthropic Claude API** (for script generation & captions)

---

## Installation

### 1. Create Python Virtual Environment
```bash
cd /tmp/ai-thuc-chien-brand
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# or: venv\Scripts\activate  # Windows
```

### 2. Install Dependencies
```bash
pip install --upgrade pip
pip install anthropic requests python-dotenv
```

### 3. Create `.env` File
```bash
# Create .env in /tmp/ai-thuc-chien-brand/
cat > .env << 'EOF'
CLAUDE_API_KEY=your_claude_key_here
TIKTOK_ACCESS_TOKEN=your_tiktok_token_here
TIKTOK_CLIENT_KEY=your_client_key_here
TIKTOK_CLIENT_SECRET=your_client_secret_here
EOF
```

---

## API Setup Instructions

### A. Claude API (Anthropic)

1. Visit https://console.anthropic.com
2. Sign up or log in
3. Go to "API Keys" section
4. Create new API key
5. Copy the key into `.env`:
```
CLAUDE_API_KEY=sk-ant-xxxxxxxxxxxxxx
```

Test:
```bash
python scripts/tiktok-script-generator.py generate \
  --topic "ChatGPT for e-commerce" \
  --category tutorial --save
```

### B. TikTok Content Posting API

**Step 1**: Create TikTok Developer Account
- Visit https://developers.tiktok.com/
- Register for developer account
- Verify email

**Step 2**: Create Application
- Go to "Apps" section
- Click "Create an app"
- Choose "Content Posting API"
- Fill app info and accept terms
- Wait for approval (24-48 hours)

**Step 3**: Get Credentials
- Find Client Key (App ID)
- Find Client Secret (App Secret)

**Step 4**: Get Access Token (OAuth)
```bash
# 1. Build authorization URL
https://www.tiktok.com/oauth/authorize?client_key=YOUR_CLIENT_KEY&redirect_uri=YOUR_REDIRECT_URI&response_type=code&scope=video.upload&state=random_state

# 2. User authorizes app
# 3. Receive authorization code
# 4. Exchange for access token:

curl -X POST https://open.tiktokapis.com/v1/oauth/token/ \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_key=YOUR_CLIENT_KEY&client_secret=YOUR_CLIENT_SECRET&code=AUTH_CODE&grant_type=authorization_code"
```

**Step 5**: Add to `.env`
```
TIKTOK_ACCESS_TOKEN=v1.xxxxx
TIKTOK_CLIENT_KEY=xxxxx
TIKTOK_CLIENT_SECRET=xxxxx
```

---

## Quick Start

### 1. Generate Your First Script
```bash
# Interactive mode
python scripts/tiktok-script-generator.py interactive

# Or direct command
python scripts/tiktok-script-generator.py generate \
  --topic "5 ChatGPT prompts for sellers" \
  --category tutorial --save
```

Output: Markdown + JSON files in `generated_scripts/`

### 2. Add Video to Queue
```bash
python scripts/tiktok-poster.py add \
  --video /path/to/video.mp4 \
  --title "5 ChatGPT prompts for sellers" \
  --category tutorial \
  --schedule "2024-03-15 12:00:00"
```

### 3. Check Status
```bash
python scripts/tiktok-poster.py status
```

### 4. Post Due Videos
```bash
python scripts/tiktok-poster.py process
```

### 5. Generate Captions
```bash
python scripts/tiktok-poster.py gen-caption \
  --topic "AI tool comparison" \
  --category tool_review
```

### 6. Generate Hashtags
```bash
python scripts/tiktok-poster.py gen-hashtags \
  --topic "ChatGPT automation" \
  --category tutorial
```

---

## File Structure

```
/tmp/ai-thuc-chien-brand/
├── tiktok-strategy.md              # Strategy document
├── tiktok-content-calendar.md      # Month 1 calendar (20 videos)
├── SETUP_GUIDE.md                 # This file
│
├── scripts/
│   ├── tiktok-poster.py           # Post videos + captions
│   └── tiktok-script-generator.py # Generate scripts
│
├── generated_scripts/             # Auto-created
├── content_queue.json            # Queue of videos
├── posted_videos.json            # Log of posted
└── tiktok_poster.log             # Activity log
```

---

## Workflow Examples

### Full Workflow: Script to Post
```bash
# 1. Generate script
python scripts/tiktok-script-generator.py generate \
  --topic "Midjourney v6 for product photography" \
  --category tool_review --save

# 2. Review script
cat generated_scripts/Midjourney_*.md

# 3. Record video based on script
# (use camera/editing software)

# 4. Add to queue
python scripts/tiktok-poster.py add \
  --video my_video.mp4 \
  --title "Midjourney v6 for product photography" \
  --category tool_review \
  --schedule "2024-03-17 12:00:00"

# 5. Post
python scripts/tiktok-poster.py process
```

### Batch Generate Month's Content
Create `topics.json`:
```json
[
  {
    "topic": "ChatGPT 4 Turbo just dropped",
    "category": "news",
    "duration": 25
  },
  {
    "topic": "3 AI prompts for product descriptions",
    "category": "tutorial",
    "duration": 30
  }
]
```

Run:
```bash
python scripts/tiktok-script-generator.py batch --file topics.json
```

---

## Security Tips

- **Never commit `.env`** (has API keys)
- Add to `.gitignore`:
  ```
  .env
  venv/
  *.log
  __pycache__/
  ```
- Rotate API keys monthly
- Use environment variables only

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "TIKTOK_ACCESS_TOKEN not found" | Add token to `.env` |
| "401 Unauthorized" from TikTok | Refresh access token, check expiry |
| "Invalid video file" | Use MP4, H.264 codec, 1080p min |
| Claude API timeout | Retry in 60s or check status.anthropic.com |
| Poor script quality | Be more specific in topic, try different category |

---

## Next Steps

1. Set up API keys (Claude + TikTok)
2. Test with single script
3. Generate 5 scripts (use content calendar)
4. Record videos
5. Add to queue and schedule
6. Set up cron for automation (optional)
7. Monitor analytics

---

## Support Resources

- **TikTok API Docs**: https://developers.tiktok.com/doc/content-posting-api
- **Claude API Docs**: https://docs.anthropic.com
- **Strategy Guide**: `tiktok-strategy.md`
- **Content Ideas**: `tiktok-content-calendar.md`

Good luck building AI Thực Chiến on TikTok! 🚀
