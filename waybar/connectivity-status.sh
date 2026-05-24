#!/bin/bash

# WiFi signal via nmcli
WIFI_ROW=$(nmcli -t -f active,signal,ssid dev wifi 2>/dev/null | grep '^yes:' | head -1)

if [ -n "$WIFI_ROW" ]; then
    signal=$(echo "$WIFI_ROW" | cut -d: -f2)
    ssid=$(echo "$WIFI_ROW"   | cut -d: -f3-)
    wifi_label="${ssid} (${signal}%)"
    wifi_up=true
else
    signal=0
    wifi_label="Disconnected"
    wifi_up=false
fi

# VPN state
vpn_state=$(mullvad status --json 2>/dev/null | jq -r '.state' 2>/dev/null)
vpn_up=false
[ "$vpn_state" = "connected" ] && vpn_up=true

vpn_label="VPN: $([ "$vpn_up" = true ] && echo "Connected" || echo "Off")"

icon="$([ "$wifi_up" = true ] && echo "󰤨" || echo "󰤭")"

if [ "$wifi_up" = true ] && [ "$vpn_up" = true ]; then
    class="good"
else
    class="off"
fi

printf '{"text":"%s","class":"%s","tooltip":"%s  ·  %s"}\n' \
    "$icon" "$class" "$wifi_label" "$vpn_label"
