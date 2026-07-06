#!/usr/bin/env bash
# Watches Hyprland socket2 and signals waybar (RTMIN+8) so the custom
# workspace buttons re-exec on any workspace change.
sock="$XDG_RUNTIME_DIR/hypr/$HYPRLAND_INSTANCE_SIGNATURE/.socket2.sock"
socat -u UNIX-CONNECT:"$sock" - | while read -r line; do
    case $line in
        workspace*|createworkspace*|destroyworkspace*|moveworkspace*|renameworkspace*|focusedmon*)
            pkill -RTMIN+8 waybar ;;
    esac
done
