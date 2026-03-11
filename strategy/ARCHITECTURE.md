# System Architecture - AI Thực Chiến Facebook Autoposter

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│                    DAILY POSTING CYCLE (1-4pm VN)                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                ┌─────────────────┼─────────────────┐
                │                 │                 │
           ┌────▼────┐       ┌────▼────┐       ┌────▼────┐
           │ FETCH   │       │ GENERATE │       │  POST   │
           │ NEWS    │──────▶│ CONTENT  │──────▶│   TO    │
           │         │       │          │       │ FACEBOOK│
           └─────────┘       └──────────┘       └─────────┘
                │                 │                 │
        ┌───────▼─────────┐ ┌─────▼──────┐ ┌──────▼────────┐
        │ Tavily API      │ │ Claude API  │ │ Graph API v18 │
        │ RSS Feeds       │ │ 4 Pillars   │ │ With Retries  │
        └─────────────────┘ └─────────────┘ └────────────────┘
                │                                     │
        ┌───────▼──────────────────────────────────────▼──────┐
        │          POST HISTORY & LOGGING SYSTEM              │
        │  data/post_history.json | logs/autoposter_*.log    │
        └──────────────────────────────────────────────────────┘
```

## Module Architecture

### 1. Main Orchestrator: `facebook-autoposter.py`

**Responsibility**: Coordinate the entire posting pipeline

**Key Classes**:

#### `FacebookAutoPoster`
```python
class FacebookAutoPoster:
    def __init__(self)
        # Initialize all components
        # Validate configuration

    def run(self) -> bool
        # Execute full pipeline:
        # 1. Fetch news
        # 2. Check history
        # 3. Select pillar
        # 4. Generate content
        # 5. Post to Facebook
        # 6. Record history

    def select_content_pillar(self) -> str
        # Weighted random selection from CONTENT_PILLARS
```

#### `PostHistory`
```python
class PostHistory:
    def add_post(...)
        # Record post to history
        # Prevent duplicates

    def has_similar_post(...) -> bool
        # Check for duplicate topics in last N days

    def get_stats() -> dict
        # Return posting statistics
```

#### `FacebookPoster`
```python
class FacebookPoster:
    def post_with_retry(...) -> str | None
        # Post to Facebook
        # Handle rate limits (429)
        # Handle auth errors (401)
        # Exponential backoff retry
```

**Error Handling**:
- Configuration validation at startup
- Try/catch around news fetching
- Duplicate detection via history check
- Retry logic with exponential backoff
- Comprehensive logging at every step

**Flow**:
```
START
  │
  ├─ Validate config (API keys, credentials)
  │
  ├─ Fetch news from Tavily or RSS
  │  └─ Log: "✓ Fetched 5 items"
  │
  ├─ Check if similar post exists in history
  │  └─ Skip if duplicate found
  │
  ├─ Randomly select content pillar (40/30/20/10 weights)
  │  └─ Log: "✓ Selected pillar: ai_news_hot_take"
  │
  ├─ Generate Vietnamese post via Claude
  │  └─ Log: "✓ Generated post (245 chars)"
  │
  ├─ Preview post content
  │  └─ Log full post for debugging
  │
  ├─ Post to Facebook with retry (max 3 attempts)
  │  ├─ 200 OK → Record success, log post ID
  │  ├─ 429 Rate Limit → Wait 5s * 2^attempt, retry
  │  ├─ 401 Auth Error → Log and abort
  │  └─ Other error → Log and retry
  │
  ├─ Add post to history
  │  └─ Log: "Total posts: 42"
  │
  └─ END (success/failure reported)
```

### 2. News Fetcher Module: `fb_news_fetcher.py`

**Responsibility**: Source AI news from multiple providers

**Key Classes**:

#### `NewsItem` (Data Class)
```python
@dataclass
class NewsItem:
    title: str
    summary: str
    source: str
    url: str
    published_date: Optional[str]
    relevance_score: float  # 0.0 to 1.0
```

#### `NewsFetcher`
```python
class NewsFetcher:
    def fetch_tavily_news() -> List[NewsItem]
        # Query Tavily API
        # Parse results
        # Return up to 5 items

    def fetch_rss_news() -> List[NewsItem]
        # Parse configured RSS feeds
        # Extract last 5 entries per feed
        # Return deduplicated list

    def fetch_all_news() -> List[NewsItem]
        # Try Tavily first
        # Fallback to RSS if needed
        # Deduplicate by title
        # Return full list

    def get_news_for_post() -> Optional[NewsItem]
        # Get single best news item
        # Usually the first (most recent)
