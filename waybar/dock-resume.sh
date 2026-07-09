#!/usr/bin/env bash
# Waybar click handler: resume the docked session in slot $1.
N="${1:?slot number required}"
REG="$HOME/.cache/jarvis/docked-sessions.tsv"
uuid=$(sed -n "${N}p" "$REG" 2>/dev/null | cut -f1)
[[ -n "$uuid" ]] && exec "$HOME/.local/bin/dock" resume "$uuid"
