# Deployment Checklist - AI Thực Chiến Facebook Autoposter

Use this checklist to verify your system is ready for production.

## Pre-Deployment Setup

### Phase 1: Files & Environment (15 min)

- [ ] **Project directory created** at `/tmp/ai-thuc-chien-brand/`
- [ ] **Python 3.8+** installed: `python3 --version`
- [ ] **Virtual environment created**: `python3 -m venv venv`
- [ ] **Virtual environment activated**: `source venv/bin/activate`
- [ ] **Dependencies installed**: `pip install -r scripts/requirements.txt`
- [ ] **.env file created**: `cp scripts/.env.example scripts/.env`
- [ ] **.env added to .gitignore** (if using git)

### Phase 2: API Keys & Configuration (10 min)

#### Facebook
- [ ] **Facebook Developer account** created
- [ ] **App created** in Meta App Dashboard
- [ ] **Page ID retrieved** (numeric, not page name)
- [ ] **Long-lived access token generated** with correct scopes:
  - [ ] `pages_manage_posts`
  - [ ] `pages_read_engagement`
- [ ] **Token pasted into .env**:
  ```
  FACEBOOK_PAGE_ID=<numeric_id>
  FACEBOOK_ACCESS_TOKEN=<token>
  ```

#### Claude
- [ ] **Anthropic account** created at console.anthropic.com
- [ ] **API key generated**
- [ ] **Key pasted into .env**:
  ```
  CLAUDE_API_KEY=sk-ant-...
  ```

#### Tavily
- [ ] **Tavily account** created at tavily.com
- [ ] **API key generated**
- [ ] **Key pasted into .env**:
  ```
  TAVILY_API_KEY=tvly-...
  ```

### Phase 3: Validation (10 min)

- [ ] **Run validation script**: `bash scripts/test-setup.sh`
- [ ] **All checks pass** (or only warnings for optional components)
- [ ] **News fetching works**: `python3 scripts/fb_news_fetcher.py`
- [ ] **Content generation works**: `python3 scripts/fb_content_generator.py`
- [ ] **Full pipeline works**: `python3 scripts/facebook-autoposter.py --run-once`

### Phase 4: Manual Testing (15 min)

- [ ] **Run full test**: `python3 scripts/facebook-autoposter.py --run-once`
- [ ] **Verify news was fetched**
- [ ] **Verify post was generated**
- [ ] **Verify post appeared on Facebook page**
- [ ] **Check post content quality** (Vietnamese, professional, includes CTA)
- [ ] **Review log file**: `cat logs/autoposter_*.log`
- [ ] **Check post history**: `cat data/post_history.json`

### Phase 5: Cron Setup (10 min)

- [ ] **Run setup script**: `bash scripts/setup-cron.sh`
- [ ] **Verify all pre-flight checks pass**
- [ ] **Cron job installed**: `crontab -l | grep facebook-autoposter`
- [ ] **Random posting time generated** (13-15 hour range)
- [ ] **Test post completed successfully** during setup
- [ ] **Note the posting time** for your records

## Post-Deployment Verification (First 7 Days)

### Day 1: Immediate Check
- [ ] **Cron job installed**: `crontab -l`
- [ ] **Logs exist**: `ls -la logs/`
- [ ] **First post appeared on Facebook** at scheduled time
- [ ] **Post content is correct Vietnamese** with CTA
- [ ] **Post history updated**: `cat data/post_history.json`

### Day 2-3: Pattern Verification
- [ ] **Posts appearing daily** at random time
- [ ] **Logs showing successful runs**: `tail -20 logs/autoposter_cron.log`
- [ ] **No error patterns** in logs
- [ ] **Content variety visible** (mix of different pillar types)
- [ ] **Facebook engagement starting** (likes, comments, shares)

### Day 4-7: Stability Check
- [ ] **All 7 posts published successfully**
- [ ] **No duplicate topics** in posts
- [ ] **Post history contains all posts**: `grep -c '"timestamp"' data/post_history.json`
- [ ] **Logs show no warnings or errors**
- [ ] **Health check passes**: `bash scripts/health-check.sh`
- [ ] **Stats look good**: `python3 scripts/facebook-autoposter.py --stats`

## Production Readiness Checklist

### Security
- [ ] **.env file is NOT in version control** (git-ignored)
- [ ] **API keys NOT visible in logs**
- [ ] **No hardcoded secrets** in any Python files
- [ ] **File permissions correct**:
  - [ ] `.env` is readable only by owner (600)
  - [ ] Scripts are executable (755)
  - [ ] Config files are readable (644)

### Monitoring
- [ ] **Log file rotation configured** (via setup-cron.sh)
- [ ] **Daily log review process** planned
- [ ] **Alert criteria defined** (what to monitor for)
- [ ] **Health check scheduled** (if using separate monitoring)
- [ ] **Facebook Insights** being checked for engagement

