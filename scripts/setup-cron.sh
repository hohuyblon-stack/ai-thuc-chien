#!/bin/bash
#
# Setup cron job for AI Thực Chiến Facebook Autoposter
# This script configures the daily posting schedule at random times between 1-4pm Vietnam time
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
DATA_DIR="$PROJECT_DIR/data"
ENV_FILE="$PROJECT_DIR/.env"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

log_info() {
    echo -e "${BLUE}ℹ ${1}${NC}"
}

log_success() {
    echo -e "${GREEN}✓ ${1}${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠ ${1}${NC}"
}

log_error() {
    echo -e "${RED}✗ ${1}${NC}"
}

# ============================================================================
# PRE-FLIGHT CHECKS
# ============================================================================

log_info "Running pre-flight checks..."

# Check if .env file exists
if [ ! -f "$ENV_FILE" ]; then
    log_error ".env file not found at $ENV_FILE"
    echo ""
    echo "Please copy .env.example to .env and fill in your API keys:"
    echo "  cp $SCRIPT_DIR/.env.example $ENV_FILE"
    echo ""
    exit 1
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    log_error "Python 3 is not installed"
    exit 1
fi

log_success "Python 3 found: $(python3 --version)"

# Check if virtualenv exists
if [ ! -d "$PROJECT_DIR/venv" ]; then
    log_error "Virtual environment not found at $PROJECT_DIR/venv"
    echo ""
    echo "Please create it first:"
    echo "  cd $PROJECT_DIR"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r scripts/requirements.txt"
    echo ""
    exit 1
fi

log_success "Virtual environment found"

# Create directories if they don't exist
mkdir -p "$LOG_DIR"
mkdir -p "$DATA_DIR"

# ============================================================================
# CRON JOB SETUP
# ============================================================================

log_info ""
log_info "Setting up cron jobs..."

VENV_PYTHON="$PROJECT_DIR/venv/bin/python3"
PIPELINE_SCRIPT="$SCRIPT_DIR/daily_pipeline.py"
AUTOPOSTER_SCRIPT="$SCRIPT_DIR/facebook-autoposter.py"

# NOTE: All times below are in Vietnam time (GMT+7).
# If your server is NOT in GMT+7, adjust accordingly or set TZ in cron:
#   TZ=Asia/Ho_Chi_Minh
# To check server timezone: timedatectl or date +%Z

# --- Facebook Autoposter (1-4pm Vietnam time) ---
FB_HOUR=$((13 + RANDOM % 3))
FB_MINUTE=$((RANDOM % 60))
FB_LOG="$LOG_DIR/autoposter_cron.log"
FB_CRON="$FB_HOUR $FB_MINUTE * * * cd $SCRIPT_DIR && . $ENV_FILE && $VENV_PYTHON $AUTOPOSTER_SCRIPT --run-once >> $FB_LOG 2>&1 || echo \"[ERROR] FB Autoposter failed at \$(date)\" >> $FB_LOG"

log_info "Facebook: ${FB_HOUR}:$(printf '%02d' $FB_MINUTE) Vietnam time"

# --- YouTube Daily Pipeline (8-10am Vietnam time — morning content) ---
YT_HOUR=$((8 + RANDOM % 2))
YT_MINUTE=$((RANDOM % 60))
YT_LOG="$LOG_DIR/youtube_pipeline_cron.log"
YT_CRON="$YT_HOUR $YT_MINUTE * * * cd $SCRIPT_DIR && . $ENV_FILE && $VENV_PYTHON $PIPELINE_SCRIPT --platform youtube --format long >> $YT_LOG 2>&1 || echo \"[ERROR] YouTube pipeline failed at \$(date)\" >> $YT_LOG"

log_info "YouTube:  ${YT_HOUR}:$(printf '%02d' $YT_MINUTE) Vietnam time (long-form)"

