#!/usr/bin/env bash
set -euo pipefail

LABEL="net.damienmurphy.rails-server"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_PLIST="$ROOT/launchd/$LABEL.plist"

LAUNCH_AGENTS="$HOME/Library/LaunchAgents"
INSTALLED_PLIST="$LAUNCH_AGENTS/$LABEL.plist"

SERVE_SCRIPT="$ROOT/serve"

mkdir -p "$LAUNCH_AGENTS"

chmod +x "$SERVE_SCRIPT"

# Remove an existing loaded instance if present.
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true

# Generate the machine-specific plist from the repo template.
sed \
    "s|RAILS_SERVE_SCRIPT|$SERVE_SCRIPT|g" \
    "$SOURCE_PLIST" > "$INSTALLED_PLIST"

plutil -lint "$INSTALLED_PLIST"

launchctl bootstrap "gui/$(id -u)" "$INSTALLED_PLIST"

echo
echo "Rails server installed."
echo "Left:  http://localhost:20000/left.html"
echo "Right: http://localhost:20000/right.html"
echo
echo "Status:"
launchctl print "gui/$(id -u)/$LABEL"
