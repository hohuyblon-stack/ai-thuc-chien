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
ENV_FILE="$SCRIPT_DIR/.env"

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
log_info "Setting up cron job..."

# Generate a random time within 1-4pm Vietnam time (13:00-16:00)
# Vietnam time = UTC+7
# We'll randomize the minute to avoid exact hour boundaries
RANDOM_HOUR=$((13 + RANDOM % 3))  # 13, 14, or 15 (1pm, 2pm, 3pm)
RANDOM_MINUTE=$((RANDOM % 60))    # 0-59

log_info "Generated random posting time: ${RANDOM_HOUR}:${RANDOM_MINUTE} Vietnam time (GMT+7)"

# Create the cron job command
# Using absolute paths for security
VENV_PYTHON="$PROJECT_DIR/venv/bin/python3"
AUTOPOSTER_SCRIPT="$SCRIPT_DIR/facebook-autoposter.py"
LOG_FILE="$LOG_DIR/autoposter_cron.log"

# The cron command with error handling and logging
CRON_COMMAND="$RANDOM_HOUR $RANDOM_MINUTE * * * cd $SCRIPT_DIR && . $ENV_FILE && $VENV_PYTHON $AUTOPOSTER_SCRIPT --run-once >> $LOG_FILE 2>&1 || echo \"[ERROR] Autoposter failed at \$(date)\" >> $LOG_FILE"

log_info "Cron command:"
echo "  $RANDOM_HOUR $RANDOM_MINUTE * * * cd $SCRIPT_DIR && . $ENV_FILE && $VENV_PYTHON $AUTOPOSTER_SCRIPT --run-once >> $LOG_FILE 2>&1"

# Check if job already exists
EXISTING_CRON=$(crontab -l 2>/dev/null | grep -c "facebook-autoposter.py" || echo 0)

if [ "$EXISTING_CRON" -gt 0 ]; then
    log_warning "Existing autoposter cron job found"
    read -p "Do you want to replace it? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Remove existing job
        crontab -l 2>/dev/null | grep -v "facebook-autoposter.py" | crontab -
        log_success "Removed existing cron job"
    else
        log_info "Keeping existing cron job"
        exit 0
    fi
fi

# Add new cron job
(crontab -l 2>/dev/null || echo ""; echo "$CRON_COMMAND") | crontab -

log_success "Cron job installed"

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
        echo "Log rotated at \$(date)" >> $LOG_FILE
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

# Check if cron job is installed
if crontab -l 2>/dev/null | grep -q "facebook-autoposter.py"; then
    echo "✓ Cron job is installed"
else
    echo "✗ Cron job is NOT installed"
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
    if [ -z "$FACEBOOK_PAGE_ID" ] || [ -z "$FACEBOOK_ACCESS_TOKEN" ] || [ -z "$CLAUDE_API_KEY" ] || [ -z "$TAVILY_API_KEY" ]; then
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
echo "📋 Configuration Summary:"
echo "  Project directory: $PROJECT_DIR"
echo "  Scripts directory: $SCRIPT_DIR"
echo "  Logs directory: $LOG_DIR"
echo "  Data directory: $DATA_DIR"
echo "  Log file: $LOG_FILE"
echo ""
echo "🕐 Posting Schedule:"
echo "  Time: ${RANDOM_HOUR}:${RANDOM_MINUTE} Vietnam time (GMT+7) daily"
echo "  Command: Check crontab with 'crontab -l'"
echo ""
echo "📊 Monitor your posts:"
echo "  View logs: tail -f $LOG_FILE"
echo "  Health check: bash $HEALTH_CHECK_SCRIPT"
echo "  View stats: $VENV_PYTHON $AUTOPOSTER_SCRIPT --stats"
echo ""
echo "🔧 Troubleshooting:"
echo "  Check cron logs: log show --predicate 'process == \"cron\"' --last 1h (macOS)"
echo "  Check .env file: cat $SCRIPT_DIR/.env"
echo ""
echo "Next steps:"
echo "  1. Review the log file: tail -f $LOG_FILE"
echo "  2. Run health check: bash $HEALTH_CHECK_SCRIPT"
echo "  3. Your posts will be published daily at ${RANDOM_HOUR}:${RANDOM_MINUTE} Vietnam time"
echo ""