# --- TikTok Daily Pipeline (11am-1pm Vietnam time — lunch time content) ---
TT_HOUR=$((11 + RANDOM % 2))
TT_MINUTE=$((RANDOM % 60))
TT_LOG="$LOG_DIR/tiktok_pipeline_cron.log"
TT_CRON="$TT_HOUR $TT_MINUTE * * * cd $SCRIPT_DIR && . $ENV_FILE && $VENV_PYTHON $PIPELINE_SCRIPT --platform tiktok --format short >> $TT_LOG 2>&1 || echo \"[ERROR] TikTok pipeline failed at \$(date)\" >> $TT_LOG"

log_info "TikTok:   ${TT_HOUR}:$(printf '%02d' $TT_MINUTE) Vietnam time (short-form)"

# Remove existing AI Thuc Chien cron jobs
EXISTING_CRON=$(crontab -l 2>/dev/null | grep -c -E "(facebook-autoposter|daily_pipeline)" || echo 0)

if [ "$EXISTING_CRON" -gt 0 ]; then
    log_warning "Existing cron jobs found ($EXISTING_CRON)"
    read -p "Do you want to replace them? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        crontab -l 2>/dev/null | grep -v -E "(facebook-autoposter|daily_pipeline)" | crontab -
        log_success "Removed existing cron jobs"
    else
        log_info "Keeping existing cron jobs"
        exit 0
    fi
fi

# Add all cron jobs
(crontab -l 2>/dev/null || echo ""
echo "# --- AI Thuc Chien Automation ---"
echo "CRON_TZ=Asia/Ho_Chi_Minh"
echo "$FB_CRON"
echo "$YT_CRON"
echo "$TT_CRON"
) | crontab -

log_success "All cron jobs installed (Facebook + YouTube + TikTok)"

# ============================================================================
# LOG ROTATION SETUP
# ============================================================================

log_info ""
log_info "Setting up log rotation..."

LOGROTATE_CONFIG="/tmp/autoposter-logrotate"

cat > "$LOGROTATE_CONFIG" << EOF
$LOG_DIR/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 \$(whoami) \$(whoami)
    sharedscripts
    postrotate
        echo "Log rotated at \$(date)" >> $LOG_DIR/logrotate.log
    endscript
}
EOF

# Note: logrotate requires sudo, so we'll just create the config and inform the user
log_info "Log rotation config template created"

# Try to install logrotate if on macOS with Homebrew
if command -v brew &> /dev/null; then
    if ! command -v logrotate &> /dev/null; then
        log_warning "logrotate not found. Install with: brew install logrotate"
    else
        log_success "logrotate is available"
    fi
elif command -v apt-get &> /dev/null; then
    if ! command -v logrotate &> /dev/null; then
        log_warning "logrotate not found. Install with: sudo apt-get install logrotate"
    else
        log_success "logrotate is available"
    fi
fi

# ============================================================================
# HEALTH CHECK
# ============================================================================

log_info ""
log_info "Setting up health checks..."

# Create a simple health check script
HEALTH_CHECK_SCRIPT="$SCRIPT_DIR/health-check.sh"

cat > "$HEALTH_CHECK_SCRIPT" << 'HEALTH_EOF'
#!/bin/bash
# Health check for autoposter - run this periodically to verify the system is working

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
DATA_DIR="$PROJECT_DIR/data"

# Check if cron jobs are installed
FB_CRON=$(crontab -l 2>/dev/null | grep -c "facebook-autoposter" || echo 0)
YT_CRON=$(crontab -l 2>/dev/null | grep -c "daily_pipeline.*youtube" || echo 0)
TT_CRON=$(crontab -l 2>/dev/null | grep -c "daily_pipeline.*tiktok" || echo 0)
echo "Cron jobs: Facebook=$FB_CRON YouTube=$YT_CRON TikTok=$TT_CRON"
if [ "$FB_CRON" -gt 0 ] && [ "$YT_CRON" -gt 0 ] && [ "$TT_CRON" -gt 0 ]; then
    echo "✓ All cron jobs installed"
