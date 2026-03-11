# AI Thực Chiến — TikTok Content Strategy & Automation Pipeline

**Complete TikTok strategy, content calendar, and automation tools for Vietnamese AI/automation brand targeting SMBs, e-commerce sellers, and solopreneurs.**

---

## Overview

This comprehensive package includes:

### 📋 Documents
- **tiktok-strategy.md** — Complete 12-section TikTok strategy guide
- **tiktok-content-calendar.md** — 20 video ideas for Month 1

### 🤖 Automation Scripts
- **tiktok-poster.py** — Post videos, generate captions (Vietnamese), manage queue
- **tiktok-script-generator.py** — Generate complete TikTok scripts in Vietnamese

### 📚 Documentation
- **SETUP_GUIDE.md** — Installation, API setup, troubleshooting

---

## Quick Start (5 minutes)

### 1. Install
```bash
cd /tmp/ai-thuc-chien-brand
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Set Up APIs
```bash
cp .env.example .env
# Edit .env with Claude API key
```

### 3. Generate Script
```bash
python scripts/tiktok-script-generator.py interactive
```

---

## File Structure

```
/tmp/ai-thuc-chien-brand/
├── tiktok-strategy.md           # Strategy guide
├── tiktok-content-calendar.md   # Month 1 calendar (20 videos)
├── SETUP_GUIDE.md              # Installation & API setup
├── README.md                   # This file
│
├── scripts/
│   ├── tiktok-poster.py        # Post videos + captions
│   └── tiktok-script-generator.py  # Generate scripts
│
├── requirements.txt
├── .env.example
├── .gitignore
│
├── generated_scripts/          # Auto-created
├── content_queue.json         # Videos to post
└── posted_videos.json         # Posted log
```

---

## Commands

### Generate Scripts
```bash
# Interactive
python scripts/tiktok-script-generator.py interactive

# Direct
python scripts/tiktok-script-generator.py generate \
  --topic "ChatGPT for sellers" --category tutorial --save

# Variations
python scripts/tiktok-script-generator.py variations \
  --topic "AI for business" --count 3 --save

# Batch
python scripts/tiktok-script-generator.py batch --file topics.json
```

### Manage Videos
```bash
# Add to queue
python scripts/tiktok-poster.py add \
  --video video.mp4 --title "..." --category tutorial

# Check status
python scripts/tiktok-poster.py status

# Post scheduled videos
python scripts/tiktok-poster.py process

# Generate caption
python scripts/tiktok-poster.py gen-caption \
  --topic "AI news" --category news

# Generate hashtags
python scripts/tiktok-poster.py gen-hashtags \
  --topic "ChatGPT automation" --category tutorial
```

---

## Content Categories

| Category | Best For | Tone |
|----------|----------|------|
| **news** | AI announcements, releases | Excited, informative |
| **tutorial** | How-to guides, steps | Helpful, clear |
| **case_study** | Real results, ROI | Inspiring, credible |
| **tool_review** | Feature demos, comparisons | Honest, practical |
| **bts** | Behind-the-scenes, relatable | Authentic, casual |

---

## Strategy at a Glance

### Content Mix
- **AI News (40%)** — Breaking news, product launches
- **Automation Wins (30%)** — Case studies, results
- **Tool Reviews (20%)** — Feature demos
- **Behind the Scenes (10%)** — Community building

### Posting Schedule
- **Frequency**: 5 videos/week (Mon-Fri)
- **Times**: 12:00 PM (lunch), 6:00 PM (evening)
- **Consistency**: Algorithm boost for same time

### Month 1 Targets
- 500-1000 new followers
- 100k-150k total views
- 50-60% avg completion rate
- 1-2 viral videos (50k+ views)

### Monetization Path
1. **0-10k**: Audience building
2. **10k-50k**: Creator Fund + Affiliate
3. **50k-100k**: Brand deals + Products
4. **100k+**: All channels + Consulting

---

## Setup (Detailed)

### Prerequisites
- Python 3.8+
- Claude API key (https://console.anthropic.com)
- TikTok API access (optional, for auto-posting)

### Installation
```bash
cd /tmp/ai-thuc-chien-brand
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# or: venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### API Configuration
1. **Claude**: Get key from console.anthropic.com, add to .env
2. **TikTok**: See SETUP_GUIDE.md for detailed OAuth flow

See **SETUP_GUIDE.md** for full instructions.

---

## Example Workflows

### Full Pipeline
```
1. Generate script
   python scripts/tiktok-script-generator.py generate ...

2. Review & edit

3. Record video

4. Add to queue
   python scripts/tiktok-poster.py add ...

5. Schedule posting
   python scripts/tiktok-poster.py add ... --schedule "2024-03-15 12:00:00"

6. Auto-post
   python scripts/tiktok-poster.py process
```

### Batch Content Creation
```bash
# Create topics.json with 20 video ideas
python scripts/tiktok-script-generator.py batch --file topics.json
# All scripts auto-generated and saved
```

---

## Included Documents

### tiktok-strategy.md (15+ pages)
- Profile setup & bio
- 6 content format recommendations
- Posting schedule & best times
- 4-tier hashtag strategy with examples
- 7 growth tactics (Vietnamese market specific)
- Sound & music strategy
- 6-stage monetization path
- YouTube repurposing guide
- KPIs & metrics
- 30-day launch plan

### tiktok-content-calendar.md (20 videos)
- Week 1: Foundation (5 videos)
- Week 2: Scaling (5 videos)
- Week 3: Viral attempts (5 videos)
- Week 4: Optimization (5 videos)
- Each with: hook, format, structure, hashtags, visual notes

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "CLAUDE_API_KEY not found" | Add to .env |
| "Invalid video file" | Use MP4, H.264, 1080p min |
| "401 Unauthorized" from TikTok | Refresh token, check expiry |
| Poor script quality | More specific topic, try different category |
| API timeout | Retry in 60s, check status.anthropic.com |

See SETUP_GUIDE.md for more help.

---

## Next Steps

1. **Install** (see SETUP_GUIDE.md)
2. **Read strategy** (tiktok-strategy.md)
3. **Review calendar** (tiktok-content-calendar.md)
4. **Generate scripts** (script generator)
5. **Record videos**
6. **Schedule posts** (poster tool)
7. **Launch & monitor**

---

## Resources

- **TikTok API**: https://developers.tiktok.com/doc/content-posting-api
- **Claude API**: https://docs.anthropic.com
- **Creator Fund**: https://www.tiktok.com/creators/creator-portal/
- **Strategy**: See tiktok-strategy.md
- **Ideas**: See tiktok-content-calendar.md

---

## Quick Ref

```bash
# Most common
python scripts/tiktok-script-generator.py interactive
python scripts/tiktok-poster.py status
python scripts/tiktok-poster.py process
```

---

**Built for AI Thực Chiến — Practical AI for Vietnamese SMBs**

Good luck! 🚀
