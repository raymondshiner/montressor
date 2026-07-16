#!/usr/bin/env bash
# 3-finger swipe down: close whichever special (overlay) workspace is open on
# the focused monitor (todoist, music, obsidian, etc). No-op if none is open.
special=$(hyprctl monitors -j | jq -r '.[] | select(.focused) | .specialWorkspace.name')
[[ -n "$special" ]] && hyprctl dispatch togglespecialworkspace "${special#special:}"
