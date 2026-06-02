#!/usr/bin/env bash
# Streaming waybar module: next-track button, hidden when spotify not running.

emit() {
    if [ -n "$(playerctl -p spotify status 2>/dev/null)" ]; then
        echo '{"text": "󰒭", "tooltip": "Next", "class": "visible"}'
    else
        echo '{"text": "", "tooltip": "", "class": "hidden"}'
    fi
}

emit
playerctl -p spotify --follow status 2>/dev/null | while IFS= read -r _; do
    emit
done
