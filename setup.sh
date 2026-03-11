#!/bin/bash
# ============================================================================
# AI Thực Chiến — One-Time Setup Script
# ============================================================================
# Run: bash setup.sh
# ============================================================================

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"

echo "============================================"
echo "  AI Thực Chiến — Setup"
echo "============================================"
echo ""

# 1. Check prerequisites
echo "[1/6] Checking prerequisites..."

check_cmd() {
    if ! command -v "$1" &>/dev/null; then
        echo "  ❌ $1 not found. Install it first."
        return 1
    fi
    echo "  ✅ $1 found"
}

check_cmd python3 || exit 1
check_cmd ffmpeg || { echo "  Install with: brew install ffmpeg"; exit 1; }
check_cmd ffprobe || { echo "  Install with: brew install ffmpeg"; exit 1; }

# 2. Create virtual environment
echo ""
echo "[2/6] Creating Python virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    echo "  ✅ Created: $VENV_DIR"
else
    echo "  ✅ Already exists: $VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

# 3. Install dependencies
echo ""
echo "[3/6] Installing Python dependencies..."
pip install -q --upgrade pip
pip install -q -r "$PROJECT_DIR/scripts/requirements.txt"
echo "  ✅ Dependencies installed"

# 4. Create .env if not exists
echo ""
echo "[4/6] Checking .env configuration..."
if [ ! -f "$PROJECT_DIR/.env" ]; then
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    echo "  ⚠️  Created .env from template — EDIT IT with your API keys:"
    echo "     $PROJECT_DIR/.env"
    echo ""
    echo "  Required keys:"
    echo "    - ANTHROPIC_API_KEY  (script generation)"
    echo "    - REPLICATE_API_TOKEN (avatar video, ~\$0.05/video)"
    echo "    - TAVILY_API_KEY     (news fetching, optional)"
else
    echo "  ✅ .env already exists"
fi

# 5. Create directories
echo ""
echo "[5/6] Creating project directories..."
mkdir -p "$PROJECT_DIR/assets"
mkdir -p "$PROJECT_DIR/output"
mkdir -p "$PROJECT_DIR/logs"
echo "  ✅ Directories ready"

# 6. Check avatar image
echo ""
echo "[6/6] Checking avatar image..."
AVATAR_PATH="$PROJECT_DIR/assets/avatar.png"
if [ ! -f "$AVATAR_PATH" ]; then
    echo "  ⚠️  Avatar image not found!"
    echo ""
    echo "  IMPORTANT: Place your face photo at:"
    echo "    $AVATAR_PATH"
    echo ""
    echo "  Requirements:"
    echo "    - Clear front-facing photo (shoulders up)"
    echo "    - 512x512 pixels or larger"
    echo "    - Good, even lighting"
    echo "    - Neutral expression, mouth closed"
    echo "    - PNG or JPG format"
    echo ""
    echo "  Tip: Use a well-lit selfie, crop to square, save as avatar.png"
else
    echo "  ✅ Avatar image found: $AVATAR_PATH"
fi

# Summary
echo ""
echo "============================================"
echo "  Setup Complete!"
echo "============================================"
echo ""
echo "  Next steps:"
echo "  1. Edit .env with your API keys"
echo "  2. Place avatar photo at: assets/avatar.png"
echo "  3. Test TTS:  python3 scripts/tts_generator.py --text 'Xin chào' -o test.mp3"
echo "  4. Dry run:   python3 scripts/daily_pipeline.py --dry-run"
echo "  5. Full run:  python3 scripts/daily_pipeline.py"
echo ""
echo "  Activate venv: source .venv/bin/activate"
echo ""
