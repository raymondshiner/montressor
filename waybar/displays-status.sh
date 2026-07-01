#!/usr/bin/env bash
# Count connected external (non-internal) displays for waybar.
count=$(hyprctl monitors -j | jq '[.[] | select(.name | test("^eDP") | not)] | length')

if [ "$count" -gt 0 ]; then
    printf '{"text":"󰍹 %s","tooltip":"%s external display(s) connected — click to configure","class":"active"}\n' "$count" "$count"
else
    printf '{"text":"","tooltip":""}\n'
fi
