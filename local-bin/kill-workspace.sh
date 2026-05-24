#!/bin/bash
# Close every window on the current workspace.
# Hyprland auto-removes empty non-persistent workspaces, so the workspace dissolves on its own.

ws=$(hyprctl -j activeworkspace | jq .id)
hyprctl -j clients | jq -r --argjson ws "$ws" '.[] | select(.workspace.id == $ws) | .address' \
    | while read -r addr; do
        hyprctl dispatch closewindow "address:$addr" >/dev/null
    done

hyprctl dispatch workspace e-1
