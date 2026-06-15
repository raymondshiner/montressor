#!/bin/bash
# Show the active project name when current workspace is a `launch` session.
# Detected by any window on this workspace titled "Agent-N-<slug>" (same
# heuristic workspace-popup.py uses).

ws_json=$(hyprctl -j activeworkspace 2>/dev/null) || exit 0
ws_id=$(echo "$ws_json" | jq -r '.id')
ws_name=$(echo "$ws_json" | jq -r '.name')

has_agent=$(hyprctl -j clients 2>/dev/null | jq --argjson id "$ws_id" \
    '[.[] | select(.workspace.id == $id) | select(.title | test("^Agent-[0-9]+-"))] | length')

if [[ "${has_agent:-0}" -gt 0 ]]; then
    printf '{"text":" %s","class":"project","tooltip":"Active project: %s"}\n' "$ws_name" "$ws_name"
else
    printf '{"text":"","class":"none","tooltip":""}\n'
fi
