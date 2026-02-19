#!/bin/bash
# Build, sign, and notarize the macOS .app bundle.
#
# Prerequisites:
#   - Apple Developer certificate installed in Keychain
#   - Set DEVELOPER_ID to your signing identity
#   - Set APPLE_ID and APPLE_TEAM_ID for notarization
#
# Usage:
#   ./build.sh                  # Build only
#   ./build.sh --sign           # Build + sign
#   ./build.sh --sign --notarize  # Build + sign + notarize

set -euo pipefail

APP_NAME="Research Taxonomy Library"
DIST_DIR="dist"
APP_PATH="$DIST_DIR/$APP_NAME.app"

# Configurable via environment
DEVELOPER_ID="${DEVELOPER_ID:-}"
APPLE_ID="${APPLE_ID:-}"
APPLE_TEAM_ID="${APPLE_TEAM_ID:-}"
KEYCHAIN_PROFILE="${KEYCHAIN_PROFILE:-notarize-profile}"

SIGN=false
NOTARIZE=false

for arg in "$@"; do
    case "$arg" in
        --sign) SIGN=true ;;
        --notarize) NOTARIZE=true ;;
    esac
done

echo "=== Building $APP_NAME ==="

# Clean previous build
rm -rf build "$DIST_DIR"

# Run py2app
python setup.py py2app 2>&1

if [ ! -d "$APP_PATH" ]; then
    echo "ERROR: Build failed — $APP_PATH not found"
    exit 1
fi

echo "Build complete: $APP_PATH"
du -sh "$APP_PATH"

# --- Code Signing ---
if [ "$SIGN" = true ]; then
    if [ -z "$DEVELOPER_ID" ]; then
        echo "WARNING: DEVELOPER_ID not set. Skipping code signing."
        echo "  Set it with: export DEVELOPER_ID='Developer ID Application: Your Name (TEAMID)'"
    else
        echo ""
        echo "=== Signing ==="
        codesign --deep --force --options runtime \
            --sign "$DEVELOPER_ID" \
            --entitlements /dev/null \
            "$APP_PATH"
        echo "Signed: $APP_PATH"
        codesign --verify --deep --strict "$APP_PATH"
        echo "Signature verified."
    fi
fi

# --- Notarization ---
if [ "$NOTARIZE" = true ] && [ "$SIGN" = true ]; then
    if [ -z "$APPLE_ID" ] || [ -z "$APPLE_TEAM_ID" ]; then
        echo "WARNING: APPLE_ID or APPLE_TEAM_ID not set. Skipping notarization."
        echo "  Set: export APPLE_ID='you@example.com' APPLE_TEAM_ID='XXXXXXXXXX'"
    else
        echo ""
        echo "=== Notarizing ==="
        ZIP_PATH="$DIST_DIR/$APP_NAME.zip"
        ditto -c -k --keepParent "$APP_PATH" "$ZIP_PATH"

        xcrun notarytool submit "$ZIP_PATH" \
            --keychain-profile "$KEYCHAIN_PROFILE" \
            --wait

        echo "Stapling notarization ticket..."
        xcrun stapler staple "$APP_PATH"
        echo "Notarization complete."

        rm -f "$ZIP_PATH"
    fi
fi

echo ""
echo "=== Done ==="
echo "App: $APP_PATH"
echo ""
echo "To run: open '$APP_PATH'"
echo "To create DMG: hdiutil create -volname '$APP_NAME' -srcfolder '$APP_PATH' -ov -format UDZO '$DIST_DIR/$APP_NAME.dmg'"
