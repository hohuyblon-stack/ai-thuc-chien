#!/bin/bash
#
# Test Setup Script - Validates that everything is configured correctly
# Run this before setting up the cron job to ensure everything works
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}ℹ ${1}${NC}"; }
log_pass() { echo -e "${GREEN}✓ ${1}${NC}"; }
log_warn() { echo -e "${YELLOW}⚠ ${1}${NC}"; }
log_fail() { echo -e "${RED}✗ ${1}${NC}"; }

TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Track results
test_check() {
    local test_name=$1
    local command=$2
    local expected_status=${3:-0}

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    if eval "$command" > /dev/null 2>&1; then
        if [ "$expected_status" -eq 0 ]; then
            log_pass "$test_name"
            PASSED_TESTS=$((PASSED_TESTS + 1))
        else
            log_fail "$test_name (expected to fail but passed)"
            FAILED_TESTS=$((FAILED_TESTS + 1))
        fi
    else
        if [ "$expected_status" -ne 0 ]; then
            log_pass "$test_name (correctly failed)"
            PASSED_TESTS=$((PASSED_TESTS + 1))
        else
            log_fail "$test_name"
            FAILED_TESTS=$((FAILED_TESTS + 1))
        fi
    fi
}

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║        AI THỰC CHIẾN - SETUP VALIDATION TEST              ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# ============================================================================
# TEST 1: Environment
# ============================================================================
log_info "TEST 1: Environment Setup"
echo ""

test_check "Python 3 is installed" "command -v python3"
test_check "Project directory exists" "[ -d '$PROJECT_DIR' ]"
test_check "Scripts directory exists" "[ -d '$SCRIPT_DIR' ]"
test_check "Virtual environment exists" "[ -d '$PROJECT_DIR/venv' ]"

echo ""

# ============================================================================
# TEST 2: Configuration Files
# ============================================================================
log_info "TEST 2: Configuration Files"
echo ""

test_check ".env.example exists" "[ -f '$SCRIPT_DIR/.env.example' ]"
test_check ".env file exists" "[ -f '$SCRIPT_DIR/.env' ]"
test_check "config.py exists" "[ -f '$SCRIPT_DIR/config.py' ]"

echo ""

# ============================================================================
# TEST 3: Python Dependencies
# ============================================================================
log_info "TEST 3: Python Dependencies"
echo ""

# Source virtual environment
if [ -f "$PROJECT_DIR/venv/bin/activate" ]; then
    source "$PROJECT_DIR/venv/bin/activate"

    test_check "anthropic package installed" "python3 -c 'import anthropic'"
    test_check "requests package installed" "python3 -c 'import requests'"
    test_check "python-dotenv package installed" "python3 -c 'import dotenv'"
    test_check "feedparser package installed" "python3 -c 'import feedparser'"

    # These are optional but recommended
    python3 -c "import tavily" 2>/dev/null && log_pass "tavily-python package installed" || log_warn "tavily-python not installed (optional)"

    deactivate 2>/dev/null || true
else
    log_fail "Virtual environment not found - please run: python3 -m venv $PROJECT_DIR/venv"
fi

echo ""

# ============================================================================
# TEST 4: Environment Variables
# ============================================================================
log_info "TEST 4: Environment Variables"
echo ""

if [ -f "$SCRIPT_DIR/.env" ]; then
    source "$SCRIPT_DIR/.env"

    # Check each required variable
    if [ -z "$FACEBOOK_PAGE_ID" ]; then
        log_fail "FACEBOOK_PAGE_ID is not set"
    else
        log_pass "FACEBOOK_PAGE_ID is set"
    fi

    if [ -z "$FACEBOOK_ACCESS_TOKEN" ]; then
        log_fail "FACEBOOK_ACCESS_TOKEN is not set"
    else
        log_pass "FACEBOOK_ACCESS_TOKEN is set (${#FACEBOOK_ACCESS_TOKEN} chars)"
    fi

    if [ -z "$CLAUDE_API_KEY" ]; then
        log_fail "CLAUDE_API_KEY is not set"
    else
        log_pass "CLAUDE_API_KEY is set (${#CLAUDE_API_KEY} chars)"
    fi

    if [ -z "$TAVILY_API_KEY" ]; then
        log_fail "TAVILY_API_KEY is not set"
    else
        log_pass "TAVILY_API_KEY is set (${#TAVILY_API_KEY} chars)"
    fi
