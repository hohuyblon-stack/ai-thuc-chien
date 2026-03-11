#!/bin/bash
# setup_wav2lip.sh
# Complete Wav2Lip setup for macOS Apple Silicon

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WAV2LIP_DIR="$PROJECT_DIR/wav2lip"

echo "=== AI Thực Chiến — Wav2Lip Setup for macOS ==="
echo "Project directory: $PROJECT_DIR"
echo ""

# 1. Install Homebrew dependencies
echo "[1/7] Installing Homebrew dependencies..."
brew install python@3.9 ffmpeg git-lfs

# 2. Create Wav2Lip directory
echo "[2/7] Creating Wav2Lip directory..."
mkdir -p "$WAV2LIP_DIR"
cd "$WAV2LIP_DIR"

# 3. Create virtual environment
echo "[3/7] Creating virtual environment with Python 3.9..."
python3.9 -m venv venv
source venv/bin/activate

# 4. Clone Wav2Lip
echo "[4/7] Cloning Wav2Lip repository..."
if [ ! -d "Wav2Lip" ]; then
  git clone https://github.com/justinjohn0306/Wav2Lip.git
fi
cd Wav2Lip

# 5. Install PyTorch (CPU optimized for macOS)
echo "[5/7] Installing PyTorch 2.1.2..."
pip install --upgrade pip setuptools wheel
pip install torch==2.1.2 torchvision==0.16.2 torchaudio==2.1.2

# 6. Install dependencies
echo "[6/7] Installing Python dependencies..."
pip install -r requirements.txt 2>&1 | grep -v "already satisfied" || true
pip install transformers==4.33.2 numpy==1.24.4

# 7. Download models
echo "[7/7] Downloading pretrained models..."
mkdir -p face_detection/detection/sfd
mkdir -p face_detection/detection/dlib
mkdir -p checkpoints

echo "  → Downloading SFD face detector..."
wget -q "https://www.adrianbulat.com/downloads/dlib/mmod_human_face_detector.dat" \
  -O face_detection/detection/sfd/s3fd.pth 2>/dev/null || \
  curl -L -o face_detection/detection/sfd/s3fd.pth \
  "https://www.adrianbulat.com/downloads/dlib/mmod_human_face_detector.dat"

echo "  → Downloading shape predictor..."
wget -q "https://www.adrianbulat.com/downloads/dlib/shape_predictor_68_face_landmarks.dat" \
  -O face_detection/detection/dlib/shape_predictor_68_face_landmarks.dat 2>/dev/null || \
  curl -L -o face_detection/detection/dlib/shape_predictor_68_face_landmarks.dat \
  "https://www.adrianbulat.com/downloads/dlib/shape_predictor_68_face_landmarks.dat"

echo "  → Downloading Wav2Lip base model..."
wget -q "https://www.dropbox.com/s/fvc9aupvv88nk5w/wav2lip.pth?dl=1" \
  -O checkpoints/wav2lip.pth 2>/dev/null || \
  curl -L -o checkpoints/wav2lip.pth \
  "https://www.dropbox.com/s/fvc9aupvv88nk5w/wav2lip.pth?dl=1"

echo "  → Downloading Wav2Lip GAN model (better quality)..."
wget -q "https://www.dropbox.com/s/h1unxlc0yq0xblh/wav2lip_gan.pth?dl=1" \
  -O checkpoints/wav2lip_gan.pth 2>/dev/null || \
  curl -L -o checkpoints/wav2lip_gan.pth \
  "https://www.dropbox.com/s/h1unxlc0yq0xblh/wav2lip_gan.pth?dl=1"

echo ""
echo "=== Setup Complete! ==="
echo ""
echo "Verification:"
echo "  Python version: $(python --version)"
echo "  FFmpeg version: $(ffmpeg -version | head -1)"
echo "  Virtual env: $WAV2LIP_DIR/venv"
echo ""
echo "Test Wav2Lip:"
echo "  cd $WAV2LIP_DIR/Wav2Lip"
echo "  source ../venv/bin/activate"
echo "  python inference.py --checkpoint_path checkpoints/wav2lip_gan.pth \\"
echo "    --face /path/to/reference.mp4 --audio /path/to/audio.wav --outfile output.mp4"
echo ""
echo "Make sure you have a reference video at: $PROJECT_DIR/data/reference_video.mp4"
