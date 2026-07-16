#!/usr/bin/env bash
# Waybar module: Todoist gem left of the center clock (mirrors the Obsidian gem on the right).
# Cyan when the Todoist overlay is shown, purple when hidden. Click toggles special:todoist.
# Streaming module — reacts to Hyprland special-workspace events, no polling interval.

ICON="󰝕"   # nf-md-format_list_checks

emit() {
    if hyprctl -j monitors 2>/dev/null | jq -e '.[] | select(.specialWorkspace.name == "special:todoist")' >/dev/null; then
        echo "{\"text\": \"$ICON\", \"class\": \"visible\", \"tooltip\": \"Hide Todoist overlay\"}"
    else
        echo "{\"text\": \"$ICON\", \"class\": \"closed\", \"tooltip\": \"Todoist overlay (Super+T)\"}"
    fi
}

emit

SOCK="${XDG_RUNTIME_DIR}/hypr/${HYPRLAND_INSTANCE_SIGNATURE}/.socket2.sock"
socat -U - "UNIX-CONNECT:${SOCK}" 2>/dev/null \
  | grep --line-buffered -E '^(activespecial|openwindow|closewindow|movewindow|movewindowv2)' \
  | while IFS= read -r _; do
        emit
    done
