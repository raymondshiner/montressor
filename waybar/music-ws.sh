#!/usr/bin/env bash
# Streaming waybar module: hidden when special:music doesn't exist,
# cyan (visible class) when overlay is shown on a monitor, purple (hidden) otherwise.
# Listens to Hyprland socket2 for instant updates.

emit() {
    local ws class
    ws=$(hyprctl -j workspaces | jq -r '.[] | select(.name == "special:music") | .name')
    if [ -z "$ws" ]; then
        echo '{"text": "", "tooltip": ""}'
        return
    fi
    if hyprctl -j monitors | jq -e '.[] | select(.specialWorkspace.name == "special:music")' >/dev/null; then
        class="visible"
    else
        class="hidden"
    fi
    echo "{\"text\": \"♪\", \"class\": \"$class\", \"tooltip\": \"Music workspace\"}"
}

emit

SOCK="${XDG_RUNTIME_DIR}/hypr/${HYPRLAND_INSTANCE_SIGNATURE}/.socket2.sock"

socat -U - "UNIX-CONNECT:${SOCK}" 2>/dev/null | while IFS= read -r line; do
    case "$line" in
        activespecial*|openwindow*|closewindow*|movewindow*|movewindowv2*|createworkspace*|destroyworkspace*|workspace*)
            emit
            ;;
    esac
done
