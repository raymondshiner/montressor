#!/usr/bin/env bash
# Waybar custom button for a named (launch/project) workspace.
# Hyprland gives named workspaces negative ids, so the numeric ws1..ws10
# buttons never match them. $1 = 1-based index into the sorted list of named
# workspaces on this monitor.
IDX="$1"

# Named = name is not purely numeric and not a special workspace.
named=$(hyprctl -j workspaces | jq -c \
    --arg mon "${WAYBAR_OUTPUT_NAME:-}" '
    [ .[]
      | select((.name | test("^[0-9]+$")) | not)
      | select(.name | startswith("special") | not)
      | select($mon == "" or .monitor == $mon)
    ] | sort_by(.id) | reverse')

row=$(jq -c --argjson i "$IDX" '.[$i-1] // empty' <<<"$named")
if [[ -z $row ]]; then
    printf '{"text":""}\n'
    exit 0
fi

name=$(jq -r .name <<<"$row")
mon=$(jq -r .monitor <<<"$row")
active_id=$(hyprctl -j monitors | jq --arg m "$mon" '.[] | select(.name == $m) | .activeWorkspace.id')
ws_id=$(jq -r .id <<<"$row")
cls=""
[[ $active_id == "$ws_id" ]] && cls="active"
jq -cn --arg t "$name" --arg c "$cls" '{text: $t, class: $c}'
