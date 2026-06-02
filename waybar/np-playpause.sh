#!/usr/bin/env bash
# Streaming waybar module: play/pause icon for spotify.

emit() {
    local status
    status=$(playerctl -p spotify status 2>/dev/null)
    case "$status" in
        Playing) echo '{"text": "󰏤", "tooltip": "Pause", "class": "playing"}' ;;
        Paused)  echo '{"text": "󰐊", "tooltip": "Play",  "class": "paused"}' ;;
        *)       echo '{"text": "", "tooltip": "", "class": "hidden"}' ;;
    esac
}

emit

playerctl -p spotify --follow status 2>/dev/null | while IFS= read -r _; do
    emit
done
