#!/bin/bash
# Скриншот HTML-схемы в PNG через headless Chrome, чтобы посмотреть результат глазами.
# Использование: shot.sh page.html out.png [ширина] [высота] [light|dark]
set -e
IN="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"; OUT="$2"; W="${3:-1800}"; H="${4:-1400}"; THEME="${5:-dark}"
for c in "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
         "/Applications/Chromium.app/Contents/MacOS/Chromium" google-chrome chromium chromium-browser; do
  if command -v "$c" >/dev/null 2>&1 || [ -x "$c" ]; then CHROME="$c"; break; fi
done
[ -n "$CHROME" ] || { echo "Chrome не найден"; exit 1; }
"$CHROME" --headless=new --disable-gpu --hide-scrollbars --force-prefers-reduced-motion \
  --blink-settings=preferredColorScheme=$([ "$THEME" = light ] && echo 1 || echo 0) \
  --window-size="$W,$H" --screenshot="$OUT" "file://$IN" >/dev/null 2>&1
echo "$OUT"
