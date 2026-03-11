# AI Thực Chiến - YouTube Automation Setup Guide

Complete setup and usage guide for the YouTube automation pipeline.

## Quick Start

### 1. Install Dependencies

```bash
cd /tmp/ai-thuc-chien-brand
pip install -r requirements.txt
chmod +x scripts/*.py
```

### 2. Set Environment Variables

Create a `.env` file in the project root:

```bash
export ANTHROPIC_API_KEY="your-anthropic-key-here"
```

Or set globally:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### 3. Set Up YouTube API

#### Step A: Create Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project: "AI Thực Chiến"
3. Enable YouTube Data API v3

#### Step B: Create OAuth Credentials
1. Go to Credentials → Create Credentials → OAuth Client ID
2. Application type: Desktop application
3. Download as JSON
4. Save as `credentials.json` in project root

#### Step C: First Authentication
```bash
python3 scripts/youtube-uploader.py --video sample.mp4 --topic "test" --dry-run
```

This will trigger OAuth flow:
- Browser opens automatically
- Sign in with YouTube account
- Grant permissions
- `token.json` is saved automatically

---

## Usage Guide

### Video Script Generation

#### Generate Single Script (Short)

```bash
python3 scripts/video-script-generator.py \
  --topic "ChatGPT tips for Shopee sellers" \
  --format short
```

Output:
- Markdown file with full script
- JSON with structured data
- Thumbnail suggestions
- Visual notes for filming

#### Generate Single Script (Long)

```bash
python3 scripts/video-script-generator.py \
  --topic "Complete guide to AI automation" \
  --format long
```

#### Batch Generate from JSON

Create `topics.json`:

```json
{
  "topics": [
    "ChatGPT for e-commerce",
    {
      "topic": "Midjourney tutorial",
      "format": "short"
    },
    {
      "topic": "Zapier automation guide",
      "format": "long"
    }
  ]
}
```

Run batch:

```bash
python3 scripts/video-script-generator.py --batch --file topics.json
```

Scripts saved to `scripts_library/` directory.

#### List Generated Scripts

```bash
python3 scripts/video-script-generator.py --list
```

---

### Video Upload

#### Option 1: Upload Immediately

```bash
python3 scripts/youtube-uploader.py \
  --video /path/to/video.mp4 \
  --topic "ChatGPT for e-commerce" \
  --format long
```

Result:
- Video uploaded as PRIVATE (for review)
- Metadata auto-generated
- SEO-optimized title, description, tags
- Video link printed to console

#### Option 2: Dry Run (No Upload)

Preview generated metadata without uploading:

```bash
python3 scripts/youtube-uploader.py \
  --video /path/to/video.mp4 \
  --topic "ChatGPT for e-commerce" \
  --dry-run
```

Shows:
- Generated title
- Generated description
- Generated tags
- No actual upload

#### Option 3: Schedule Upload

Upload at specific time:

```bash
python3 scripts/youtube-uploader.py \
  --video /path/to/video.mp4 \
  --topic "AI trends March 2026" \
  --schedule "2026-03-15T10:00:00Z"
```

Note: Time is in UTC (Z = Zulu time). For Vietnam (GMT+7):
- 10 AM Vietnam = 3 AM UTC
- Use "2026-03-15T03:00:00Z"

#### Option 4: Add to Queue (Batch)

Add multiple videos for batch processing:

```bash
# Add directory of videos to queue
python3 scripts/youtube-uploader.py \
  --queue-dir ./pending_videos/ \
  --format long

# Process entire queue
python3 scripts/youtube-uploader.py --process-queue
```

This:
1. Scans directory for video files (.mp4, .mov, .mkv)
2. Uses filename as topic
3. Saves to `upload_queue.json`
4. Processes with retry logic

---

## Workflow Examples

### Example 1: Create & Upload Single Video

