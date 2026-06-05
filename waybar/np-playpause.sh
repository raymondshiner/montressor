#!/usr/bin/env bash
# Streaming waybar module: play/pause icon for spotify.

emit() {
    local status
    status=$(playerctl -p spotify status 2>/dev/null)
    case "$status" in
        Playing) echo '{"text": "󰏤", "tooltip": "Pause", "class": "playing"}' ;;
        Paused)  echo '{"text": "󰐊", "tooltip": "Play",  "class": "paused"}' ;;
        *)       echo '{"text": "󰐊", "tooltip": "Launch Spotify", "class": "offline"}' ;;
    esac
}

emit

while true; do
    if [ -n "$(playerctl -p spotify status 2>/dev/null)" ]; then
        playerctl -p spotify --follow status 2>/dev/null | while IFS= read -r _; do
            emit
        done
    fi
    sleep 2
    emit
done