else
    log_fail ".env file not found"
fi

echo ""

# ============================================================================
# TEST 5: Script Files
# ============================================================================
log_info "TEST 5: Script Files"
echo ""

test_check "facebook-autoposter.py exists" "[ -f '$SCRIPT_DIR/facebook-autoposter.py' ]"
test_check "facebook-autoposter.py is executable" "[ -x '$SCRIPT_DIR/facebook-autoposter.py' ]"
test_check "fb_news_fetcher.py exists" "[ -f '$SCRIPT_DIR/fb_news_fetcher.py' ]"
test_check "fb_content_generator.py exists" "[ -f '$SCRIPT_DIR/fb_content_generator.py' ]"
test_check "setup-cron.sh is executable" "[ -x '$SCRIPT_DIR/setup-cron.sh' ]"

echo ""

# ============================================================================
# TEST 6: Directories
# ============================================================================
log_info "TEST 6: Required Directories"
echo ""

test_check "logs directory can be created" "mkdir -p '$PROJECT_DIR/logs' && [ -w '$PROJECT_DIR/logs' ]"
test_check "data directory can be created" "mkdir -p '$PROJECT_DIR/data' && [ -w '$PROJECT_DIR/data' ]"

echo ""

# ============================================================================
# TEST 7: Python Syntax Check
# ============================================================================
log_info "TEST 7: Python Syntax Check"
echo ""

test_check "config.py has valid syntax" "python3 -m py_compile '$SCRIPT_DIR/config.py'"
test_check "fb_news_fetcher.py has valid syntax" "python3 -m py_compile '$SCRIPT_DIR/fb_news_fetcher.py'"
test_check "fb_content_generator.py has valid syntax" "python3 -m py_compile '$SCRIPT_DIR/fb_content_generator.py'"
test_check "facebook-autoposter.py has valid syntax" "python3 -m py_compile '$SCRIPT_DIR/facebook-autoposter.py'"

echo ""

# ============================================================================
# TEST 8: Network Connectivity (Optional)
# ============================================================================
log_info "TEST 8: Network Connectivity (Optional)"
echo ""

if command -v curl &> /dev/null; then
    # Test basic connectivity
    if curl -s --max-time 5 https://www.google.com > /dev/null 2>&1; then
        log_pass "Internet connectivity working"
    else
        log_warn "Could not reach google.com - check your internet connection"
    fi
fi

echo ""

# ============================================================================
# SUMMARY
# ============================================================================
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                    TEST RESULTS SUMMARY                     ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Total Tests:    $TOTAL_TESTS"
echo -e "Passed:         ${GREEN}$PASSED_TESTS${NC}"
echo -e "Failed:         ${RED}$FAILED_TESTS${NC}"
echo ""

if [ "$FAILED_TESTS" -eq 0 ]; then
    echo -e "${GREEN}✓ ALL TESTS PASSED!${NC}"
    echo ""
    echo "Your setup is ready. You can now:"
    echo "  1. Test the system:  cd $SCRIPT_DIR && python3 facebook-autoposter.py --run-once"
    echo "  2. Set up cron:      cd $SCRIPT_DIR && bash setup-cron.sh"
    echo ""
    exit 0
else
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    echo ""
    echo "Please fix the issues above before proceeding:"
    echo ""
    echo "Common fixes:"
    echo "  1. Missing .env: cp $SCRIPT_DIR/.env.example $SCRIPT_DIR/.env"
    echo "  2. Missing venv: cd $PROJECT_DIR && python3 -m venv venv"
    echo "  3. Missing deps: source $PROJECT_DIR/venv/bin/activate && pip install -r $SCRIPT_DIR/requirements.txt"
    echo ""
    exit 1
fi