else
    echo "⚠ Some cron jobs missing — run setup-cron.sh"
fi

# Check logs
if [ -f "$LOG_DIR/autoposter_cron.log" ]; then
    LAST_RUN=$(tail -1 "$LOG_DIR/autoposter_cron.log" | head -1)
    echo "✓ Last run: $LAST_RUN"
else
    echo "⚠ No logs found yet"
fi

# Check history
if [ -f "$DATA_DIR/post_history.json" ]; then
    POST_COUNT=$(grep -c '"timestamp"' "$DATA_DIR/post_history.json" || echo "0")
    echo "✓ Total posts created: $POST_COUNT"
else
    echo "⚠ No post history found yet"
fi

# Check API keys
if [ -f "$SCRIPT_DIR/.env" ]; then
    . "$SCRIPT_DIR/.env"
    if [ -z "$FACEBOOK_PAGE_ID" ] || [ -z "$FACEBOOK_ACCESS_TOKEN" ] || [ -z "${ANTHROPIC_API_KEY:-$CLAUDE_API_KEY}" ] || [ -z "$TAVILY_API_KEY" ]; then
        echo "✗ Missing required API keys in .env"
    else
        echo "✓ All required API keys are configured"
    fi
else
    echo "✗ .env file not found"
fi
HEALTH_EOF

chmod +x "$HEALTH_CHECK_SCRIPT"
log_success "Health check script created at $HEALTH_CHECK_SCRIPT"

# ============================================================================
# TEST RUN
# ============================================================================

log_info ""
read -p "Do you want to run a test post now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "Running test..."
    cd "$SCRIPT_DIR"
    source "$ENV_FILE"
    source "$PROJECT_DIR/venv/bin/activate"

    $VENV_PYTHON $AUTOPOSTER_SCRIPT --run-once

    if [ $? -eq 0 ]; then
        log_success "Test run completed successfully"
    else
        log_warning "Test run failed - check logs at $LOG_DIR"
    fi
fi

# ============================================================================
# SUMMARY
# ============================================================================

log_info ""
log_info "=========================================="
log_success "SETUP COMPLETED!"
log_info "=========================================="
echo ""
echo "Configuration Summary:"
echo "  Project directory: $PROJECT_DIR"
echo "  Scripts directory: $SCRIPT_DIR"
echo "  Logs directory: $LOG_DIR"
echo "  Data directory: $DATA_DIR"
echo ""
echo "Posting Schedule (Vietnam time, GMT+7):"
echo "  YouTube:  ${YT_HOUR}:$(printf '%02d' $YT_MINUTE) daily (long-form)"
echo "  TikTok:   ${TT_HOUR}:$(printf '%02d' $TT_MINUTE) daily (short-form)"
echo "  Facebook: ${FB_HOUR}:$(printf '%02d' $FB_MINUTE) daily (text post)"
echo "  Check crontab: crontab -l"
echo ""
echo "Monitor:"
echo "  YouTube logs:  tail -f $LOG_DIR/youtube_pipeline_cron.log"
echo "  TikTok logs:   tail -f $LOG_DIR/tiktok_pipeline_cron.log"
echo "  Facebook logs: tail -f $LOG_DIR/autoposter_cron.log"
echo "  Health check:  bash $HEALTH_CHECK_SCRIPT"
echo ""
echo "Manual runs:"
echo "  Full pipeline:   $VENV_PYTHON $PIPELINE_SCRIPT --dry-run"
echo "  YouTube only:    $VENV_PYTHON $PIPELINE_SCRIPT --platform youtube --dry-run"
echo "  TikTok only:     $VENV_PYTHON $PIPELINE_SCRIPT --platform tiktok --format short --dry-run"
echo "  Facebook only:   $VENV_PYTHON $AUTOPOSTER_SCRIPT --run-once"
echo ""
