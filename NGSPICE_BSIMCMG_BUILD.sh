#!/bin/bash
# NGSPICE BSIM-CMG Build Script
# This compiles ngspice-42 with BSIM-CMG support for native FinFET model execution

set -e

echo "=========================================="
echo "Building ngspice-42 with BSIM-CMG support"
echo "=========================================="

# Step 1: Create build directory
BUILD_DIR=$(mktemp -d)
echo "Build directory: $BUILD_DIR"
cd "$BUILD_DIR"

# Step 2: Clone ngspice
echo ""
echo "[1/5] Cloning ngspice repository..."
git clone https://git.code.sf.net/p/ngspice/ngspice
cd ngspice

# Step 3: Configure with BSIM-CMG
echo ""
echo "[2/5] Configuring ngspice with BSIM-CMG support..."
./configure \
  --enable-bsimcmg \
  --with-ngshared \
  --prefix=/usr/local

# Step 4: Build
echo ""
echo "[3/5] Compiling ngspice (this may take 5-10 minutes)..."
make -j$(nproc)

# Step 5: Install
echo ""
echo "[4/5] Installing ngspice..."
sudo make install

# Step 6: Verify
echo ""
echo "[5/5] Verifying installation..."
/usr/local/bin/ngspice --version | head -n 5

echo ""
echo "=========================================="
echo "✅ Build complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Update your PATH to use the new ngspice:"
echo "   export PATH=/usr/local/bin:\$PATH"
echo ""
echo "2. Verify it supports BSIM-CMG:"
echo "   ngspice --version"
echo ""
echo "3. Run full verification batch:"
echo "   cd /home/shennilee/newproject2026/proj1/new-spice-translator"
echo "   source .venv/bin/activate"
echo "   python3 batch_verify.py --mc-runs 10 --roundtrip"
echo ""
echo "4. Compare results with previous run (should be identical or improved)"
echo ""
