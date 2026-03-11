"""
Configuration for AI Thực Chiến Facebook Automation
"""
import os
from typing import Dict, List
from datetime import time

# ============================================================================
# API KEYS & CREDENTIALS
# ============================================================================
FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID", "")
FACEBOOK_ACCESS_TOKEN = os.getenv("FACEBOOK_ACCESS_TOKEN", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY", "")
CLAUDE_API_KEY = ANTHROPIC_API_KEY  # backward compat
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

# ============================================================================
# CONTENT PILLAR WEIGHTS
# ============================================================================
# Determines random selection of content type when posting
CONTENT_PILLARS = {
    "ai_news_hot_take": 0.40,      # 40%: AI News + Hot Take
    "automation_wins": 0.30,        # 30%: Automation Wins/Case Studies
    "tool_reviews": 0.20,           # 20%: Tool Reviews
    "behind_the_scenes": 0.10,      # 10%: Behind the Scenes
}

# ============================================================================
# POSTING SCHEDULE
# ============================================================================
# Vietnam time is GMT+7
POST_WINDOW_START = 13  # 1pm
POST_WINDOW_END = 16    # 4pm (posts between 1-4pm)
TIMEZONE_OFFSET = 7     # GMT+7

# ============================================================================
# LOGGING & HISTORY
# ============================================================================
LOG_DIR = os.path.dirname(__file__) + "/../logs"
HISTORY_FILE = os.path.dirname(__file__) + "/../data/post_history.json"
DATA_DIR = os.path.dirname(__file__) + "/../data"

# ============================================================================
# VIETNAMESE COPYWRITING PROMPTS
# ============================================================================
SYSTEM_PROMPTS = {
    "ai_news_hot_take": """Bạn là một chuyên gia viết nội dung cho Facebook Page "AI Thực Chiến" - một trang dành cho chủ doanh nghiệp, bán hàng online, và solopreneur người Việt (25-55 tuổi).

Hãy viết một bài post Facebook về tin tức AI mới nhất với:
1. Hook mạnh mẽ ở câu đầu tiên (không quá 15 từ) - gây tò mò, gây cảm xúc, liên quan đến lợi ích business
2. Giải thích đơn giản tin tức này có ý nghĩa gì (không dùng thuật ngữ kỹ thuật)
3. Cụ thể: Nó có thể giúp business của họ kiếm tiền thêm, tiết kiệm thời gian, hay bán hàng nhiều hơn?
4. Câu kết thúc là CTA rõ ràng: "DM mình 'TỰ ĐỘNG' nếu bạn muốn áp dụng cho business của mình"
5. Tông giọng: thân thiết, thực dụng, không quá kỹ thuật
6. Dùng emoji hợp lý (3-5 emoji), dấu xuống dòng để dễ đọc
7. Độ dài: 150-250 từ

Bài post phải gây hứng thú, không quá dài, và rõ ràng lợi ích cho reader.""",

    "automation_wins": """Bạn là một chuyên gia viết case study & automation wins cho Facebook Page "AI Thực Chiến".

Hãy viết một bài post về cách AI/Automation giúp business đạt kết quả thực tế:
1. Hook: Bắt đầu bằng kết quả cụ thể (ví dụ: "+30% doanh thu", "tiết kiệm 10 giờ/tuần")
2. Story: Kể ngắn gọn câu chuyện - tình huống trước, cách họ dùng AI/Automation, kết quả sau
3. Con số cụ thể: Giờ tiết kiệm, tiền kiếm thêm, phần trăm tăng trưởng
4. Bài học: 1-2 insights từ câu chuyện này
5. CTA: "DM mình 'TỰ ĐỘNG' nếu bạn muốn áp dụng cho business của mình"
6. Tông giọng: khoả lạc, thực tế, bằng chứng/số liệu
7. Dùng emoji (3-5), dấu xuống dòng
8. Độ dài: 150-250 từ""",

    "tool_reviews": """Bạn là một chuyên gia review AI tools cho Facebook Page "AI Thực Chiến" hướng tới business owners.

Hãy viết một bài review về một AI tool mới:
1. Hook: Tên tool + 1 benefit chính (ví dụ: "ChatGPT Plus - Hỗ trợ tạo content 10x nhanh")
2. Describe: Cái tool này làm gì? (đơn giản, không kỹ thuật)
3. Pros: 2-3 ưu điểm cụ thể cho business owners - tập trung vào tiết kiệm thời gian/chi phí
4. Cons: 1-2 hạn chế thật thà
5. Price: Giá bao nhiêu? Có free version không?
6. Best for: Phù hợp nhất cho loại business nào?
7. CTA: "DM mình 'TỰ ĐỘNG' nếu bạn muốn áp dụng cho business của mình"
8. Tông giọng: thành thật, hữu ích, không quá marketing
9. Dùng emoji (3-5), dấu xuống dòng
10. Độ dài: 150-250 từ""",

    "behind_the_scenes": """Bạn là một chuyên gia viết behind-the-scenes content cho Facebook Page "AI Thực Chiến".

Hãy viết một bài post về hậu trường, kinh nghiệm, hoặc insights từ việc xây dựng trang:
1. Chia sẻ thật thà một challenge mà bạn gặp
2. Cách bạn giải quyết nó (sử dụng AI/Automation)
3. Bài học rút ra - có thể áp dụng cho business của họ
4. Tone: người bạn, khiêm tốn, có hài hước
5. CTA: "DM mình 'TỰ ĐỘNG' nếu bạn muốn áp dụng cho business của mình"
6. Dùng emoji (3-5), dấu xuống dòng
7. Độ dài: 100-200 từ (ngắn hơn vì tính chất intimate)""",
}

# ============================================================================
# NEWS SOURCES
# ============================================================================
TAVILY_SEARCH_PARAMS = {
    "query": "AI news automation Vietnam technology",
    "search_depth": "basic",
    "max_results": 5,
}

RSS_FEEDS = [
    "https://feeds.techcrunch.com/tc-crunch/",  # TechCrunch main
    "https://feeds.theverge.com/theevergetech.xml",  # The Verge Tech
    "https://feeds.bloomberg.com/markets/news.rss",  # Bloomberg
]

# ============================================================================
# FACEBOOK GRAPH API
# ============================================================================
FACEBOOK_API_VERSION = "v21.0"
FACEBOOK_GRAPH_URL = f"https://graph.facebook.com/{FACEBOOK_API_VERSION}"

# ============================================================================
# RETRY LOGIC
# ============================================================================
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5  # Start with 5s, exponential backoff

# ============================================================================
# VALIDATION
# ============================================================================
def validate_config() -> bool:
    """Validate that all required config is present."""
    required_keys = ["FACEBOOK_PAGE_ID", "FACEBOOK_ACCESS_TOKEN", "ANTHROPIC_API_KEY", "TAVILY_API_KEY"]
    missing = [key for key in required_keys if not globals()[key]]

    if missing:
        print(f"❌ Missing required config: {', '.join(missing)}")
        print("   Please set these environment variables in .env file")
        return False

    return True
