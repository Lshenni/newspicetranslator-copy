#!/bin/bash
# ngspice Upgrade Script for Level-72 Support
#
# This script helps identify whether ngspice supports BSIM level 72,
# and provides guided upgrade instructions.
#
# Usage: ./tools/upgrade_ngspice.sh [check|build|help]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
NGSPICE_MIN_VERSION=44  # First version with BSIM6/level-72 support
INSTALL_PREFIX="${HOME}/.local"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'  # No Color

# ============================================================================
# Utility Functions
# ============================================================================

print_header() {
    echo -e "${GREEN}=== $1 ===${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

get_ngspice_version() {
    local ng_path="$1"
    if ! command -v "$ng_path" &> /dev/null; then
        echo "0"
        return
    fi
    
    local ver_output
    ver_output=$("$ng_path" -v 2>&1 | head -1)
    
    # Extract version number: "ngspice-42" -> "42"
    local version=$(echo "$ver_output" | grep -oE '[0-9]+' | head -1)
    echo "${version:-0}"
}

# ============================================================================
# Check Current ngspice
# ============================================================================

check_ngspice() {
    print_header "Checking Current ngspice Installation"
    
    # Find ngspice
    local ng_path
    ng_path=$(command -v ngspice || echo "not found")
    
    if [[ "$ng_path" == "not found" ]]; then
        print_error "ngspice not found in PATH"
        echo "    Next steps: Run 'tools/upgrade_ngspice.sh build' to compile from source"
        return 1
    fi
    
    print_success "Found: $ng_path"
    
    local version
    version=$(get_ngspice_version "$ng_path")
    
    echo "    Version: ngspice-$version"
    
    # Check level-72 support
    if [[ $version -ge $NGSPICE_MIN_VERSION ]]; then
        print_success "ngspice-$version supports BSIM level 72"
        
        # Run verification test
        print_info "Running level-72 verification test..."
        test_level_72_support "$ng_path" && return 0 || return 1
    else
        print_error "ngspice-$version does NOT support BSIM level 72 (need $NGSPICE_MIN_VERSION+)"
        echo "    Next steps: Run 'tools/upgrade_ngspice.sh build' to upgrade"
        return 1
    fi
}

test_level_72_support() {
    local ng_path="$1"
    local test_dir
    test_dir=$(mktemp -d)
    
    # Create minimal level-72 test netlist
    cat > "$test_dir/test_level72.cir" << 'EOF'
Test BSIM6 Level 72
.model nch_test nmos (level=72 vth0=0.4 tox=2.5e-9)
M1 d g 0 0 nch_test W=1u L=20n
.op
.end
EOF
    
    local output
    output=$("$ng_path" -b "$test_dir/test_level72.cir" 2>&1 || true)
    
    rm -rf "$test_dir"
    
    if echo "$output" | grep -qi "Only MOS device levels"; then
        print_error "Level 72 support NOT confirmed (error in test)"
        return 1
    else
        print_success "Level 72 test passed"
        return 0
    fi
}

# ============================================================================
# Build from Source
# ============================================================================

build_ngspice_from_source() {
    print_header "Building ngspice from Source"
    
    local build_dir
    build_dir=$(mktemp -d)
    
    print_info "Build directory: $build_dir"
    print_info "Install prefix: $INSTALL_PREFIX"
    
    cd "$build_dir"
    
    # Check prerequisites
    print_info "Checking prerequisites..."
    local missing_deps=()
    for cmd in git autoconf automake libtool gcc make; do
        if ! command -v "$cmd" &> /dev/null; then
            missing_deps+=("$cmd")
        fi
    done
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        print_error "Missing required tools: ${missing_deps[*]}"
        echo ""
        echo "On Ubuntu/Debian, install with:"
        echo "    sudo apt-get install -y build-essential git autoconf automake libtool"
        echo ""
        echo "On macOS, install with:"
        echo "    brew install autoconf automake libtool"
        return 1
    fi
    
    print_success "All prerequisites found"
    
    # Clone and checkout
    print_info "Cloning ngspice repository..."
    git clone https://git.code.sf.net/p/ngspice/ngspice ngspice-src
    cd ngspice-src
    
    print_info "Checking out ngspice-46 (with BSIM6 level-72 support)..."
    git checkout ngspice-46
    
    # Configure
    print_info "Configuring ngspice..."
    ./autogen.sh
    ./configure \
        --prefix="$INSTALL_PREFIX" \
        --enable-xspice \
        --with-readline=yes \
        --enable-cider \
        2>&1 | tail -20
    
    # Build
    print_info "Building (this may take a few minutes)..."
    make -j"$(nproc)" 2>&1 | tail -10
    
    print_info "Installing to $INSTALL_PREFIX..."
    make install
    
    # Verify
    local ng_new="$INSTALL_PREFIX/bin/ngspice"
    if [[ -f "$ng_new" ]]; then
        print_success "Installation successful: $ng_new"
        
        local new_version
        new_version=$(get_ngspice_version "$ng_new")
        echo "    Version: ngspice-$new_version"
        
        # Test level-72 support
        if test_level_72_support "$ng_new"; then
            print_success "Level-72 support confirmed"
        else
            print_error "Level-72 support test failed"
            return 1
        fi
        
        # Update PATH hint
        echo ""
        print_info "Add this to your ~/.bashrc to use the new ngspice:"
        echo "    export PATH=\"$INSTALL_PREFIX/bin:\$PATH\""
        echo ""
        print_info "Then run:"
        echo "    source ~/.bashrc"
        echo ""
    else
        print_error "Installation failed"
        return 1
    fi
    
    # Cleanup
    cd /
    rm -rf "$build_dir"
}

# ============================================================================
# Update Project Integration
# ============================================================================

update_project() {
    print_header "Updating Project for New ngspice"
    
    # Check if custom ngspice is in PATH
    local ng_path
    ng_path=$(command -v ngspice || echo "not found")
    
    if [[ "$ng_path" == "not found" ]]; then
        print_error "ngspice still not found in PATH"
        return 1
    fi
    
    local version
    version=$(get_ngspice_version "$ng_path")
    
    if [[ $version -lt $NGSPICE_MIN_VERSION ]]; then
        print_error "Found version $version (need $NGSPICE_MIN_VERSION+)"
        return 1
    fi
    
    print_success "Found ngspice-$version at $ng_path"
    
    # Run a test plot generation
    print_info "Running test plot generation for ASAP7..."
    cd "$PROJECT_ROOT"
    
    if [[ -f "generate_verification_plots.py" ]]; then
        # Activate venv if it exists
        if [[ -f ".venv/bin/activate" ]]; then
            # shellcheck disable=SC1091
            source .venv/bin/activate
        fi
        
        python generate_verification_plots.py output/asap7_hspice-ngspice --max-devices 1 2>&1 | head -50
    fi
}

# ============================================================================
# Help
# ============================================================================

print_help() {
    cat << 'EOF'
ngspice Upgrade Tool for BSIM Level-72 Support

USAGE:
    tools/upgrade_ngspice.sh [COMMAND]

COMMANDS:
    check       Verify current ngspice version and level-72 support
    build       Build and install ngspice 46+ from source
    update      Update project and run validation
    help        Show this help message

EXAMPLES:
    # Check if ngspice supports level 72
    tools/upgrade_ngspice.sh check

    # Build ngspice from source (first-time setup)
    tools/upgrade_ngspice.sh build

    # After building, update project and test
    tools/upgrade_ngspice.sh update

ABOUT:
    BSIM level 72 (used by ASAP7, FreePDK15, FreePDK3) requires ngspice 44+.
    ngspice 42 (default on many systems) does NOT support level 72.

    For detailed information, see: docs/NGSPICE_UPGRADE_GUIDE.md

EOF
}

# ============================================================================
# Main
# ============================================================================

main() {
    local cmd="${1:-check}"
    
    case "$cmd" in
        check)
            check_ngspice
            ;;
        build)
            build_ngspice_from_source
            ;;
        update)
            update_project
            ;;
        help | -h | --help)
            print_help
            ;;
        *)
            print_error "Unknown command: $cmd"
            echo "Run 'tools/upgrade_ngspice.sh help' for usage"
            exit 1
            ;;
    esac
}

main "$@"
