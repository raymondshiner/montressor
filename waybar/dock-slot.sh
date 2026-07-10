#!/usr/bin/env bash
# Waybar docked-Jarvis-session slot. $1 = slot number (1-based line in registry).
# Renders the docked session's label; empty (hidden via hide-empty-text) when the
# slot is unused. Left-click resumes, right-click undocks (wired in waybar config).
N="${1:?slot number required}"
REG="$HOME/.cache/jarvis/docked-sessions.tsv"

[[ -f "$REG" ]] || { printf '{"text":""}\n'; exit 0; }

line=$(sed -n "${N}p" "$REG")
[[ -z "$line" ]] && { printf '{"text":""}\n'; exit 0; }

uuid=$(cut -f1 <<<"$line")
label=$(cut -f2 <<<"$line")
cwd=$(cut -f3 <<<"$line")

tooltip="$label"$'\n'"click: resume  •  right-click: undock"$'\n'"${uuid:0:8}  •  $cwd"

jq -cn --arg t "󰊤 $label" --arg tt "$tooltip" '{text:$t, tooltip:$tt}'
