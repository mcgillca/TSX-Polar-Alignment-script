#!/bin/bash
# TSXS Polar Alignment v2.0 — first-run setup
# Opened in Terminal by the launcher on first launch only.

export PATH="$HOME/.local/bin:$HOME/.cargo/bin:/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:$PATH"

FLAG="$HOME/.tsxpolar_cache/.tsxpolar_ready"
mkdir -p "$HOME/.tsxpolar_cache"

echo ""
echo "============================================"
echo "  TSXS Polar Alignment v2.0 - First Run Setup"
echo "============================================"
echo ""
echo "This window shows progress during first-time setup."
echo "It will not appear on future launches."
echo ""

if ! command -v uv &>/dev/null; then
    echo "Step 1: Installing uv (Python package manager)..."
    echo "        This is a one-time download (~30 seconds)."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    echo ""
fi

if ! command -v uv &>/dev/null; then
    echo "ERROR: uv installation failed."
    echo "Please install from https://docs.astral.sh/uv/ and try again."
    read -r -p "Press Enter to close this window."
    exit 1
fi

echo "Step 2: Downloading Python and packages..."
echo "        (This may take a minute on a slow connection.)"
echo ""

# Navigate to the folder containing the .app bundle
# Script is at: App.app/Contents/Resources/first_run.sh
# App dir is:   ../../../.. = 4 levels up
APP_DIR="$(cd "$(dirname "$0")/../../.." && pwd)"
echo "Step 3: Starting TSXS Polar Alignment..."
echo "        (You can close this window once the app opens.)"
echo ""
cd "$APP_DIR"
uv run "PAUI.py"
touch "$FLAG"
echo ""
echo "Setup complete. You can close this window."