```

**News Sources**:
- **Primary**: Tavily API (real-time web search)
  - Query: "AI news automation Vietnam technology"
  - Returns: URL, title, content summary

- **Fallback**: RSS feeds
  - TechCrunch AI
  - The Verge Tech
  - Bloomberg Markets
  - Configurable in `config.py`

**Data Flow**:
```
                    ┌─────────────────┐
                    │ AI News Query   │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
   ┌────▼────┐          ┌────▼────┐         ┌────▼────┐
   │ Tavily   │          │ RSS Feed1│         │ RSS Feed2│
   │ API      │          │ TechCrunch         │  Verge  │
   └────┬────┘          └────┬────┘         └────┬────┘
        │                    │                    │
        └────────┬───────────┼───────────┬────────┘
                 │           │           │
           ┌─────▼─────────────────────────▼────┐
           │  Deduplicate by Title              │
           │  Assign Relevance Scores           │
           │  Sort by Recency                   │
           └─────────┬───────────────────────────┘
                     │
                ┌────▼─────┐
                │ NewsItem  │
                │ List      │
                └─────┬─────┘
                      │
                 ┌────▼──────────┐
                 │ Return First   │
                 │ Item to Post   │
                 └────────────────┘
```

**Error Handling**:
- Tavily client initialization failures logged as warning, doesn't crash
- RSS parsing errors logged per-feed, continues with other feeds
- Missing fields handled gracefully (defaults to empty string)
- Returns empty list if all sources fail

### 3. Content Generator Module: `fb_content_generator.py`

**Responsibility**: Transform news into Vietnamese Facebook posts

**Key Classes**:

#### `GeneratedPost` (Data Class)
```python
@dataclass
class GeneratedPost:
    content: str              # The post text
    pillar: str              # Content type
    news_title: Optional[str]  # Source news title
    image_prompt: Optional[str] # For future image generation
```

#### `ContentGenerator`
```python
class ContentGenerator:
    def generate_post(
        news_item: NewsItem,
        pillar: str
    ) -> Optional[GeneratedPost]
        # Select appropriate system prompt by pillar
        # Build user message from news item
        # Call Claude API
        # Parse response
        # Generate image prompt
        # Return GeneratedPost

    def _build_user_message(...) -> str
        # Format news item for Claude
        # Different format per pillar type

    def _generate_image_prompt(...) -> str
        # Create prompt for optional image generation
        # Pillar-specific visual suggestions
```

**Content Pillars & System Prompts**:

All prompts are in `config.py`:

1. **AI News + Hot Take (40%)**
   - Hook: Strong opening line about AI news
   - Body: Explain news in simple Vietnamese
   - Benefit: How it helps SMBs make money/save time
   - Includes: Specific use case, result
   - CTA: "DM 'TỰ ĐỘNG'"

2. **Automation Wins (30%)**
   - Hook: Concrete result (e.g., "+45% sales")
   - Story: Before/after situation
   - Numbers: Specific metrics and timeline
   - Lesson: Actionable insight
   - CTA: "DM 'TỰ ĐỘNG'"

3. **Tool Reviews (20%)**
   - Hook: Tool name + key benefit
   - What: Simple explanation of tool
   - Pros: 2-3 benefits for SMBs
   - Cons: 1-2 honest limitations
   - Price: Cost info
   - Best For: Target use case
   - CTA: "DM 'TỰ ĐỘNG'"

4. **Behind the Scenes (10%)**
   - Hook: Honest challenge or insight
   - Context: Setting and situation
   - Solution: How AI/automation helped
   - Lesson: Applicable to reader's business
   - Tone: Humble, authentic
   - CTA: "DM 'TỰ ĐỘNG'"

**Claude API Call**:
```
Request:
  model: "claude-3-5-sonnet-20241022"
  max_tokens: 1024
  system: [pillar-specific system prompt]
  messages: [user message with news content]

Response:
  → Parse first text block
  → Extract post content
  → Generate image prompt
  → Return GeneratedPost
```

**Prompt Engineering Details**:

Each system prompt includes:
- Target audience (Vietnamese SMBs, 25-55)
- Tone guidelines (friendly, practical, no jargon)
- Structure (hook → value → CTA)
- Writing style (short sentences, emoji, emotion)
- Length target (150-250 words)
- Vietnamese language specifics

Example Hook Elements:
- Emotional triggers: "Game changer!", "Tiết kiệm 10 giờ"
- Specificity: Numbers, concrete examples
- Relevance: Direct to business benefits
- Urgency: "Just released", "Available now"

### 4. Configuration Module: `config.py`

**Responsibility**: Centralized settings management

**Key Sections**:

```python
# 1. API Credentials (from environment)
FACEBOOK_PAGE_ID
FACEBOOK_ACCESS_TOKEN
CLAUDE_API_KEY
TAVILY_API_KEY

# 2. Content Pillar Weights
CONTENT_PILLARS = {
    "ai_news_hot_take": 0.40,
    "automation_wins": 0.30,
    "tool_reviews": 0.20,
    "behind_the_scenes": 0.10,
}

