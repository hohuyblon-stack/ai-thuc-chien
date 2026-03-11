# AI Thực Chiến — Quick Start Guide

This is the fastest way to get your automated YouTube pipeline running.

## Prerequisites (5 minutes)

1. **macOS with Apple Silicon** (M1/M2/M3+)
2. **Homebrew**: https://brew.sh
3. **API Keys**:
   - Anthropic (Claude): https://console.anthropic.com
   - Google Cloud (YouTube): https://console.cloud.google.com
   - Reddit (optional): https://reddit.com/prefs/apps

## Installation (20 minutes)

### Step 1: Clone and Initialize
```bash
cd ~
mkdir -p ai-thuc-chien && cd ai-thuc-chien
git init

# Copy this file and TECHNICAL_BLUEPRINT.md here
# Then:
python3.9 -m venv venv
source venv/bin/activate
```

### Step 2: Install Python Dependencies
```bash
cat > requirements.txt << 'EOF'
anthropic==0.28.0
praw==7.7.0
requests==2.31.0
beautifulsoup4==4.12.0
feedparser==6.0.10
edge-tts==0.2.1
google-auth-oauthlib==1.2.0
google-auth-httplib2==0.2.0
google-api-python-client==2.104.0
python-dotenv==1.0.0
opencv-python==4.8.0.76
numpy==1.24.4
EOF

pip install -r requirements.txt
```

### Step 3: Set Up Wav2Lip (15 minutes)
```bash
bash setup_wav2lip.sh
```

### Step 4: Configure API Keys
```bash
cat > .env << 'EOF'
# Anthropic
ANTHROPIC_API_KEY=sk-ant-YOUR_KEY_HERE

# Reddit (optional)
REDDIT_CLIENT_ID=YOUR_CLIENT_ID
REDDIT_CLIENT_SECRET=YOUR_CLIENT_SECRET
REDDIT_USER_AGENT=ai-thuc-chien/1.0

# YouTube
YOUTUBE_CLIENT_SECRETS_JSON=client_secrets.json
YOUTUBE_CHANNEL_ID=UCxxxxxxxx

# Optional: HackerNews, TechCrunch have no auth
EOF
```

### Step 5: Prepare Avatar
Record a 5-10 second video of yourself (or use an AI avatar from Synthesia/HeyGen):
```bash
# Save to:
mkdir -p data
# → Put your video at: data/reference_video.mp4
```

## Test Run (10 minutes)

### Test 1: News Scraping
```bash
python src/scraper.py
# Check: output/2026-03-11_stories.json created
```

### Test 2: Script Generation
```bash
python src/script_generator.py
# Check: output/2026-03-11_script.txt created
```

### Test 3: TTS Audio
```bash
python src/tts_generator.py
# Check: output/2026-03-11_audio.wav created
```

### Test 4: Avatar Animation
```bash
python src/avatar_animator.py
# Check: output/2026-03-11_avatar.mp4 created (3-5 min, be patient)
```

### Test 5: YouTube Upload
First-time only:
```bash
python src/youtube_uploader.py
# Opens browser for OAuth consent → creates token.json
```

## Run Full Pipeline

### Manual (first time verification)
```bash
bash run_daily_pipeline.sh
```

Monitor logs:
```bash
tail -f logs/pipeline.log
```

### Automate with Cron (8 AM daily)
```bash
crontab -e

# Add this line:
0 8 * * * source ~/.zprofile && /Users/huyho/ai-thuc-chien/run_daily_pipeline.sh >> /Users/huyho/ai-thuc-chien/logs/pipeline.log 2>&1

# Save and exit
```

Check it's scheduled:
```bash
crontab -l | grep ai-thuc-chien
```

## Troubleshooting

### "Python not found" in cron
Add this to top of `run_daily_pipeline.sh`:
```bash
export PATH="/opt/homebrew/bin:$PATH"
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init --path)"
```

### Wav2Lip slow on CPU
Expected! 30 seconds of video = 3-5 minutes on M-series CPU.
For faster inference, skip this for now. Upgrade to external GPU later.

