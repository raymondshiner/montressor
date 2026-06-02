#!/usr/bin/env bash
# Streaming waybar module: music note that caps the now-playing pill.
# Hidden when spotify is not running. Cyan when the music overlay is shown,
# purple when the overlay is hidden. Click toggles the special:music workspace.

emit() {
    local class
    if [ -z "$(playerctl -p spotify status 2>/dev/null)" ]; then
        echo '{"text": "", "tooltip": "", "class": "hidden"}'
        return
    fi
    if hyprctl -j monitors 2>/dev/null | jq -e '.[] | select(.specialWorkspace.name == "special:music")' >/dev/null; then
        class="visible"
    else
        class="closed"
    fi
    echo "{\"text\": \"♪\", \"class\": \"$class\", \"tooltip\": \"Toggle music overlay\"}"
}

emit

SOCK="${XDG_RUNTIME_DIR}/hypr/${HYPRLAND_INSTANCE_SIGNATURE}/.socket2.sock"

{
    socat -U - "UNIX-CONNECT:${SOCK}" 2>/dev/null | grep --line-buffered -E '^(activespecial|openwindow|closewindow|movewindow|movewindowv2|createworkspace|destroyworkspace|workspace)' &
    playerctl -p spotify --follow status 2>/dev/null &
    wait
} | while IFS= read -r _; do
    emit
done