# 3. Posting Schedule
POST_WINDOW_START = 13  # 1pm Vietnam time
POST_WINDOW_END = 16    # 4pm Vietnam time

# 4. System Prompts (4 different ones)
SYSTEM_PROMPTS = {
    "ai_news_hot_take": "...",
    "automation_wins": "...",
    "tool_reviews": "...",
    "behind_the_scenes": "...",
}

# 5. News Sources
RSS_FEEDS = [...]
TAVILY_SEARCH_PARAMS = {...}

# 6. Logging & History
LOG_DIR, HISTORY_FILE, DATA_DIR

# 7. Error Handling
MAX_RETRIES, RETRY_DELAY_SECONDS

# 8. Validation
validate_config() -> bool
```

## Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                  COMPLETE DATA FLOW                          │
└──────────────────────────────────────────────────────────────┘

TIME: Random within 1-4pm Vietnam (GMT+7) daily
  │
  │ STEP 1: NEWS FETCHING
  ├─────────────────────────────────────────────────────────────
  │
  │ Tavily API Request
  │ ├─ Query: "AI news automation Vietnam"
  │ ├─ Max Results: 5
  │ └─ Return: Title, Summary, URL, Source
  │
  │ NewsItem Objects Created
  │ ├─ title: str
  │ ├─ summary: str
  │ ├─ source: str
  │ ├─ url: str
  │ ├─ published_date: str
  │ └─ relevance_score: 0.9
  │
  │ Deduplication
  │ └─ Remove duplicate titles
  │
  ├─ [Log] ✓ Fetched 5 items from Tavily
  │
  │ STEP 2: HISTORY CHECK
  ├─────────────────────────────────────────────────────────────
  │
  │ Load post_history.json
  │ ├─ Check last 7 days of posts
  │ ├─ Look for matching news title
  │ └─ Compare relevance_score
  │
  │ If Similar Post Found:
  │ ├─ [Log] ⚠ Similar post found in history: "..."
  │ └─ EXIT (skip this run)
  │
  │ If Unique:
  │ └─ [Log] ✓ No similar posts, proceeding
  │
  │ STEP 3: PILLAR SELECTION
  ├─────────────────────────────────────────────────────────────
  │
  │ Random Selection (Weighted)
  │ ├─ 40% chance: ai_news_hot_take
  │ ├─ 30% chance: automation_wins
  │ ├─ 20% chance: tool_reviews
  │ └─ 10% chance: behind_the_scenes
  │
  │ ├─ [Log] ✓ Selected pillar: ai_news_hot_take
  │
  │ STEP 4: CONTENT GENERATION
  ├─────────────────────────────────────────────────────────────
  │
  │ Claude API Request
  │ ├─ System Prompt: pillar-specific system message
  │ │  └─ Includes brand voice, structure, Vietnamese guidelines
  │ ├─ User Message:
  │ │  ├─ News title
  │ │  ├─ News source
  │ │  ├─ News summary
  │ │  └─ Pillar-specific instructions
  │ └─ Response: Vietnamese post (150-250 words)
  │
  │ Post Structure:
  │ ├─ Hook (emotional, benefit-focused, <15 words)
  │ ├─ Body (value, benefits, specific examples)
  │ ├─ Call-to-Action ("DM mình 'TỰ ĐỘNG'...")
  │ └─ Emoji (3-5, strategic placement)
  │
  │ Image Prompt Generated
  │ └─ For future visual enhancement
  │
  │ GeneratedPost Created
  │ ├─ content: str
  │ ├─ pillar: str
  │ ├─ news_title: str
  │ └─ image_prompt: str
  │
  │ ├─ [Log] ✓ Generated post (245 chars)
  │ ├─ [Log] Preview: [full post content]
  │
  │ STEP 5: FACEBOOK POSTING
  ├─────────────────────────────────────────────────────────────
  │
  │ Facebook Graph API Request
  │ ├─ POST https://graph.facebook.com/v18.0/{page_id}/feed
  │ ├─ Params:
  │ │  ├─ message: [post content]
  │ │  └─ access_token: [long-lived token]
  │ └─ Response: {"id": "post_id"}
  │
  │ Success (200):
  │ ├─ [Log] ✓ Post published successfully: {post_id}
  │
  │ Rate Limited (429):
  │ ├─ Wait: 5s * 2^attempt
  │ └─ Retry (max 3 times)
  │
  │ Auth Error (401):
  │ ├─ [Log] ✗ Authentication failed - refresh token
  │ └─ EXIT
  │
  │ Other Error (4xx/5xx):
  │ ├─ Retry with exponential backoff
  │ └─ Fail after 3 attempts
  │
  │ STEP 6: HISTORY RECORDING
  ├─────────────────────────────────────────────────────────────
  │
  │ Create History Entry
  │ ├─ timestamp: ISO format
  │ ├─ news_title: str
  │ ├─ pillar: str
  │ ├─ content_hash: MD5 of post content
  │ └─ facebook_post_id: str
  │
  │ Write to post_history.json
  │ └─ Append entry to array
  │
  │ ├─ [Log] ✓ Added post to history (total: 42)
  │ ├─ [Log] Total posts: 42
  │ ├─ [Log]   ai_news_hot_take: 17
  │ ├─ [Log]   automation_wins: 12
  │ ├─ [Log]   tool_reviews: 10
  │ └─ [Log]   behind_the_scenes: 3
  │
  │ STEP 7: COMPLETION
  ├─────────────────────────────────────────────────────────────
  │
  │ [Log] ✓ AUTOPOSTER RUN COMPLETED SUCCESSFULLY
  │ [Log] Next run: Tomorrow at {random time}
  │
  └─────────────────────────────────────────────────────────────
```

