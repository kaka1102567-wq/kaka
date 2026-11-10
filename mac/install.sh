#!/usr/bin/env bash
# Install the health coach as a daily launchd job on macOS.
# Secrets go into the macOS Keychain (never into files or git).
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="com.kaka.healthcoach"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
SERVICE="health-coach"
HOUR="${COACH_HOUR:-5}"
MINUTE="${COACH_MINUTE:-47}"

command -v python3 >/dev/null || { echo "❌ Cần python3. Chạy: xcode-select --install"; exit 1; }
python3 -c 'import sys; assert sys.version_info >= (3, 9)' || { echo "❌ Cần Python 3.9+"; exit 1; }

save_secret() {  # $1 = name, $2 = prompt, $3 = hidden(1/0)
  if security find-generic-password -s "$SERVICE" -a "$1" >/dev/null 2>&1; then
    read -r -p "• $1 đã có trong Keychain. Nhập lại? [y/N] " ans
    [[ "$ans" =~ ^[Yy]$ ]] || return 0
  fi
  if [[ "$3" == 1 ]]; then read -r -s -p "$2: " val; echo; else read -r -p "$2: " val; fi
  [[ -n "$val" ]] || { echo "❌ Không được để trống"; exit 1; }
  security add-generic-password -U -s "$SERVICE" -a "$1" -w "$val"
  echo "  ✅ Đã lưu $1 vào Keychain"
}

echo "== Lưu thông tin vào macOS Keychain =="
save_secret INTERVALS_ATHLETE_ID "Intervals Athlete ID (vd i123456)" 0
save_secret INTERVALS_API_KEY    "Intervals API key (ẩn khi gõ)" 1
save_secret TELEGRAM_BOT_TOKEN   "Telegram bot token (ẩn khi gõ)" 1
save_secret TELEGRAM_CHAT_ID     "Telegram chat ID" 0

chmod +x "$REPO_DIR/mac/run.sh"
mkdir -p "$HOME/Library/LaunchAgents" "$HOME/Library/Logs"

cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array><string>/bin/bash</string><string>$REPO_DIR/mac/run.sh</string></array>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>$HOUR</integer><key>Minute</key><integer>$MINUTE</integer></dict>
  <key>StandardOutPath</key><string>$HOME/Library/Logs/health-coach.log</string>
  <key>StandardErrorPath</key><string>$HOME/Library/Logs/health-coach.log</string>
</dict>
</plist>
PL

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "✅ Đã cài lịch chạy $(printf '%02d:%02d' "$HOUR" "$MINUTE") mỗi ngày (giờ của máy Mac)."

read -r -p "Gửi thử báo cáo lên Telegram ngay bây giờ? [Y/n] " ans
if [[ ! "$ans" =~ ^[Nn]$ ]]; then
  /bin/bash "$REPO_DIR/mac/run.sh" && echo "✅ Đã gửi — kiểm tra Telegram."
fi
echo "Log: ~/Library/Logs/health-coach.log"
