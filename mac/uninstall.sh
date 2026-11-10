#!/usr/bin/env bash
# Remove the launchd job and (optionally) the Keychain entries.
set -uo pipefail
LABEL="com.kaka.healthcoach"
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null
rm -f "$HOME/Library/LaunchAgents/$LABEL.plist"
echo "✅ Đã gỡ lịch chạy."
read -r -p "Xoá luôn khoá trong Keychain? [y/N] " ans
if [[ "$ans" =~ ^[Yy]$ ]]; then
  for k in INTERVALS_ATHLETE_ID INTERVALS_API_KEY TELEGRAM_BOT_TOKEN TELEGRAM_CHAT_ID; do
    security delete-generic-password -s health-coach -a "$k" >/dev/null 2>&1 && echo "  đã xoá $k"
  done
fi
