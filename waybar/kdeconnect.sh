#!/bin/bash

if ! pgrep -x kdeconnectd > /dev/null 2>&1; then
    printf '{"text":"󰏲","tooltip":"KDE Connect not running","class":"disconnected"}\n'
    exit 0
fi

device_line=$(kdeconnect-cli --list-available 2>/dev/null | grep "^- " | head -1)

if [ -z "$device_line" ]; then
    printf '{"text":"󰏲","tooltip":"Phone not reachable","class":"disconnected"}\n'
    exit 0
fi

device_name=$(echo "$device_line" | sed 's/^- //; s/: .*//')
device_id=$(echo "$device_line" | sed 's/.*: //; s/ (.*)//')

battery_output=$(kdeconnect-cli -d "$device_id" --battery 2>/dev/null)
battery_pct=$(echo "$battery_output" | grep -oP 'Battery:\s*\K\d+')

if [ -n "$battery_pct" ]; then
    charging=$(echo "$battery_output" | grep -i "Charging" | grep -iv "Not")
    if [ -n "$charging" ]; then
        tooltip="${device_name}\nBattery: ${battery_pct}% (charging)"
    else
        tooltip="${device_name}\nBattery: ${battery_pct}%"
    fi
    text="󰄜 ${battery_pct}%"
else
    text="󰄜"
    tooltip="$device_name"
fi

printf '{"text":"%s","tooltip":"%s","class":"connected"}\n' "$text" "$tooltip"