## Error Handling Strategy

### Level 1: Startup Validation
```python
# In __init__:
if not config.validate_config():
    raise ValueError("Configuration validation failed")
```

### Level 2: API Call Protection
```python
try:
    response = requests.post(url, ...)
except requests.exceptions.Timeout:
    # Exponential backoff retry
except requests.exceptions.ConnectionError:
    # Network error, log and retry
except Exception as e:
    # Unexpected error, log and fail
```

### Level 3: Logic Protection
```python
if not news_item:
    logger.error("No news found, aborting")
    return False

if self.history.has_similar_post(...):
    logger.warning("Similar post found, skipping")
    return False

if not post:
    logger.error("Content generation failed, aborting")
    return False
```

### Level 4: Graceful Degradation
```python
# Tavily fails → fallback to RSS
if not tavily_items:
    logger.info("Tavily returned no results, using RSS feeds")
    rss_items = self.fetch_rss_news(config.RSS_FEEDS)

# RSS also fails → abort gracefully
if not all_news:
    logger.error("No news items found from any source")
    return False
```

## Cron Scheduling

**When**: Daily at random time within 1-4pm Vietnam time (GMT+7)

**How**:
1. `setup-cron.sh` generates random hour (13, 14, or 15)
2. Generates random minute (0-59)
3. Installs crontab entry:
   ```
   {hour} {minute} * * * cd /scripts && . .env && python3 facebook-autoposter.py --run-once
   ```

**Benefits**:
- Avoids exact hour boundaries
- Distributes load if running multiple instances
- Appears more organic (not robotic)

**Monitoring**:
- Logs go to `logs/autoposter_cron.log`
- Health check script provided: `health-check.sh`
- Manual run possible: `python3 facebook-autoposter.py --run-once`

## Security Considerations

### API Keys
- All keys stored in `.env` (git-ignored)
- Keys loaded via `python-dotenv`
- Validated at startup
- Never logged in output
- Used only for their specific API calls

### Access Tokens
- Facebook tokens are long-lived (60 days)
- Should be refreshed before expiration
- Token rotation recommended monthly
- Compromised token immediately rotates

### Data Privacy
- Post history contains only metadata (no sensitive data)
- News summaries are from public sources
- No user data collected or transmitted
- Logs contain only operational info

### Error Messages
- Errors logged with full context for debugging
- User-facing messages are safe and don't leak details
- API errors not passed to user directly

## Performance Characteristics

### Time Complexity
- **News fetching**: O(n) where n = number of API results (5-10)
- **Deduplication**: O(n log n) for title sorting
- **History check**: O(m) where m = posts in history (usually 30-400)
- **Content generation**: Fixed time (Claude API call)
- **Posting**: Fixed time (1 API call with retries)

### Space Complexity
- **Memory**: O(n + m) where n = news items, m = history entries
- **Disk**: Post history grows by ~500 bytes per post (~15KB/month)
- **Logs**: ~2-5KB per run (~60KB/month)

### Network Usage
- **Per run**: ~50KB total (news fetch + API calls)
- **Monthly**: ~1.5MB total
- **Costs**: Minimal ($20/month for APIs)

## Extension Points

### Adding News Sources
1. Create new fetcher method in `NewsFetcher`
2. Add to `fetch_all_news()`
3. Return `List[NewsItem]`

### Adding Content Pillars
1. Add to `CONTENT_PILLARS` in `config.py` with weight
2. Add system prompt to `SYSTEM_PROMPTS`
3. Adjust weights to sum to 1.0

### Custom Posting Destination
1. Create new `Poster` class matching interface
2. Implement `post_with_retry(message) -> Optional[str]`
3. Use in `FacebookAutoPoster.run()`

### Advanced Analytics
1. Log engagement metrics from Facebook API
2. Store in separate analytics database
3. Feed back into pillar weighting algorithm

---

**Architecture Version**: 1.0
**Last Updated**: March 2024
