#!/usr/bin/env bash
# Waybar right-click handler: undock the session in slot $1.
N="${1:?slot number required}"
REG="$HOME/.cache/jarvis/docked-sessions.tsv"
label=$(sed -n "${N}p" "$REG" 2>/dev/null | cut -f2)
[[ -z "$label" ]] && exit 0
"$HOME/.local/bin/dock" undock "$N" >/dev/null 2>&1
notify-send "Dock" "Undocked \"$label\"" 2>/dev/null || true
