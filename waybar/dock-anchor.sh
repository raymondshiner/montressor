#!/usr/bin/env bash
# Waybar anchor for the docked-session rail: a pin icon + count of docked
# sessions. Hidden when nothing is docked (hide-empty-text).
REG="$HOME/.cache/jarvis/docked-sessions.tsv"
count=0
[[ -f "$REG" ]] && count=$(grep -c . "$REG")

if [[ "$count" -eq 0 ]]; then
    printf '{"text":""}\n'
    exit 0
fi

jq -cn --arg t "󰐃 $count" \
   --arg tt "$count docked Jarvis session(s) — click a pill to resume" \
   '{text:$t, tooltip:$tt}'
