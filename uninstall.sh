#!/bin/bash
# TSXS Polar Alignment v2.0 - macOS uninstaller
# Run from Terminal:  bash uninstall.sh
# Drag the .app bundle to the Trash to remove the app itself.

echo ""
echo "============================================"
echo "  TSXS Polar Alignment - Uninstall"
echo "============================================"
echo ""
echo "To remove the app, drag the .app bundle to the Trash."
echo ""

# Always clear the first-run flag so a future install shows first-run setup
# again, regardless of whether settings/cache below are kept.
rm -f "$HOME/.tsxpolar_cache/.tsxpolar_ready"

read -r -p "Remove settings and cached data? [y/N] " choice
if [[ "$choice" =~ ^[Yy]$ ]]; then
    rm -f "$HOME/.tsxpolar.json"
    rm -rf "$HOME/.tsxpolar_cache"
    echo "Settings removed."
fi

echo ""
echo "WARNING: Do NOT remove uv if you use it for other Python projects."
read -r -p "Remove uv? [y/N] " ruv
if [[ "$ruv" =~ ^[Yy]$ ]]; then
    rm -f "$HOME/.local/bin/uv" "$HOME/.local/bin/uvx"
    rm -rf "$HOME/.local/share/uv"
    echo "uv removed."
fi

echo ""
echo "Done."
