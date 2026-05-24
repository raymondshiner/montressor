#!/bin/bash
JSON=$(mullvad status --json 2>/dev/null)
STATE=$(echo "$JSON" | jq -r '.state' 2>/dev/null)

case "$STATE" in
    connected)
        CITY=$(echo "$JSON" | jq -r '.details.location.city // ""')
        COUNTRY=$(echo "$JSON" | jq -r '.details.location.country // ""')
        HOST=$(echo "$JSON" | jq -r '.details.location.hostname // ""')
        IP=$(echo "$JSON" | jq -r '.details.location.ipv4 // ""')
        printf '{"text":"󰒘 VPN","tooltip":"%s, %s\\n%s\\n%s","class":"connected"}\n' \
            "$COUNTRY" "$CITY" "$HOST" "$IP"
        ;;
    connecting)
        printf '{"text":"󰒘 ...","tooltip":"Connecting…","class":"connecting"}\n'
        ;;
    *)
        printf '{"text":"󰒙 VPN","tooltip":"Disconnected","class":"disconnected"}\n'
        ;;
esac
