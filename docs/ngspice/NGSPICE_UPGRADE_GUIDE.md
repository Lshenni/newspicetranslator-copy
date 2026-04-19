# ngspice Upgrade Guide for BSIM Level 72 Support

## Overview

The current ngspice binary (version 42) supports MOS device levels: **1–6, 8–10, 14, 49, 54–58, 60, 68, 73**.

**ASAP7**, **FreePDK15**, and **FreePDK3** models use **BSIM level 72** (advanced FinFET), which is **not supported** in ngspice 42.

This guide provides upgrade paths to enable level-72 support for verification plot generation.

---

## Model Level Reference

| Level | Name | Technology | Status in ng42 |
|-------|------|-----------|---|
| 1–3 | BSIM1/2/3 | Bulk CMOS (legacy) | ✅ Supported |
| 4–6 | BSIM4 | Bulk CMOS (modern) | ✅ Supported |
| 49 | BSIM-IMG | Image-charge FinFET | ✅ Supported |
| 54–58 | BSIM-CMG | Common-multi-gate FinFET | ✅ Supported |
| 60 | BSIM-SOI | Silicon-on-insulator | ✅ Supported |
| 68 | PSP | Platform-independent bulk | ✅ Supported |
| 72 | BSIM6 | Advanced FinFET / GAA | ❌ **Not supported** |
| 73 | BSIM-FD | Fully-depleted SOI | ✅ Supported |

---

## Upgrade Option 1: Build ngspice from Source (Recommended)

### Prerequisites

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y \
    build-essential \
    git \
    autoconf \
    automake \
    libtool \
    libxaw7-dev \
    libxmu-dev \
    libx11-dev \
    libxt-dev \
    libreadline-dev \
    libglui-dev \
    libfftw3-dev

# macOS (using Homebrew)
brew install autoconf automake libtool readline fftw3 xorg-server
```

### Build Steps

```bash
# 1. Clone ngspice repository
cd /tmp
git clone https://git.code.sf.net/p/ngspice/ngspice ngspice-src
cd ngspice-src

# 2. (Optional) Checkout recent version with level-72 support
# Level 72 was added in ngspice 44+
# Use latest stable tag (check releases at sourceforge)
git tag | grep -E '^ngspice-[0-9]+$' | tail -5
git checkout ngspice-46  # Use ngspice-46 or later for level-72 support

# 3. Configure with standard options
./autogen.sh
./configure \
    --prefix=$HOME/.local \
    --enable-xspice \
    --with-readline=yes \
    --enable-cider

# 4. Build and install
make -j$(nproc)
make install

# 5. Verify installation
$HOME/.local/bin/ngspice -v | head -5
```

### Verify Level-72 Support

```bash
# Create a test netlist with level 72 model
cat > /tmp/test_level72.cir << 'EOF'
Test BSIM6 Level 72
.include /tmp/dummy_level72.mdl

Vdd d 0 DC 1.2
Vgs g 0 DC 0.6
M1 d g 0 0 nch_level72 W=1u L=20n

.model nch_level72 nmos (level=72 vth0=0.4 tox=2.5e-9)

.op
.end
EOF

# Run with upgraded ngspice
$HOME/.local/bin/ngspice -b /tmp/test_level72.cir -o /tmp/test_level72.out 2>&1

# Check output for "Only MOS device levels" warning
grep -i "Only MOS device levels\|Error" /tmp/test_level72.out || echo "✅ Level 72 supported"
```

---

## Upgrade Option 2: Use Pre-built Binaries

### Linux (Ubuntu/Debian)

```bash
# Add ngspice PPA (if available) with newer version
sudo add-apt-repository ppa:ngspice/ngspice-dev
sudo apt-get update
sudo apt-get install ngspice

# Verify version
ngspice -v | head -1
```

### Linux (Build from Snap)

```bash
# Snap packages may have more recent versions
snap search ngspice
snap install ngspice  # If available with level-72 support
```

### macOS

```bash
# HomeBrew may have recent version
brew install ngspice@latest
# Or compile from source (see Option 1)
```

---

## Upgrade Option 3: Docker Container

Use a pre-configured Docker image with ngspice 46+:

```bash
# Create a simple Dockerfile
cat > /tmp/Dockerfile << 'EOF'
FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    build-essential autoconf automake libtool \
    libreadline-dev libfftw3-dev libxaw7-dev \
    git

