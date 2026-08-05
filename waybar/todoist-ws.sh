#!/usr/bin/env bash
# Waybar module: Todoist gem left of the center clock (mirrors the Obsidian gem on the right).
# Brighter when a Todoist window is visible on a normal workspace, dim when parked/hidden.
# Click = minimize/restore into the current workspace (todoist-raise).
# Streaming module — reacts to Hyprland window events, no polling interval.

ICON=""   # nf-fa-check_circle

emit() {
    if hyprctl clients -j 2>/dev/null | jq -e '.[] | select((.class|ascii_downcase)=="todoist" and ((.workspace.name|startswith("special"))|not))' >/dev/null; then
        echo "{\"text\": \"$ICON\", \"class\": \"visible\", \"tooltip\": \"Hide Todoist\"}"
    else
        echo "{\"text\": \"$ICON\", \"class\": \"closed\", \"tooltip\": \"Todoist (Super+T)\"}"
    fi
}

emit

SOCK="${XDG_RUNTIME_DIR}/hypr/${HYPRLAND_INSTANCE_SIGNATURE}/.socket2.sock"
socat -U - "UNIX-CONNECT:${SOCK}" 2>/dev/null \
  | grep --line-buffered -E '^(activespecial|openwindow|closewindow|movewindow|movewindowv2)' \
  | while IFS= read -r _; do
        emit
    done