```bash
# 1. Generate script
python3 scripts/video-script-generator.py \
  --topic "ChatGPT for writing product descriptions" \
  --format short

# Output: scripts_library/20260311_120000_ChatGPT_for_writing_short.md

# 2. Record video using the script
# (Manual: use phone/camera + script from .md file)
# Save as: ~/Downloads/chatgpt_descriptions.mp4

# 3. Preview metadata
python3 scripts/youtube-uploader.py \
  --video ~/Downloads/chatgpt_descriptions.mp4 \
  --topic "ChatGPT for writing product descriptions" \
  --dry-run

# 4. Upload to YouTube
python3 scripts/youtube-uploader.py \
  --video ~/Downloads/chatgpt_descriptions.mp4 \
  --topic "ChatGPT for writing product descriptions"
```

### Example 2: Batch Content Pipeline

```bash
# 1. Create batch topics file
cat > weekly_topics.json << 'EOF'
{
  "topics": [
    {"topic": "ChatGPT for social media", "format": "short"},
    {"topic": "Midjourney image generation", "format": "long"},
    {"topic": "Zapier automation tutorial", "format": "long"},
    {"topic": "AI news roundup", "format": "short"}
  ]
}
EOF

# 2. Generate all scripts
python3 scripts/video-script-generator.py \
  --batch \
  --file weekly_topics.json \
  --output weekly_scripts/

# 3. Record videos using scripts
# (Manual: film 4 videos using generated scripts)

# 4. Add videos to upload queue
python3 scripts/youtube-uploader.py \
  --queue-dir ./recorded_videos/ \
  --format long

# 5. Schedule uploads for optimal times
# Edit upload_queue.json to add scheduled times, then:
python3 scripts/youtube-uploader.py --process-queue

# 6. Queue will automatically retry any failures
python3 scripts/youtube-uploader.py --process-queue  # Run again next hour
```

### Example 3: Scheduled Content Calendar

Create a calendar using the content calendar from `youtube-content-calendar.md`:

```bash
# Create scheduled topics file
cat > march_schedule.json << 'EOF'
{
  "topics": [
    {"topic": "ChatGPT cho chủ shop Shopee: Tiết kiệm 5 giờ mỗi ngày", "format": "long"},
    {"topic": "Viết bài quảng cáo Facebook trong 30 giây", "format": "short"},
    {"topic": "Midjourney tạo ảnh bán hàng", "format": "short"}
  ]
}
EOF

# Generate scripts for entire month
python3 scripts/video-script-generator.py --batch --file march_schedule.json

# Record videos and add to queue with timestamps
python3 scripts/youtube-uploader.py \
  --video video1.mp4 \
  --topic "ChatGPT cho chủ shop..." \
  --schedule "2026-03-11T03:00:00Z"  # Tuesday 10 AM Vietnam

python3 scripts/youtube-uploader.py \
  --video video2.mp4 \
  --topic "Viết bài quảng cáo..." \
  --schedule "2026-03-12T03:00:00Z"  # Wednesday 10 AM Vietnam
```

---

## Configuration

### YouTube Upload Settings

Edit upload behavior in `youtube-uploader.py`:

```python
# Privacy default: "private" (safest)
# Change to "public" or "unlisted" as needed
privacy_status: str = "private"

# Category ID: "22" = People & Blogs
# Other options: "20" (Gaming), "24" (Entertainment)
category_id: str = "22"
```

### Script Generation Settings

Default model: `claude-opus-4-1-20250805`

For cost savings, switch to `claude-3-5-sonnet-20241022`:

```python
# In video-script-generator.py, line ~200
model="claude-3-5-sonnet-20241022"  # Faster, cheaper
```

---

## Troubleshooting

### Issue: "ANTHROPIC_API_KEY not found"

**Solution**: Set environment variable

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
python3 scripts/video-script-generator.py --topic "test" --format short
```

### Issue: "Credentials file not found: credentials.json"

**Solution**: Download OAuth credentials from Google Cloud Console

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Credentials → Download OAuth JSON
3. Save as `credentials.json` in project root

### Issue: Upload fails with "Invalid video file"

**Solution**: Ensure video format is supported

Supported formats:
- .mp4 (recommended)
- .mov
- .mkv
- .flv
- .avi
- .webm

Use FFmpeg to convert:
```bash
ffmpeg -i input.mov -c:v libx264 -c:a aac output.mp4
```

### Issue: "Max retries exceeded" in queue

**Solution**: Check error logs and fix, then re-add to queue

```bash
# Check log file
cat youtube_uploader.log | grep ERROR

