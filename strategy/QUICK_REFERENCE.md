# Quick Reference - YouTube Automation Commands

## One-Line Setup

```bash
pip install -r requirements.txt && export ANTHROPIC_API_KEY="your-key-here"
```

## Common Commands

### Generate Scripts

```bash
# Short video script (45-60 seconds)
python3 scripts/video-script-generator.py --topic "ChatGPT tips" --format short

# Long video script (8-10 minutes)
python3 scripts/video-script-generator.py --topic "AI automation guide" --format long

# Batch generate from JSON
python3 scripts/video-script-generator.py --batch --file topics-sample.json

# List all generated scripts
python3 scripts/video-script-generator.py --list
```

### Upload Videos

```bash
# Preview metadata (no upload)
python3 scripts/youtube-uploader.py --video video.mp4 --topic "Your topic" --dry-run

# Upload immediately
python3 scripts/youtube-uploader.py --video video.mp4 --topic "Your topic"

# Schedule upload (Vietnam time: subtract 7 hours from desired time)
# Example: Upload Tuesday 10 AM Vietnam = 3 AM UTC
python3 scripts/youtube-uploader.py --video video.mp4 --topic "Topic" --schedule "2026-03-11T03:00:00Z"

# Add videos from directory to queue
python3 scripts/youtube-uploader.py --queue-dir ./videos/ --format long

# Process all queued uploads
python3 scripts/youtube-uploader.py --process-queue
```

## File Locations

| File | Purpose |
|------|---------|
| `youtube-strategy.md` | Full channel strategy (read first) |
| `youtube-content-calendar.md` | 12 video ideas for month 1 |
| `scripts/youtube-uploader.py` | Upload script |
| `scripts/video-script-generator.py` | Script generation |
| `topics-sample.json` | Sample topics for batch processing |
| `SETUP.md` | Detailed setup guide |
| `scripts_library/` | Generated scripts (auto-created) |
| `upload_queue.json` | Pending uploads (auto-created) |

## API Keys

```bash
# Set Anthropic key (for script generation)
export ANTHROPIC_API_KEY="sk-ant-..."

# YouTube OAuth (automatic on first upload)
# 1. Go to Google Cloud Console
# 2. Create OAuth credentials
# 3. Download as credentials.json
# 4. Save in project root
# 5. First upload will trigger OAuth flow
```

## Workflow Checklist

### Single Video
- [ ] `video-script-generator.py --topic "..." --format long`
- [ ] Review script in `scripts_library/`
- [ ] Record video based on script
- [ ] `youtube-uploader.py --video video.mp4 --topic "..." --dry-run`
- [ ] Review metadata preview
- [ ] `youtube-uploader.py --video video.mp4 --topic "..."`
- [ ] Check YouTube Studio (video will be PRIVATE)
- [ ] Publish when ready

### Batch Month
- [ ] `video-script-generator.py --batch --file topics-sample.json`
- [ ] Record all 12 videos
- [ ] `youtube-uploader.py --queue-dir ./videos/`
- [ ] `youtube-uploader.py --process-queue`
- [ ] Monitor: `tail -f youtube_uploader.log`

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "ANTHROPIC_API_KEY not found" | `export ANTHROPIC_API_KEY="sk-ant-..."` |
| "credentials.json not found" | Download from Google Cloud Console, save in root |
| "Invalid video file" | Check format: .mp4, .mov, .mkv, .flv, .avi, .webm |
| Upload fails | Check `youtube_uploader.log` for errors |
| Slow script generation | Use `--model claude-3-5-sonnet-20241022` (faster) |

## Key Timings (Vietnam = GMT+7)

| Desired Time (Vietnam) | UTC Time | Upload Command |
|------------------------|----------|-----------------|
| 10 AM (Tuesday) | 3 AM | `--schedule "2026-03-11T03:00:00Z"` |
| 2 PM (Thursday) | 7 AM | `--schedule "2026-03-13T07:00:00Z"` |
| 8 PM (Saturday) | 1 PM | `--schedule "2026-03-15T13:00:00Z"` |

Formula: `Vietnam time - 7 hours = UTC time`

## Expected Outputs

### Script Generation
```
scripts_library/
├── 20260311_120000_topic_short.md      (Readable script)
├── 20260311_120000_topic_short.json    (Structured data)
├── 20260311_121500_topic_long.md
└── 20260311_121500_topic_long.json
```

### Upload
- Video uploaded to YouTube (PRIVATE by default)
- Console shows: Video ID + URL
- `youtube_uploader.log` has full details
- `upload_queue.json` tracks pending uploads

## Performance Targets

- **Script generation:** ~30-60 seconds per script
- **Upload:** ~2-5 minutes per video (depends on file size)
- **Batch upload:** Can run in background while doing other work

## Cost Breakdown (Monthly)

- Scripts: ~$8-24 (12 scripts per month)
- YouTube API: $0 (free quota)
- **Total:** ~$8-24

Labor saved: ~17 hours = ~$255 value
**ROI: 10x+**

## Learning Path

1. **Day 1:** Read `youtube-strategy.md` (understand channel vision)
2. **Day 2:** Read `youtube-content-calendar.md` (understand content)
3. **Day 3:** Set up API keys, test scripts
4. **Day 4-7:** Generate scripts for first 4 videos
5. **Week 2:** Record videos
6. **Week 3:** Upload and publish

## Resources

- Strategy: `youtube-strategy.md` (12 KB, 30 min read)
- Calendar: `youtube-content-calendar.md` (24 KB, 45 min read)
- Setup: `SETUP.md` (11 KB, 20 min read)
- Full guide: `YOUTUBE_AUTOMATION_SUMMARY.md` (40 KB)

## Need Help?

```bash
# Show script generator help
python3 scripts/video-script-generator.py --help

# Show uploader help
python3 scripts/youtube-uploader.py --help

# Check logs
tail -f youtube_uploader.log
tail -f script_generator.log

# View queue status
cat upload_queue.json | python3 -m json.tool
```

## One-Stop Command Examples

```bash
# Complete Month 1 workflow (4 commands)
python3 scripts/video-script-generator.py --batch --file topics-sample.json
# ... record all 12 videos ...
python3 scripts/youtube-uploader.py --queue-dir ./recorded_videos/ --format long
python3 scripts/youtube-uploader.py --process-queue
```

---

**Start here:** `python3 scripts/video-script-generator.py --topic "ChatGPT for e-commerce" --format short`

*For detailed information, see SETUP.md or YOUTUBE_AUTOMATION_SUMMARY.md*
