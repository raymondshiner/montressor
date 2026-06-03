#!/usr/bin/env bash
# Streaming waybar module: spotify track title, hidden when not running.

MAX_LEN=40

emit() {
    local status title artist text class
    status=$(playerctl -p spotify status 2>/dev/null)
    if [ -z "$status" ]; then
        echo '{"text": "", "tooltip": "", "class": "hidden"}'
        return
    fi
    title=$(playerctl -p spotify metadata title 2>/dev/null)
    artist=$(playerctl -p spotify metadata artist 2>/dev/null)
    if [ -z "$title" ]; then
        echo '{"text": "", "tooltip": "", "class": "hidden"}'
        return
    fi
    text="$title — $artist"
    if [ ${#text} -gt $MAX_LEN ]; then
        text="${text:0:$((MAX_LEN-1))}…"
    fi
    text=${text//\"/\\\"}
    case "$status" in
        Playing) class="playing" ;;
        Paused)  class="paused" ;;
        *)       class="stopped" ;;
    esac
    printf '{"text": "%s", "tooltip": "%s — %s", "class": "%s"}\n' \
        "$text" "${title//\"/\\\"}" "${artist//\"/\\\"}" "$class"
}

emit

playerctl -p spotify --follow metadata --format '{{status}}' 2>/dev/null | while IFS= read -r _; do
    emit
done
