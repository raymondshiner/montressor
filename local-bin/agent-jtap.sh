#!/usr/bin/env bash
# Super+J: single tap -> Jarvis, double tap (<300ms) -> Vision.
# Hyprland has no native double-tap, so we debounce via a timestamp file.
# Cost: single-tap Jarvis is delayed ~300ms while we wait to see if a second
# tap is coming. That latency is inherent to overloading one key.
STAMP=/tmp/agent-jtap.stamp
WINDOW_MS=300

now=$(date +%s%3N)
last=$(cat "$STAMP" 2>/dev/null); last=${last:-0}
if (( now - last < WINDOW_MS )); then
  : > "$STAMP"   # consume: signals the pending single-tap to abort
  exec kitty --title "Vision" --config "$HOME/.config/kitty/vision.conf" \
    --directory "$HOME/vision" -e "$HOME/.local/bin/vision"
fi

echo "$now" > "$STAMP"
(
  sleep 0.30
  [[ "$(cat "$STAMP" 2>/dev/null)" == "$now" ]] || exit 0   # second tap fired -> abort
  rm -f "$STAMP"
  kitty --title "Jarvis" --config "$HOME/.config/kitty/jarvis.conf" \
    --directory "$HOME" -e "$HOME/.local/bin/jarvis"
) &
