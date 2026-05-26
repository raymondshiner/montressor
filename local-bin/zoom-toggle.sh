#!/usr/bin/env bash
# Toggle ~1.7x monitor scaling across every connected display.
# Scale 1.6 chosen because it produces integer logical dimensions on
# both 1920x1080 and 3440x1440 -- no "scale unknown" warning.
# auto positioning lets Hyprland recompute offsets -- no "monitor layout is bad".
FLAG=/tmp/zoom-mode.on
SCALE=1.6

if [[ -f "$FLAG" ]]; then
    hyprctl reload >/dev/null
    rm -f "$FLAG"
    notify-send -t 1500 -h string:x-canonical-private-synchronous:zoom "Zoom off" "scale 1.0"
else
    while read -r mon; do
        hyprctl keyword monitor "${mon},preferred,auto,${SCALE}" >/dev/null
    done < <(hyprctl monitors -j | jq -r '.[].name')
    touch "$FLAG"
    notify-send -t 1500 -h string:x-canonical-private-synchronous:zoom "Zoom on" "scale ${SCALE}"
fi
