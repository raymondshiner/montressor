#!/usr/bin/env bash
# Close the focused window. For apps that ignore the wayland close signal
# (Kodi, etc.), send SIGTERM directly to the pid instead.

FORCE_KILL_CLASSES=("Kodi" "kodi")

read -r class pid < <(hyprctl activewindow -j | jq -r '"\(.class) \(.pid)"')

for offender in "${FORCE_KILL_CLASSES[@]}"; do
    if [[ "$class" == "$offender" && "$pid" -gt 0 ]]; then
        kill -TERM "$pid"
        exit 0
    fi
done

hyprctl dispatch killactive
