#!/usr/bin/env bash
# Called by launchd: read secrets from Keychain, build the report, send to Telegram.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE="health-coach"
get() { security find-generic-password -s "$SERVICE" -a "$1" -w; }

export INTERVALS_ATHLETE_ID="$(get INTERVALS_ATHLETE_ID)"
export INTERVALS_API_KEY="$(get INTERVALS_API_KEY)"
export TELEGRAM_BOT_TOKEN="$(get TELEGRAM_BOT_TOKEN)"
export TELEGRAM_CHAT_ID="$(get TELEGRAM_CHAT_ID)"
export COACH_TZ="${COACH_TZ:-Asia/Phnom_Penh}"

echo "=== $(date '+%Y-%m-%d %H:%M:%S') ==="
cd "$REPO_DIR"
# Retry once after 5 min (e.g. Wi-Fi not up yet right after the Mac wakes).
if ! /usr/bin/env python3 -m health_coach.daily --telegram >/dev/null; then
  echo "Lần 1 lỗi, thử lại sau 5 phút..."; sleep 300
  /usr/bin/env python3 -m health_coach.daily --telegram >/dev/null
fi
echo "OK: đã gửi Telegram"
