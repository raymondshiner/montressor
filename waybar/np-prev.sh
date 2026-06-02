#!/usr/bin/env bash
# Streaming waybar module: prev-track button, hidden when spotify not running.

emit() {
    if [ -n "$(playerctl -p spotify status 2>/dev/null)" ]; then
        echo '{"text": "󰒮", "tooltip": "Previous", "class": "visible"}'
    else
        echo '{"text": "", "tooltip": "", "class": "hidden"}'
    fi
}

emit
playerctl -p spotify --follow status 2>/dev/null | while IFS= read -r _; do
    emit
done
