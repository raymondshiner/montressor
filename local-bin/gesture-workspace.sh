#!/usr/bin/env bash
# 3-finger workspace swipe. If a special (overlay) workspace is open on the
# focused monitor, close it instead of switching the workspace underneath it.
dir="$1"  # next | prev

special=$(hyprctl monitors -j | jq -r '.[] | select(.focused) | .specialWorkspace.name')

if [[ -n "$special" ]]; then
    hyprctl dispatch togglespecialworkspace "${special#special:}"
else
    case "$dir" in
        next) hyprctl dispatch workspace e+1 ;;
        prev) hyprctl dispatch workspace e-1 ;;
    esac
fi
