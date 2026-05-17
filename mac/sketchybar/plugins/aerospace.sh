#!/usr/bin/env bash
# Highlight the focused AeroSpace workspace.
TARGET="$1"
FOCUSED=$(aerospace list-workspaces --focused 2>/dev/null)

CYAN=0xff00E8C6
MUTED=0xff677691

if [[ "$TARGET" == "$FOCUSED" ]]; then
  sketchybar --set "$NAME" icon.color=$CYAN background.drawing=on background.color=0x2200E8C6
else
  sketchybar --set "$NAME" icon.color=$MUTED background.drawing=off
fi