RUN cd /tmp && \
    git clone https://git.code.sf.net/p/ngspice/ngspice ngspice-src && \
    cd ngspice-src && \
    git checkout ngspice-46 && \
    ./autogen.sh && \
    ./configure --prefix=/usr/local --enable-xspice && \
    make -j4 && make install

RUN ngspice -v
EOF

# Build and run
docker build -t ngspice:46 /tmp
docker run --rm -it ngspice:46 ngspice -v
```

---

## Integration with Project

Once ngspice with level-72 support is installed, update the Python plot generator:

### Option A: Use Custom ngspice Binary

Edit [generate_verification_plots.py](../generate_verification_plots.py):

```python
# At top of file, after imports:
NGSPICE_PATH = '/path/to/upgraded/ngspice'  # e.g., '/home/user/.local/bin/ngspice'

# In run_ngspice_simulation():
result = subprocess.run(
    [NGSPICE_PATH, '-b', netlist_file],  # Use custom path
    capture_output=True,
    text=True,
    timeout=timeout
)
```

### Option B: Add to PATH

```bash
# If using $HOME/.local/bin from source build:
export PATH=$HOME/.local/bin:$PATH

# Add to ~/.bashrc to persist:
echo 'export PATH=$HOME/.local/bin:$PATH' >> ~/.bashrc
source ~/.bashrc

# Verify ngspice resolution
which ngspice
ngspice -v | head -1
```

---

## Verification After Upgrade

```bash
# 1. Test with ASAP7 model
cd /path/to/project
python generate_verification_plots.py output/asap7_hspice-ngspice --max-devices 3

# Expected output: ✅ Generated N verification plots (instead of 0)

# 2. Test with FreePDK15
python generate_verification_plots.py output/freepdk15_hspice-ngspice --max-devices 3

# 3. Test with FreePDK3
python generate_verification_plots.py output/freepdk3_hspice-ngspice --max-devices 3
```

---

## Troubleshooting

### "Only MOS device levels 1-6..." still appears

- Verify ngspice binary version: `ngspice -v`
- Check it's using upgraded binary: `which ngspice`
- Confirm compilation included level-72 support (check `./configure` output for BSIM6/level-72)

### Build fails on Linux

```bash
# Ensure all dev libraries are installed
sudo apt-get install -y libtermcap-dev

# Try cleaner build
cd ngspice-src
make distclean
./autogen.sh
./configure --prefix=$HOME/.local --enable-xspice --with-readline=yes
make -j$(nproc)
make install
```

### Build fails on macOS

```bash
# Install dependencies via Homebrew
brew install autoconf automake libtool readline fftw3

# Configure with Homebrew paths
./configure \
    --prefix=$HOME/.local \
    LDFLAGS="-L/usr/local/opt/readline/lib" \
    CPPFLAGS="-I/usr/local/opt/readline/include"
```

---

## Model Support Matrix After Upgrade

After completing an upgrade to **ngspice 46+**, the following PDK models should generate plots:

| PDK | Level | Source | Target | Status After Upgrade |
|-----|-------|--------|--------|---|
| FreePDK45 | 54 | HSPICE | ngspice | ✅ Already working |
| ASAP7 | 72 | HSPICE | ngspice | ✅ **Fixed** |
| FreePDK15 | 72 | HSPICE | ngspice | ✅ **Fixed** |
| FreePDK3 | 72 | HSPICE | ngspice | ✅ **Fixed** |
| Sky130 | Mixed | ngspice | HSPICE | ⚠️ Requires parameter bootstrap (separate issue) |

---

## References

- [ngspice SourceForge](https://sourceforge.net/p/ngspice/ngspice/ci/master/tree/)
- [BSIM Models Documentation](https://bsim.berkeley.edu/)
- [ngspice Manual (Level Support)](http://ngspice.sourceforge.net/docs/ngspice-manual.pdf)

---

## Quick Start Checklist

- [ ] Install prerequisites for your OS
- [ ] Clone or download ngspice source (tag: ngspice-46 or later)
- [ ] Run `./autogen.sh && ./configure && make -j4 && make install`
- [ ] Verify: `ngspice -v` shows version 46 or later
- [ ] Update `PATH` or `NGSPICE_PATH` in project
- [ ] Re-run plot generation for ASAP7/FreePDK15/FreePDK3
- [ ] Verify: All three directories now generate plots ✅