### FFmpeg "Unknown encoder"
```bash
brew uninstall ffmpeg
brew install ffmpeg
ffmpeg -codecs | grep h264  # Verify output
```

### YouTube quota exceeded
You can upload 6 videos/day with free quota. If you need more:
1. Go to Google Cloud Console
2. Request quota increase (24-48 hour wait)

### Video looks blurry
Edit `run_daily_pipeline.sh` and change:
```bash
# From:
--resize_factor 2

# To:
--resize_factor 1  # Slower but higher quality
```

## File Structure (after setup)

```
ai-thuc-chien/
├── .env                      # API keys (DO NOT COMMIT)
├── .gitignore
├── requirements.txt
├── TECHNICAL_BLUEPRINT.md
├── QUICKSTART.md
├── setup_wav2lip.sh
├── run_daily_pipeline.sh
├── venv/                     # Python environment
├── src/
│   ├── scraper.py
│   ├── script_generator.py
│   ├── tts_generator.py
│   ├── avatar_animator.py
│   ├── graphics_renderer.py
│   └── youtube_uploader.py
├── data/
│   └── reference_video.mp4   # Your avatar (5-10 sec)
├── output/
│   ├── 2026-03-11_stories.json
│   ├── 2026-03-11_script.txt
│   ├── 2026-03-11_audio.wav
│   ├── 2026-03-11_avatar.mp4
│   └── 2026-03-11_youtube.mp4
├── wav2lip/
│   ├── venv/
│   └── Wav2Lip/
└── logs/
    └── pipeline.log
```

## Advanced Customization

### Change Voice
Edit `src/tts_generator.py`:
```python
VIETNAMESE_VOICES = {
    "female": "vi-VN-HoaiMyNeural",  # Change to "vi-VN-NamMinhNeural" for male
    "male": "vi-VN-NamMinhNeural"
}
```

### Change News Sources
Edit `src/scraper.py`:
```python
# Add or remove subreddits:
all_stories.extend(self.scrape_reddit('artificial', limit=3))
all_stories.extend(self.scrape_reddit('MachineLearning', limit=2))
```

### Adjust Video Encoding
Edit `run_daily_pipeline.sh`, FFmpeg section:
```bash
# For YouTube Shorts (vertical)
ffmpeg -i final.mp4 \
  -vf "scale=1080:1920,pad=1080:1920" \
  -c:v libx264 -crf 18 -preset medium \
  output.mp4

# For higher quality (bigger file):
ffmpeg -i final.mp4 \
  -c:v libx264 -crf 14 -preset slow \  # Lower CRF = better quality
  output.mp4
```

### Skip Steps (for testing)
Comment out in `run_daily_pipeline.sh`:
```bash
# python src/scraper.py  # Already ran yesterday
python src/script_generator.py
python src/tts_generator.py
# ... rest of pipeline
```

## Monitoring

### Check daily output
```bash
ls -lh output/2026-03-*

# Last video created:
stat output/2026-03-*_youtube.mp4
```

### Monitor cron execution
```bash
log stream --predicate 'process == "cron"' --level debug

# Or check system logs:
tail -100 /var/log/system.log | grep cron
```

## Next: Production Optimization (Optional)

1. **Parallel Processing**: Run scraper while TTS generates audio
2. **Multi-Voice**: Rotate between male/female for variety
3. **B-roll Database**: Add stock footage clips between segments
4. **Thumbnail Generation**: AI-generated thumbnails via DALL-E
5. **Multi-Language**: Generate Vietnamese + English versions

## Support Resources

- **Wav2Lip Issues**: See TECHNICAL_BLUEPRINT.md § Known Issues
- **YouTube API**: https://developers.google.com/youtube/v3/docs
- **Claude API Docs**: https://docs.anthropic.com
- **Edge TTS Voices**: `edge-tts --list-voices`

## Estimated Daily Costs

- Claude API: ~$0.80/day (~2,000 tokens)
- YouTube API: Free (10,000 units/day)
- Edge TTS: Free
- **Total**: ~$24/month for 365 videos/year

---

**Happy automating! 🚀**

Start with the test run, then schedule the cron job.
Your first automated video will upload tomorrow morning!
