#!/usr/bin/env bash
# Waybar docked-Jarvis-session slot. $1 = slot number (1-based line in registry).
# Renders the docked session's label; cyan ".active" class when its session is
# currently live. Empty output (hidden via hide-empty-text) when the slot is
# unused. Click target: `dock resume <uuid>`.
N="${1:?slot number required}"
REG="$HOME/.cache/jarvis/docked-sessions.tsv"

[[ -f "$REG" ]] || { printf '{"text":""}\n'; exit 0; }

line=$(sed -n "${N}p" "$REG")
[[ -z "$line" ]] && { printf '{"text":""}\n'; exit 0; }

uuid=$(cut -f1 <<<"$line")
label=$(cut -f2 <<<"$line")
cwd=$(cut -f3 <<<"$line")

cls="docked"
for pid in $(pgrep -u "$USER" -f 'claude' 2>/dev/null); do
    sid=$(tr '\0' '\n' < "/proc/$pid/environ" 2>/dev/null | sed -n 's/^CLAUDE_CODE_SESSION_ID=//p')
    if [[ "$sid" == "$uuid" ]]; then cls="active"; break; fi
done

state="docked — click to resume"
[[ "$cls" == "active" ]] && state="active now"
tooltip="$label ($state)"$'\n'"${uuid:0:8}  •  $cwd"

jq -cn --arg t "󰊤 $label" --arg c "$cls" --arg tt "$tooltip" \
   '{text:$t, class:$c, tooltip:$tt}'
