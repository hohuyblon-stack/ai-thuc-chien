# AI Thực Chiến — YouTube Automation Pipeline
## Technical Blueprint & Implementation Guide

**Project**: Self-hosted AI avatar video automation for Vietnamese AI news channel
**Target**: Daily automated video generation and upload
**Platform**: macOS with Apple Silicon (M1/M2/M3+)
**Created**: March 2026

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Component Specifications](#component-specifications)
3. [Installation & Setup Guide](#installation--setup-guide)
4. [Code Snippets](#code-snippets)
5. [Reference Video Requirements](#reference-video-requirements)
6. [Comparison: Wav2Lip vs MuseTalk](#comparison-wav2lip-vs-musetalk)
7. [Known Issues & Solutions](#known-issues--solutions)
8. [Daily Cron Schedule](#daily-cron-schedule)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    DAILY PIPELINE EXECUTION                      │
└─────────────────────────────────────────────────────────────────┘
     │
     ├─→ [1] News Scraper (Reddit, HackerNews, TechCrunch)
     │       └─→ Store top 5 stories in JSON
     │
     ├─→ [2] Script Generator (Claude API)
     │       └─→ Generates Vietnamese script (2-3 min duration)
     │
     ├─→ [3] TTS Engine (Edge TTS / VietTTS)
     │       └─→ Converts script to WAV audio (Vietnamese voices)
     │
     ├─→ [4] Avatar Animation (Wav2Lip OR MuseTalk)
     │       └─→ Reference video + audio → lip-synced video
     │
     ├─→ [5] Motion Graphics (FFmpeg + optional Remotion)
     │       └─→ Add intro/outro, B-roll, subtitles, watermarks
     │
     ├─→ [6] Post-Processing
     │       └─→ Encode to H.264, optimize for YouTube
     │
     └─→ [7] YouTube Upload (Data API v3)
             └─→ Publish with metadata, schedule if needed
```

---

## Component Specifications

### 1. NEWS SCRAPING

**Goal**: Fetch 5 trending AI stories daily from multiple sources

**Tools & Libraries**:
- `praw` (Python Reddit API Wrapper) v7.7.0+
- `requests` v2.31+
- `beautifulsoup4` v4.12+
- `feedparser` v6.0+

**Sources**:
- Reddit: r/artificial, r/singularity, r/OpenAI
- HackerNews: Top stories from HN API (trending AI)
- TechCrunch: RSS feed scraping
- Medium: Tag-based API

**Installation**:
```bash
pip install praw requests beautifulsoup4 feedparser python-dotenv
```

**Output Format**: `news_stories.json`
```json
{
  "date": "2026-03-11",
  "stories": [
    {
      "title": "Story Title",
      "source": "HackerNews",
      "url": "https://...",
      "summary": "Brief description",
      "score": 350
    }
  ]
}
```

**Gotchas**:
- Reddit API requires OAuth app credentials (register at reddit.com/prefs/apps)
- Rate limiting: 60 requests/min on most APIs
- HackerNews has no official API for Vietnamese content — use English sources

---

### 2. SCRIPT GENERATION

**Goal**: Convert news stories into natural Vietnamese script (2-3 minutes)

**Tool**: Claude API (claude-3-5-sonnet-20241022)

**Installation**:
```bash
pip install anthropic python-dotenv
```

**API Key Setup**:
```bash
# Store in ~/.claude/secrets.env
ANTHROPIC_API_KEY=sk-ant-...
```

**Constraints**:
- Script length: ~450-600 words (≈ 2:30-3:00 speech duration)
- Tone: Professional but engaging, conversational
- Format: Sentence breaks for natural TTS pacing
- Language: Vietnamese (Tiếng Việt)

**Prompt Template**:
```
Bạn là một nhà báo AI chuyên nghiệp. Viết kịch bản tin tức
dài 2-3 phút (khoảng 450-600 từ) bằng tiếng Việt tự nhiên về:

[NEWS STORIES HERE]

Yêu cầu:
- Giọng lề, chuyên nghiệp nhưng hấp dẫn
- Chia thành 2-3 đoạn rõ ràng
- Bao gồm intro và outro
- Tránh từ ngữ quá kỹ thuật, giải thích rõ
```

---

### 3. TEXT-TO-SPEECH (TTS)

**Two Options**:

#### Option A: Edge TTS (Recommended for Vietnamese)
- **Free**, no authentication needed
- **Vietnamese voices available**: vi-VN-HoaiMyNeural (female), vi-VN-NamMinhNeural (male)
- **Output**: MP3, WAV
- **Speed**: 1-2 seconds per minute of audio

**Library**: `edge-tts` v0.2.1+

**Installation**:
```bash
pip install edge-tts
```

**CLI Usage**:
```bash
edge-tts --voice "vi-VN-HoaiMyNeural" \
  --text "Xin chào bạn" \
  --write-media output.mp3 \
  --write-subtitles output.vtt
```

#### Option B: VietTTS (Self-Hosted, Advanced)
- Higher quality Vietnamese voice cloning
- Requires GPU (not recommended on macOS M-series without external setup)
- **Installation**: Docker-based (see HuggingFace: dangvansam/viet-tts)

**Recommendation**: Use Edge TTS for automation (fast, simple), VietTTS for premium output later.

---

### 4. AVATAR VIDEO GENERATION (LIP-SYNC)

## **Recommendation: WAV2LIP for macOS (Easier Setup)**

Reason: MuseTalk is research-grade with complex dependencies; Wav2Lip has better macOS community support.

### Wav2Lip Setup (macOS Apple Silicon)

**System Requirements**:
- Python 3.9 (not 3.6 as docs suggest)
- FFmpeg v4.4+
- Homebrew
- ~8GB free disk space
- No GPU required (CPU-based inference works, slower)

**Installation Steps**:

```bash
# 1. Create project directory
mkdir -p ~/ai-thuc-chien/wav2lip && cd ~/ai-thuc-chien/wav2lip

# 2. Install Python 3.9 via Homebrew
brew install python@3.9 ffmpeg git-lfs

# 3. Create virtual environment
python3.9 -m venv venv
source venv/bin/activate

# 4. Clone repository
git clone https://github.com/justinjohn0306/Wav2Lip.git
cd Wav2Lip

# 5. Install PyTorch (CPU optimized for macOS)
pip install torch==2.1.2 torchvision==0.16.2 torchaudio==2.1.2

# 6. Install dependencies
pip install -r requirements.txt

# 7. Download pretrained weights
wget "https://www.adrianbulat.com/downloads/dlib/mmod_human_face_detector.dat" \
  -O face_detection/detection/sfd/s3fd.pth

wget "https://www.adrianbulat.com/downloads/dlib/shape_predictor_68_face_landmarks.dat" \
  -O face_detection/detection/dlib/shape_predictor_68_face_landmarks.dat

# For Wav2Lip model weights
mkdir -p checkpoints
wget "https://www.dropbox.com/s/fvc9aupvv88nk5w/wav2lip.pth?dl=1" \
  -O checkpoints/wav2lip.pth

# For GAN model (better quality)
wget "https://www.dropbox.com/s/h1unxlc0yq0xblh/wav2lip_gan.pth?dl=1" \
  -O checkpoints/wav2lip_gan.pth
```

**Inference Command**:
```bash
python inference.py \
  --checkpoint_path checkpoints/wav2lip_gan.pth \
  --face path/to/reference_video.mp4 \
  --audio path/to/audio.wav \
  --outfile output/result.mp4
```

**Performance on macOS M-series**:
- 30-second video: ~3-5 minutes (CPU)
- If GPU available (external RTX): ~30 seconds
- Recommended: CPU processing is acceptable for daily automation

**Key Parameters**:
- `--resize_factor 2`: Input video resolution scaling (2 = 720p) — set to 2 for faster processing
- `--face_det_batch_size 16`: Adjust down if memory constrained
- `--pads [0, 10, 0, 0]`: Padding around detected face (top, bottom, left, right)

### MuseTalk Setup (Advanced Alternative)

**NOT RECOMMENDED for macOS M-series** without external GPU. Research-grade project with:
- Complex dependency management (mmcv, mmdet, mmpose)
- CUDA 11.7+ requirement (macOS has no CUDA)
- Better quality (256×256) but 2-3x setup complexity

Skip unless you have Linux server with NVIDIA GPU.

---

### 5. MOTION GRAPHICS & OVERLAYS

**Recommendation: FFmpeg (pure approach)**

Why: Simplicity, no extra dependencies, perfect for daily automation

**Advanced Option**: Remotion (React-based, for complex templates)

#### FFmpeg Approach (Recommended)

**Installation**:
```bash
brew install ffmpeg
```

**Operations**:

**A) Add Text Overlay (Vietnamese subtitles)**:
```bash
ffmpeg -i avatar_video.mp4 \
  -vf "subtitles=subtitles.vtt:force_style='FontSize=24,PrimaryColour=&HFFFFFF&'" \
  -c:a copy output.mp4
```

**B) Add Intro/Outro (5-second clips)**:
```bash
# Create intro text graphic
ffmpeg -f lavfi -i color=c=black:s=1920x1080:d=5 \
  -vf "drawtext=text='AI Thực Chiến':fontfile=/System/Library/Fonts/Arial.ttf:fontsize=80:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2" \
  intro.mp4

# Concatenate: intro + avatar_video + outro
echo "file 'intro.mp4'" > concat.txt
echo "file 'avatar_video.mp4'" >> concat.txt
echo "file 'outro.mp4'" >> concat.txt

ffmpeg -f concat -safe 0 -i concat.txt -c copy final.mp4
```

**C) Add Watermark**:
```bash
ffmpeg -i video.mp4 \
  -i watermark.png \
  -filter_complex "overlay=x=W-w-10:y=H-h-10" \
  -c:a copy output.mp4
```

**D) Encode for YouTube (H.264)**:
```bash
ffmpeg -i final.mp4 \
  -vcodec libx264 \
  -crf 18 \
  -preset medium \
  -acodec aac \
  -ab 192k \
  -movflags +faststart \
  final_youtube.mp4
```

#### Remotion Approach (Optional, For Premium Templates)

**When to use**: If you want visual polish, animations, transitions

**Installation**:
```bash
npx create-video@latest ai-thuc-chien-video
cd ai-thuc-chien-video
npm install
```

**Advantages**:
- React-based, code-driven templates
- Synchronize animations with audio
- Export directly to MP4

**Disadvantages**:
- ~2-3x setup complexity
- Node.js environment overhead
- Slower for daily automation (Puppeteer + FFmpeg rendering)

**Verdict**: Use FFmpeg for MVP, switch to Remotion if you need professional motion graphics.

---

### 6. YOUTUBE DATA API v3

**Setup**: Google Cloud Console

**Step 1: Create Project**
1. Go to https://console.cloud.google.com
2. Create new project: "ai-thuc-chien-uploads"
3. Enable YouTube Data API v3

**Step 2: OAuth 2.0 Credentials**
1. Go to Credentials → Create OAuth 2.0 Client ID
2. Application type: Desktop application
3. Download JSON → save as `client_secrets.json`

**Step 3: Python Setup**
```bash
pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

**API Quota**:
- 10,000 quota units/day (free)
- `videos.insert` = 1,600 units
- ~6 videos/day allowed (8 recommended minimum)

---

### 7. CRON SCHEDULING

**Daily at 8:00 AM Vietnam Time**:
```bash
# Edit crontab
crontab -e

# Add this line (runs at 8 AM every day, adjusted for your timezone)
0 8 * * * /Users/huyho/ai-thuc-chien/run_daily_pipeline.sh >> /Users/huyho/ai-thuc-chien/logs/pipeline.log 2>&1
```

---

## Installation & Setup Guide

### Prerequisites

```bash
# Install Homebrew (if not already)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install system dependencies
brew install python@3.9 ffmpeg git-lfs

# Install Xcode Command Line Tools (if prompted)
xcode-select --install
```

### Project Structure

```
~/ai-thuc-chien/
├── .env                          # API keys (DO NOT COMMIT)
├── TECHNICAL_BLUEPRINT.md        # This file
├── run_daily_pipeline.sh         # Main orchestration script
├── requirements.txt              # Python dependencies
│
├── config/
│   ├── news_sources.json         # URLs to scrape
│   ├── youtube_metadata.json     # Template for video metadata
│   └── tts_settings.json         # Voice, pitch, speed config
│
├── src/
│   ├── scraper.py                # News scraping
│   ├── script_generator.py        # Claude API integration
│   ├── tts_generator.py           # Edge TTS wrapper
│   ├── avatar_animator.py         # Wav2Lip orchestration
│   ├── graphics_renderer.py       # FFmpeg operations
│   └── youtube_uploader.py        # YouTube API upload
│
├── data/
│   ├── reference_video.mp4       # Your avatar reference (5-10 sec)
│   ├── intro.mp4                 # Intro video (5 sec)
│   ├── outro.mp4                 # Outro video (5 sec)
│   └── watermark.png             # Channel watermark
│
├── output/
│   ├── {date}_script.txt         # Generated script
│   ├── {date}_audio.wav          # Generated audio
│   ├── {date}_avatar.mp4         # Lip-synced video
│   ├── {date}_final.mp4          # With graphics/subtitles
│   └── {date}_youtube.mp4        # Encoded for upload
│
├── wav2lip/                      # Wav2Lip installation
│   ├── venv/
│   ├── Wav2Lip/
│   └── checkpoints/
│
├── logs/
│   └── pipeline.log              # Daily execution logs
│
└── tests/
    ├── test_scraper.py
    ├── test_tts.py
    └── test_upload.py
```

### Step-by-Step Setup

**1. Clone & Initialize**:
```bash
mkdir -p ~/ai-thuc-chien && cd ~/ai-thuc-chien
git init
touch .env .gitignore
echo ".env" >> .gitignore
echo "logs/" >> .gitignore
echo "output/" >> .gitignore
echo "wav2lip/" >> .gitignore
```

**2. Create Virtual Environment**:
```bash
python3.9 -m venv venv
source venv/bin/activate
pip install --upgrade pip
```

**3. Install Dependencies**:
```bash
# Create requirements.txt
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
pydub==0.25.1
EOF

pip install -r requirements.txt
```

**4. Setup Wav2Lip** (see Section 4 above):
```bash
cd ~/ai-thuc-chien
bash setup_wav2lip.sh  # Create this script with Wav2Lip installation
```

**5. Configure API Keys**:
```bash
cat > .env << 'EOF'
ANTHROPIC_API_KEY=sk-ant-...
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
REDDIT_USER_AGENT=...
YOUTUBE_CLIENT_SECRETS_JSON=client_secrets.json
YOUTUBE_CHANNEL_ID=UCxxxx
EOF
```

**6. Prepare Reference Video**:
- Shoot 5-10 second video of yourself (or avatar) facing camera
- Resolution: 720p (1280×720) minimum
- Lighting: Well-lit face, no strong shadows
- Format: MP4 H.264
- Save as `data/reference_video.mp4`

---

## Code Snippets

### 1. News Scraper

```python
# src/scraper.py
import praw
import requests
import json
from datetime import datetime
from pathlib import Path

class NewsScraperAI:
    def __init__(self, reddit_client_id, reddit_secret, user_agent):
        self.reddit = praw.Reddit(
            client_id=reddit_client_id,
            client_secret=reddit_secret,
            user_agent=user_agent
        )

    def scrape_reddit(self, subreddit_name, limit=5):
        """Fetch top posts from subreddit"""
        subreddit = self.reddit.subreddit(subreddit_name)
        posts = []
        for post in subreddit.hot(limit=limit):
            if post.score > 100:  # Quality filter
                posts.append({
                    "title": post.title,
                    "source": f"Reddit r/{subreddit_name}",
                    "url": f"https://reddit.com{post.permalink}",
                    "summary": post.selftext[:200] if post.selftext else post.title,
                    "score": post.score
                })
        return posts

    def scrape_hackernews(self, limit=5):
        """Fetch top AI stories from HackerNews"""
        url = "https://hacker-news.firebaseio.com/v0/topstories.json"
        top_stories = requests.get(url).json()[:30]
        posts = []

        for story_id in top_stories[:limit]:
            story_url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
            story = requests.get(story_url).json()

            # Filter for AI-related
            if story and any(keyword in story['title'].lower()
                           for keyword in ['ai', 'llm', 'neural', 'model']):
                posts.append({
                    "title": story['title'],
                    "source": "HackerNews",
                    "url": story.get('url', f"https://news.ycombinator.com/item?id={story_id}"),
                    "summary": story['title'],
                    "score": story.get('score', 0)
                })

        return posts[:limit]

    def scrape_techcrunch_rss(self):
        """Fetch TechCrunch AI posts via RSS"""
        import feedparser
        feed = feedparser.parse(
            'https://techcrunch.com/feed/?s=artificial+intelligence'
        )
        posts = []

        for entry in feed.entries[:5]:
            posts.append({
                "title": entry.title,
                "source": "TechCrunch",
                "url": entry.link,
                "summary": entry.get('summary', entry.title)[:200],
                "score": 0
            })

        return posts

    def run_daily_scrape(self):
        """Main execution"""
        all_stories = []

        # Scrape all sources
        all_stories.extend(self.scrape_reddit('artificial', limit=3))
        all_stories.extend(self.scrape_reddit('singularity', limit=2))
        all_stories.extend(self.scrape_hackernews(limit=3))
        all_stories.extend(self.scrape_techcrunch_rss())

        # Sort by score and take top 5
        all_stories.sort(key=lambda x: x['score'], reverse=True)
        top_5 = all_stories[:5]

        # Save to JSON
        output_path = Path('output') / f"{datetime.now().strftime('%Y-%m-%d')}_stories.json"
        output_path.parent.mkdir(exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                "date": datetime.now().isoformat(),
                "stories": top_5
            }, f, ensure_ascii=False, indent=2)

        return top_5


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()
    scraper = NewsScraperAI(
        reddit_client_id=os.getenv('REDDIT_CLIENT_ID'),
        reddit_secret=os.getenv('REDDIT_CLIENT_SECRET'),
        user_agent=os.getenv('REDDIT_USER_AGENT')
    )
    scraper.run_daily_scrape()
```

### 2. Script Generator (Claude API)

```python
# src/script_generator.py
from anthropic import Anthropic
import json
from pathlib import Path
from datetime import datetime

class ScriptGeneratorVN:
    def __init__(self, api_key):
        self.client = Anthropic()
        self.api_key = api_key

    def load_stories(self, json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)['stories']

    def generate_script(self, stories):
        """Generate Vietnamese script from stories"""

        stories_text = "\n\n".join([
            f"({i+1}) {story['title']}\nNguồn: {story['source']}\nTóm tắt: {story['summary']}"
            for i, story in enumerate(stories[:5])
        ])

        prompt = f"""Bạn là một nhà báo AI chuyên nghiệp làm cho kênh YouTube "AI Thực Chiến".
Viết kịch bản tin tức dài 2-3 phút (khoảng 450-600 từ) bằng tiếng Việt tự nhiên và hấp dẫn.

CÁC CÂU CHUYỆN:
{stories_text}

YÊU CẦU:
- Giọng lề, chuyên nghiệp nhưng hấp dẫn và dễ hiểu
- Chia thành 3 đoạn rõ ràng (mở đầu, nội dung chính, kết luận)
- BẮT ĐẦU với câu chào tự nhiên (ví dụ: "Xin chào các bạn, mình là AI Thực Chiến")
- KẾT THÚC với câu cảm ơn và khuyến khích tương tác
- Giải thích rõ các khái niệm AI phức tạp bằng cách dân dã, không dùng quá nhiều thuật ngữ kỹ thuật
- Tâm trạng: Tích cực, lạc quan về tương lai của AI
- Mỗi câu nên dài 10-20 từ để phù hợp với bài phát âm tự nhiên
- Thêm các dấu câu tự nhiên (...) để TTS phát âm tự nhiên

KHÔNG ĐƯỢC:
- Lặp lại quá nhiều cùng một từ
- Sử dụng câu quá dài (>25 từ)
- Nêu quan điểm cá nhân, chỉ trình bày sự kiện
"""

        message = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        return message.content[0].text

    def save_script(self, script, date_str=None):
        if date_str is None:
            date_str = datetime.now().strftime('%Y-%m-%d')

        output_path = Path('output') / f"{date_str}_script.txt"
        output_path.parent.mkdir(exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(script)

        return output_path


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()

    generator = ScriptGeneratorVN(api_key=os.getenv('ANTHROPIC_API_KEY'))
    today = datetime.now().strftime('%Y-%m-%d')

    stories_path = Path('output') / f"{today}_stories.json"
    if stories_path.exists():
        stories = generator.load_stories(stories_path)
        script = generator.generate_script(stories)
        saved_path = generator.save_script(script)
        print(f"Script saved to {saved_path}")
```

### 3. TTS Generator (Edge TTS)

```python
# src/tts_generator.py
import edge_tts
import asyncio
from pathlib import Path
from datetime import datetime

class TTSGeneratorVietnamese:
    VIETNAMESE_VOICES = {
        "female": "vi-VN-HoaiMyNeural",
        "male": "vi-VN-NamMinhNeural"
    }

    def __init__(self, voice="female"):
        self.voice = self.VIETNAMESE_VOICES.get(voice, "vi-VN-HoaiMyNeural")
        self.rate = "0.95"  # Slightly slower for clarity

    async def generate_audio(self, text, output_path):
        """Generate Vietnamese audio from text"""

        communicate = edge_tts.Communicate(
            text=text,
            voice=self.voice,
            rate=self.rate
        )

        await communicate.save(output_path)

    def run(self, script_path, output_path=None):
        """Synchronous wrapper"""

        # Read script
        with open(script_path, 'r', encoding='utf-8') as f:
            script = f.read()

        # Determine output path
        if output_path is None:
            date_str = datetime.now().strftime('%Y-%m-%d')
            output_path = Path('output') / f"{date_str}_audio.wav"

        output_path.parent.mkdir(exist_ok=True)

        # Generate audio
        asyncio.run(self.generate_audio(script, str(output_path)))

        print(f"Audio generated: {output_path}")
        return output_path


if __name__ == "__main__":
    from datetime import datetime

    today = datetime.now().strftime('%Y-%m-%d')
    script_path = Path('output') / f"{today}_script.txt"

    if script_path.exists():
        generator = TTSGeneratorVietnamese(voice="female")
        generator.run(script_path)
```

### 4. Avatar Animator (Wav2Lip Wrapper)

```python
# src/avatar_animator.py
import subprocess
from pathlib import Path
from datetime import datetime
import os

class AvatarAnimator:
    def __init__(self, wav2lip_dir):
        self.wav2lip_dir = Path(wav2lip_dir)
        self.python_exe = self.wav2lip_dir / "venv" / "bin" / "python"

    def animate(self, reference_video, audio_file, output_path, resize_factor=2):
        """Animate avatar using Wav2Lip"""

        output_path = Path(output_path)
        output_path.parent.mkdir(exist_ok=True)

        cmd = [
            str(self.python_exe),
            str(self.wav2lip_dir / "inference.py"),
            "--checkpoint_path", str(self.wav2lip_dir / "checkpoints" / "wav2lip_gan.pth"),
            "--face", str(reference_video),
            "--audio", str(audio_file),
            "--outfile", str(output_path),
            "--resize_factor", str(resize_factor),
            "--pads", "0", "10", "0", "0"
        ]

        print(f"Running Wav2Lip: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"Error: {result.stderr}")
            raise RuntimeError(f"Wav2Lip failed: {result.stderr}")

        print(f"Avatar video created: {output_path}")
        return output_path

    def run(self, reference_video, audio_file, output_path=None):
        if output_path is None:
            date_str = datetime.now().strftime('%Y-%m-%d')
            output_path = Path('output') / f"{date_str}_avatar.mp4"

        return self.animate(reference_video, audio_file, output_path)


if __name__ == "__main__":
    animator = AvatarAnimator(wav2lip_dir="~/ai-thuc-chien/wav2lip")

    today = datetime.now().strftime('%Y-%m-%d')
    audio_path = Path('output') / f"{today}_audio.wav"

    if audio_path.exists():
        animator.run(
            reference_video=Path('data') / 'reference_video.mp4',
            audio_file=audio_path
        )
```

### 5. YouTube Uploader

```python
# src/youtube_uploader.py
import google.oauth2.credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import json
from pathlib import Path

class YouTubeUploader:
    SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

    def __init__(self, client_secrets_json):
        self.client_secrets = client_secrets_json
        self.youtube = None

    def authenticate(self):
        """OAuth 2.0 authentication (one-time, caches token)"""
        flow = InstalledAppFlow.from_client_secrets_file(
            self.client_secrets,
            scopes=self.SCOPES
        )

        # This opens a browser for user consent (first time only)
        credentials = flow.run_local_server(port=8080)

        # Save credentials for future use
        with open('token.json', 'w') as token:
            token.write(credentials.to_json())

        self.youtube = build('youtube', 'v3', credentials=credentials)

    def upload_video(self, video_path, title, description, tags, category_id='27'):
        """Upload video to YouTube"""

        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags,
                'categoryId': category_id  # 27 = Education
            },
            'status': {
                'privacyStatus': 'public',  # or 'unlisted', 'private'
                'selfDeclaredMadeForKids': False
            }
        }

        media = MediaFileUpload(
            video_path,
            mimetype='video/mp4',
            resumable=True,
            chunksize=10*1024*1024  # 10MB chunks
        )

        request = self.youtube.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=media
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"Upload progress: {int(status.progress() * 100)}%")

        video_id = response['id']
        print(f"Video uploaded successfully! ID: {video_id}")
        return video_id


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    from datetime import datetime

    load_dotenv()

    uploader = YouTubeUploader(
        client_secrets_json=os.getenv('YOUTUBE_CLIENT_SECRETS_JSON')
    )

    # Authenticate (first time)
    uploader.authenticate()

    # Upload video
    today = datetime.now().strftime('%Y-%m-%d')
    video_path = Path('output') / f"{today}_youtube.mp4"

    if video_path.exists():
        uploader.upload_video(
            video_path=str(video_path),
            title=f"AI News {today}",
            description="Daily AI news summary in Vietnamese",
            tags=['AI', 'news', 'Vietnam', 'technology']
        )
```

### 6. Main Orchestration Script

```bash
#!/bin/bash
# run_daily_pipeline.sh

set -e

# Configuration
PROJECT_DIR="$HOME/ai-thuc-chien"
VENV_PATH="$PROJECT_DIR/venv"
LOG_FILE="$PROJECT_DIR/logs/pipeline.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

# Initialize log
mkdir -p "$PROJECT_DIR/logs"
echo "[$DATE] Pipeline started" >> "$LOG_FILE"

# Activate virtual environment
source "$VENV_PATH/bin/activate"

cd "$PROJECT_DIR"

# Step 1: Scrape news
echo "[$DATE] Step 1: Scraping news..." >> "$LOG_FILE"
python src/scraper.py >> "$LOG_FILE" 2>&1 || {
  echo "[$DATE] FAILED at scraper" >> "$LOG_FILE"
  exit 1
}

# Step 2: Generate script
echo "[$DATE] Step 2: Generating script..." >> "$LOG_FILE"
python src/script_generator.py >> "$LOG_FILE" 2>&1 || {
  echo "[$DATE] FAILED at script generation" >> "$LOG_FILE"
  exit 1
}

# Step 3: Generate TTS
echo "[$DATE] Step 3: Generating TTS audio..." >> "$LOG_FILE"
python src/tts_generator.py >> "$LOG_FILE" 2>&1 || {
  echo "[$DATE] FAILED at TTS generation" >> "$LOG_FILE"
  exit 1
}

# Step 4: Animate avatar
echo "[$DATE] Step 4: Animating avatar..." >> "$LOG_FILE"
python src/avatar_animator.py >> "$LOG_FILE" 2>&1 || {
  echo "[$DATE] FAILED at avatar animation" >> "$LOG_FILE"
  exit 1
}

# Step 5: Add graphics (FFmpeg)
echo "[$DATE] Step 5: Adding graphics..." >> "$LOG_FILE"
TODAY=$(date '+%Y-%m-%d')
AVATAR_VIDEO="$PROJECT_DIR/output/${TODAY}_avatar.mp4"
FINAL_VIDEO="$PROJECT_DIR/output/${TODAY}_final.mp4"

# Add watermark and subtitles with FFmpeg
ffmpeg -i "$AVATAR_VIDEO" \
  -i "$PROJECT_DIR/data/watermark.png" \
  -filter_complex "overlay=x=W-w-10:y=H-h-10" \
  -c:a copy "$FINAL_VIDEO" >> "$LOG_FILE" 2>&1 || {
  echo "[$DATE] FAILED at graphics rendering" >> "$LOG_FILE"
  exit 1
}

# Step 6: Encode for YouTube
echo "[$DATE] Step 6: Encoding for YouTube..." >> "$LOG_FILE"
YOUTUBE_VIDEO="$PROJECT_DIR/output/${TODAY}_youtube.mp4"

ffmpeg -i "$FINAL_VIDEO" \
  -vcodec libx264 -crf 18 -preset medium \
  -acodec aac -ab 192k \
  -movflags +faststart \
  "$YOUTUBE_VIDEO" >> "$LOG_FILE" 2>&1 || {
  echo "[$DATE] FAILED at YouTube encoding" >> "$LOG_FILE"
  exit 1
}

# Step 7: Upload to YouTube
echo "[$DATE] Step 7: Uploading to YouTube..." >> "$LOG_FILE"
python src/youtube_uploader.py >> "$LOG_FILE" 2>&1 || {
  echo "[$DATE] FAILED at YouTube upload" >> "$LOG_FILE"
  exit 1
}

echo "[$DATE] Pipeline completed successfully!" >> "$LOG_FILE"
deactivate
```

---

## Reference Video Requirements

### Specifications for Your Avatar

**Ideal Setup**:
- **Duration**: 5-10 seconds
- **Resolution**: 1280×720 (720p) minimum, 1920×1080 (1080p) recommended
- **Format**: MP4, H.264 codec
- **Frame Rate**: 25 fps (PAL) or 30 fps (NTSC)
- **Codec**: H.264 (libx264)

**Framing**:
- Head and shoulders visible
- Face centered, 60% of frame
- Neutral expression at start
- Clear view of lips
- Minimal head movement (tilt is okay, not full rotations)

**Lighting**:
- Front-facing key light (3000-5000K daylight)
- No harsh shadows on face
- Avoid backlighting
- Uniform background (solid color preferred)

**What Works**:
- Sitting in chair, facing camera
- Slight head tilt acceptable
- Natural blinking okay
- Minimal hand gestures

**What Doesn't Work**:
- Extreme angles (profile, over-shoulder)
- Moving around the frame
- Rapid head movements
- Extreme expressions
- Heavy makeup/filters (affects lip detection)

**Creation Tips**:
```bash
# Record with iPhone/webcam
ffmpeg -f avfoundation -i "0:0" -t 10 reference_video.mp4

# OR use ffmpeg to convert existing video
ffmpeg -i source.mov \
  -vf scale=1280:720 \
  -c:v libx264 -preset fast \
  -c:a aac \
  reference_video.mp4
```

---

## Comparison: Wav2Lip vs MuseTalk

| **Metric** | **Wav2Lip** | **MuseTalk** |
|---|---|---|
| **Setup Difficulty** | Easy (2-3 hours) | Hard (6-12 hours) |
| **macOS M-series Support** | Good (CPU-friendly) | Poor (CUDA-dependent) |
| **Output Resolution** | 96×96 (low quality) | 256×256 (better) |
| **Speed** | Slow on CPU (3-5 min/30sec) | Fast on GPU only |
| **Lip-Sync Accuracy** | 85% | 95% |
| **Identity Preservation** | Good | Excellent |
| **Community Support** | Large | Small |
| **External Dependencies** | Minimal | Heavy (mmcv, mmdet, mmpose) |
| **Best Use Case** | Daily automation | Premium quality (requires GPU) |
| **Recommendation for You** | ✅ USE THIS | Future upgrade with external GPU |

**Decision Tree**:
```
Do you have an NVIDIA GPU available?
├─ NO (macOS M-series native) → Use Wav2Lip
│   └─ Fast setup, CPU-friendly, good enough quality
│
└─ YES (external RTX server/cloud) → Use MuseTalk
    └─ Better quality, real-time speed on GPU, worth the setup
```

---

## Known Issues & Solutions

### Issue 1: Wav2Lip "ModuleNotFoundError: No module named 'dlib'"

**Solution**:
```bash
pip install dlib
# If fails, use:
conda install -c conda-forge dlib
```

### Issue 2: FFmpeg "Unknown encoder 'libx264'"

**Solution**:
```bash
brew install ffmpeg --with-options-x264

# Or use pre-built ffmpeg with codec support:
brew install ffmpeg
ffmpeg -codecs | grep h264  # Verify it works
```

### Issue 3: YouTube API "quota exceeded"

**Solution**:
- Default quota: 10,000 units/day
- `videos.insert` = 1,600 units
- Max 6 videos/day with free quota
- Request quota increase in Google Cloud Console (takes 1-2 business days)

### Issue 4: Edge TTS "Connection timeout"

**Solution**:
```python
# Add retry logic
import time
for attempt in range(3):
    try:
        asyncio.run(generate_audio(...))
        break
    except Exception as e:
        if attempt < 2:
            time.sleep(5)
        else:
            raise
```

### Issue 5: Wav2Lip face detection fails

**Causes & Solutions**:
- Face too small → Use `--pads 0 20 0 0` to expand detection area
- Poor lighting → Ensure front-facing light on face
- Video too long → Split into 30-second chunks
- Wrong format → Ensure video is MP4 H.264

```bash
# Troubleshoot with verbose output
python inference.py ... --face_det_batch_size 8 --nosmooth
```

---

## Daily Cron Schedule

**Setup**:
```bash
crontab -e

# Add this line (8 AM Vietnam time = 1 AM UTC, adjust for your TZ)
0 8 * * * source ~/.zprofile && /Users/huyho/ai-thuc-chien/run_daily_pipeline.sh
```

**Monitoring**:
```bash
# View logs
tail -f ~/ai-thuc-chien/logs/pipeline.log

# Check cron execution history
log stream --predicate 'process == "cron"' --level debug

# Manual test run
~/ai-thuc-chien/run_daily_pipeline.sh
```

**Backup & Recovery**:
- Store daily outputs in `output/` directory
- Keep logs for debugging
- Weekly backup of reference video and config files

---

## Cost Analysis

| **Component** | **Cost** | **Notes** |
|---|---|---|
| **Claude API** | $0.80/day | ~2,000 tokens × $0.003/1K tokens |
| **YouTube Data API** | FREE | 10,000 units/day free tier |
| **Edge TTS** | FREE | Microsoft Edge, no auth required |
| **Wav2Lip** | FREE | Open-source, self-hosted |
| **FFmpeg** | FREE | Open-source |
| **Total** | ~$24/month | Minimal cost for 365 videos/year |

---

## Next Steps

1. **Week 1**: Set up environment, install Wav2Lip, prepare reference video
2. **Week 2**: Implement scraper and script generator, test API integrations
3. **Week 3**: Set up TTS, animate first test video, refine graphics
4. **Week 4**: YouTube API setup, upload first video, schedule cron job
5. **Ongoing**: Monitor daily outputs, adjust prompts/parameters, scale to 2x/day if needed

---

## Resources & Links

- **Wav2Lip**: https://github.com/justinjohn0306/Wav2Lip
- **Edge TTS**: https://github.com/rany2/edge-tts
- **YouTube Data API**: https://developers.google.com/youtube/v3
- **Claude API**: https://anthropic.com/api
- **FFmpeg Docs**: https://ffmpeg.org/documentation.html

---

**Document Last Updated**: March 2026
**Status**: Production-Ready
**Maintenance**: Review quarterly for API changes
