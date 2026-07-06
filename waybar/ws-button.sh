#!/usr/bin/env bash
# Waybar custom workspace button. $1 = workspace id.
N="$1"
row=$(hyprctl -j workspaces | jq -c --argjson n "$N" '.[] | select(.id == $n)')
if [[ -z $row ]]; then
    printf '{"text":""}\n'
    exit 0
fi
mon=$(jq -r .monitor <<<"$row")
# Match hyprland/workspaces all-outputs:false — only show on the bar of its monitor
if [[ -n $WAYBAR_OUTPUT_NAME && $mon != "$WAYBAR_OUTPUT_NAME" ]]; then
    printf '{"text":""}\n'
    exit 0
fi
name=$(jq -r .name <<<"$row")
active_id=$(hyprctl -j monitors | jq --arg m "$mon" '.[] | select(.name == $m) | .activeWorkspace.id')
cls=""
[[ $active_id == "$N" ]] && cls="active"
jq -cn --arg t "$name" --arg c "$cls" '{text: $t, class: $c}'
