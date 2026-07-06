#!/usr/bin/env bash
# Right-click on a workspace button: switch to it, then open the workspace popup.
hyprctl dispatch workspace "$1" >/dev/null
exec "$HOME/.config/waybar/workspace-popup.py"
