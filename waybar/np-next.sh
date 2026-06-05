#!/usr/bin/env bash
# Streaming waybar module: next-track button, hidden when spotify not running.

emit() {
    if [ -n "$(playerctl -p spotify status 2>/dev/null)" ]; then
        echo '{"text": "󰒭", "tooltip": "Next", "class": "visible"}'
    else
        echo '{"text": "󰒭", "tooltip": "Spotify not running", "class": "offline"}'
    fi
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
