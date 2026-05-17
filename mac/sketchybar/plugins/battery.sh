#!/usr/bin/env bash
# Andromeda battery indicator.
PERCENT=$(pmset -g batt | grep -Eo "[0-9]+%" | head -1 | tr -d %)
CHARGING=$(pmset -g batt | grep -c "AC Power")

[[ -z "$PERCENT" ]] && exit 0

if (( CHARGING )); then
  ICON=""; COLOR=0xff00E8C6
elif (( PERCENT < 20 )); then
  ICON=""; COLOR=0xffEE5D43
elif (( PERCENT < 50 )); then
  ICON=""; COLOR=0xffFFE66D
elif (( PERCENT < 80 )); then
  ICON=""; COLOR=0xffA8FF60
else
  ICON=""; COLOR=0xffA8FF60
fi

sketchybar --set "$NAME" icon="$ICON" icon.color="$COLOR" label="${PERCENT}%"