### Documentation
- [ ] **Team knows how to check logs**: `tail -f logs/autoposter_cron.log`
- [ ] **Team knows how to view stats**: `python3 facebook-autoposter.py --stats`
- [ ] **Team knows how to run manual post**: `python3 facebook-autoposter.py --run-once`
- [ ] **Team knows how to pause cron**: `crontab -e` (comment out line)
- [ ] **Emergency contact info** documented if system fails

### Backup & Recovery
- [ ] **Post history backed up** (regular snapshots)
- [ ] **API keys backed up** securely (not in repo)
- [ ] **Cron command documented** (in case recovery needed)
- [ ] **Recovery procedure** written (how to restore from backup)

## Ongoing Maintenance (Weekly)

- [ ] **Review logs** for errors or warnings
- [ ] **Check Facebook Insights** for engagement metrics
- [ ] **Verify 7 posts created** in past week
- [ ] **Review post quality** in feed
- [ ] **Check API usage** (Tavily, Claude)
- [ ] **Monitor costs** (should be ~$20/month)

## Ongoing Maintenance (Monthly)

- [ ] **Refresh Facebook access token** (before 60-day expiration)
- [ ] **Review engagement trends** in Facebook Insights
- [ ] **Adjust content pillar weights** if needed (in config.py)
- [ ] **Update Vietnamese prompts** based on performance
- [ ] **Back up post history** (copy to safe location)
- [ ] **Review error logs** for patterns
- [ ] **Check if any new API changes** from Facebook/Claude/Tavily

## Troubleshooting During Deployment

### Test Fails at Configuration Check
```bash
# Check if .env exists and is valid
cat scripts/.env | grep -v "^#"

# Verify all required keys are set
python3 -c "
from scripts.config import validate_config
if not validate_config():
    exit(1)
"
```

### News Fetching Fails
```bash
# Test Tavily API directly
python3 -c "
from scripts.fb_news_fetcher import NewsFetcher
from scripts import config
fetcher = NewsFetcher(config.TAVILY_API_KEY)
items = fetcher.fetch_tavily_news()
print(f'Fetched {len(items)} items')
"

# Check internet connectivity
curl -I https://www.google.com
```

### Content Generation Fails
```bash
# Test Claude API directly
python3 -c "
import anthropic
client = anthropic.Anthropic(api_key='YOUR_KEY')
response = client.messages.create(
    model='claude-3-5-sonnet-20241022',
    max_tokens=100,
    messages=[{'role': 'user', 'content': 'Hello'}]
)
print(response.content[0].text)
"
```

### Facebook Posting Fails
```bash
# Check access token validity
curl -X GET "https://graph.facebook.com/me?access_token=YOUR_TOKEN"

# Verify page ID is numeric
echo "YOUR_PAGE_ID" | grep -E '^[0-9]+$' && echo "Valid" || echo "Invalid"
```

### Cron Job Not Running
```bash
# Check if cron job exists
crontab -l | grep facebook-autoposter

# Check cron daemon is running
sudo systemctl status cron  # Linux
launchctl list | grep cron # macOS

# Check cron logs
log show --predicate 'process == "cron"' --last 1h  # macOS
grep CRON /var/log/syslog | tail -20  # Linux
```

## Go-Live Readiness

Once all checkboxes are complete:

### In .env:
- [ ] FACEBOOK_PAGE_ID = Set
- [ ] FACEBOOK_ACCESS_TOKEN = Set and validated
- [ ] CLAUDE_API_KEY = Set and validated
- [ ] TAVILY_API_KEY = Set and validated

### In scripts:
- [ ] All 5 main scripts present and executable
- [ ] config.py contains correct system prompts
- [ ] Content pillar weights appropriate for your brand

### Cron Setup:
- [ ] Cron job installed and active
- [ ] Random posting time within 1-4pm Vietnam time
- [ ] Log directory exists and is writable
- [ ] Data directory exists and is writable

### Monitoring:
- [ ] Someone assigned to check logs daily for first week
- [ ] Someone assigned to monitor Facebook Insights
- [ ] Someone assigned to handle escalations
- [ ] Error notification system in place (optional but recommended)

### Documentation:
- [ ] All team members know location of logs
- [ ] All team members know how to run health check
- [ ] All team members know how to pause automation
- [ ] Emergency procedures documented

## Sign-Off

When all sections are complete and verified:

```
System Name: AI Thực Chiến Facebook Autoposter
Deployed Date: _______________
Deployed By: _______________
Reviewed By: _______________

✓ All technical requirements met
✓ All security requirements met
✓ All monitoring requirements met
✓ Ready for production use

Notes:
_____________________________________________________________
_____________________________________________________________
```

---

**After completing this checklist, your system is production-ready and should run smoothly for months with minimal maintenance.**

Good luck! 🚀
