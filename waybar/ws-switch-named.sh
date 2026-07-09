#!/usr/bin/env bash
# Switch to the Nth named (launch/project) workspace on this monitor.
# $1 = 1-based index, matching ws-button-named.sh ordering.
IDX="$1"

name=$(hyprctl -j workspaces | jq -r \
    --arg mon "${WAYBAR_OUTPUT_NAME:-}" --argjson i "$IDX" '
    [ .[]
      | select(.id < 0)
      | select(.name | startswith("special") | not)
      | select($mon == "" or .monitor == $mon)
    ] | sort_by(.id) | reverse | .[$i-1].name // empty')

[[ -n $name ]] && hyprctl dispatch workspace "name:$name"
