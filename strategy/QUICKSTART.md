# Quick Start Guide - 5 Minutes to Automated Posts

Follow this guide to get your Facebook automation running in under 5 minutes.

## Step 1: Get Your API Keys (2 minutes)

### Facebook Access Token & Page ID

1. Go to https://developers.facebook.com/tools/explorer/
2. In the dropdown, select your app (or create one)
3. Get a **User Token** with these permissions:
   - `pages_manage_posts`
   - `pages_read_engagement`
4. Make it long-lived: Click "Generate Long-Lived Token"
5. Copy the token → you'll need this for `.env`

**Get your Page ID:**
- Visit https://findmyfacebook.com/
- Enter your page name
- Copy the numeric ID

### Claude API Key

1. Go to https://console.anthropic.com/account/keys
2. Click "Create Key"
3. Copy it → you'll need this for `.env`

### Tavily API Key

1. Go to https://tavily.com/
2. Sign up (free)
3. Go to API keys
4. Copy it → you'll need this for `.env`

## Step 2: Install & Configure (2 minutes)

```bash
# Navigate to project
cd /tmp/ai-thuc-chien-brand

# Create Python environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r scripts/requirements.txt

# Copy environment file
cp scripts/.env.example scripts/.env

# Edit with your API keys
nano scripts/.env
```

Paste these into your `.env`:
```
FACEBOOK_PAGE_ID=your_numeric_page_id
FACEBOOK_ACCESS_TOKEN=your_long_lived_token
CLAUDE_API_KEY=sk-ant-...
TAVILY_API_KEY=tvly-...
```

## Step 3: Test It Works (1 minute)

```bash
cd scripts

# Test fetching news
python3 fb_news_fetcher.py

# Test generating content for each pillar
python3 fb_content_generator.py

# Full test (won't post to Facebook yet)
python3 facebook-autoposter.py --run-once
```

You should see:
- ✓ News fetched from Tavily or RSS
- ✓ Vietnamese posts generated for each pillar
- ✓ Preview of what would be posted

## Step 4: Set Up Daily Automation (2 minutes)

```bash
cd scripts
bash setup-cron.sh
```

The script will:
- ✓ Verify your setup
- ✓ Install a cron job for daily posting
- ✓ Offer to run a test post
- ✓ Show you monitoring commands

**That's it!** Your posts will now be published daily.

## Monitor Your Posts

### Check if it's working

```bash
# View live logs
tail -f logs/autoposter_cron.log

# Show posting stats
cd scripts
python3 facebook-autoposter.py --stats

# Run health check
bash scripts/health-check.sh
```

### Expected output

Every day, you should see in logs:
```
✓ Fetched 5 items from Tavily
✓ Selected pillar: ai_news_hot_take
✓ Generated ai_news_hot_take post
✓ Post published successfully: 1234567890123
✓ Added post to history
```

## Verify on Facebook

1. Go to your AI Thực Chiến Facebook page
2. Refresh the page daily around 1-4pm Vietnam time
3. New Vietnamese posts should appear automatically
4. Check Facebook Insights for engagement metrics

## Common Issues & Quick Fixes

| Issue | Solution |
|-------|----------|
| ".env not found" | `cp scripts/.env.example scripts/.env` and edit it |
| "No news found" | Check TAVILY_API_KEY is correct, verify internet |
| "Post failed" | Generate new Facebook access token, verify Page ID |
| "Cron not running" | `crontab -l` to verify, `tail -f logs/` to debug |
| "Claude API error" | Check CLAUDE_API_KEY is correct and you have API access |

## What Gets Posted?

Your system posts Vietnamese AI content in 4 categories:

- **40%**: AI News with practical insights for businesses
- **30%**: Automation success stories with real numbers
- **20%**: Reviews of AI tools for SMB owners
- **10%**: Behind-the-scenes sharing and insights

Each post is:
- 150-250 words (optimal for Facebook)
- Conversational Vietnamese
- Focused on business benefits
- Ends with: "DM mình 'TỰ ĐỘNG' nếu bạn muốn áp dụng cho business của mình"

## Customize Your Posts

To change the content voice, edit `scripts/config.py`:

Look for the `SYSTEM_PROMPTS` dictionary and update the Vietnamese prompts to match your brand.

For example, to make posts more casual:
```python
"ai_news_hot_take": """Viết như một bạn của người dùng, không quá formal..."""
```

## Next Steps

1. **Monitor daily** - Check logs and Facebook Insights
2. **Adjust prompts** - Update Vietnamese copy based on engagement
3. **Add more sources** - Edit RSS_FEEDS in config.py for more news
4. **Scale up** - Change cron to post multiple times daily if desired

---

That's it! You now have a fully automated Vietnamese AI content system posting daily to Facebook.

For detailed documentation, see **README.md**.