# Fix issue (e.g., invalid metadata), then re-add
python3 scripts/youtube-uploader.py --queue-dir ./fixed_videos/
```

### Issue: Script generation is slow

**Solution**: Use faster model (trade-off: less creative)

```bash
# Edit video-script-generator.py
# Change model to claude-3-5-sonnet-20241022
```

---

## Optimization Tips

### 1. Batch Processing

Process multiple videos at once:

```bash
python3 scripts/youtube-uploader.py --process-queue
```

This processes all pending uploads in one run.

### 2. Dry Runs

Always preview before uploading:

```bash
python3 scripts/youtube-uploader.py --video file.mp4 --topic "test" --dry-run
```

### 3. Queue Management

View pending uploads:

```bash
cat upload_queue.json
```

Edit to adjust retry counts or add scheduled times.

### 4. Cost Optimization

- Use shorter prompts for script generation
- Batch generate scripts (cost per token is same, but batch = higher token efficiency)
- Use `claude-3-5-sonnet-20241022` for faster turnaround (~70% cost of Opus)

---

## Monitoring & Logging

### Log Files

- `youtube_uploader.log` - Upload operations
- `script_generator.log` - Script generation
- Both include DEBUG level details for troubleshooting

### Queue Status

```bash
# View pending uploads
python3 -c "import json; print(json.dumps(json.load(open('upload_queue.json')), indent=2))"

# Count pending jobs
python3 -c "import json; jobs = json.load(open('upload_queue.json')); print(f'Pending: {len(jobs)}')"
```

### API Usage

YouTube Data API has quotas:
- **Quota**: 10,000 units/day per account
- **Cost per upload**: ~1,500 units
- **Limit**: ~6 uploads/day (safe)

Anthropic API costs:
- ~$0.10-0.50 per script generation
- Batch of 10 scripts: $1-5

---

## Advanced Usage

### Custom Metadata

Override auto-generated metadata:

Edit `youtube-uploader.py`, modify `VideoMetadata` before upload:

```python
metadata.title = "Custom Title"
metadata.tags = ["custom", "tags"]
metadata.description = "Custom description"
```

### Custom Prompts

Modify Claude prompts for specific style:

Edit `video-script-generator.py`, update `generate_short_form_script()`:

```python
prompt = f"""Your custom prompt here..."""
```

### Parallel Processing

Process multiple uploads simultaneously:

```bash
# In background terminal 1
python3 scripts/youtube-uploader.py --video video1.mp4 --topic "Topic 1" &

# In background terminal 2
python3 scripts/youtube-uploader.py --video video2.mp4 --topic "Topic 2" &

# Wait for both to complete
wait
```

---

## Checklist for Going Live

Before publishing videos to public:

- [ ] All videos are in Private status (default)
- [ ] Reviewed title, description, tags
- [ ] Thumbnail created (use suggestions from script)
- [ ] Video plays correctly on YouTube
- [ ] Descriptions have proper Vietnamese characters
- [ ] No broken links in description
- [ ] Hashtags are relevant (#AI #TựđộngHóa etc)
- [ ] Category is "People & Blogs"
- [ ] Video is >60 seconds (monetization requirement)

To publish:

1. Go to YouTube Studio
2. Select video
3. Change privacy: Private → Public/Unlisted
4. Click Save

---

## Support

For issues:

1. Check logs: `cat youtube_uploader.log`
2. Verify API keys are set
3. Test credentials: `python3 scripts/youtube-uploader.py --help`
4. Check network: `curl -I https://www.youtube.com`

---

*Last Updated: 2026-03-11*
*Next Review: After first 10 uploads*
