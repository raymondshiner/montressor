#!/bin/bash
# Super+M: Musicboard (left 28%) + Spotify (right 72%) tiled on workspace 9.
# Uses dwindle splitratio: 1.0 = even split. First child (musicboard) gets ratio/2,
# second child (spotify) gets (2-ratio)/2. So ratio=0.5 -> musicboard 25%, spotify 75%.

CHROME_APP_ID="llknpfcjghkmocoiolfnjeeobajolgpl"
LOG=/tmp/music-launch.log
: > "$LOG"
exec >>"$LOG" 2>&1
echo "=== $(date) ==="

mb_running=$(hyprctl clients | grep -c "title: Musicboard")
sp_running=$(hyprctl clients | grep -ci "class: Spotify")

if [ "$mb_running" -eq 0 ] && [ "$sp_running" -eq 0 ]; then
    hyprctl dispatch togglespecialworkspace music

    hyprctl dispatch exec "[workspace special:music silent; tile] spotify"

    SP_ADDR=""
    for _ in $(seq 1 150); do
        SP_ADDR=$(hyprctl -j clients | jq -r '.[] | select(.class=="Spotify") | .address' | head -1)
        [ -n "$SP_ADDR" ] && break
        sleep 0.1
    done
    echo "spotify addr: $SP_ADDR"

    hyprctl dispatch exec "[workspace special:music silent; tile] /opt/google/chrome/google-chrome --profile-directory=Default --app-id=${CHROME_APP_ID}"

    MB_ADDR=""
    for _ in $(seq 1 80); do
        MB_ADDR=$(hyprctl -j clients | jq -r '.[] | select(.title | startswith("Musicboard")) | .address' | head -1)
        [ -n "$MB_ADDR" ] && break
        sleep 0.1
    done
    echo "musicboard addr: $MB_ADDR"

    # Let dwindle finish placing them
    sleep 0.6

    # Force tile in case spotify floated
    sp_floating=$(hyprctl -j clients | jq -r ".[] | select(.address==\"$SP_ADDR\") | .floating")
    echo "spotify floating: $sp_floating"
    if [ "$sp_floating" = "true" ]; then
        hyprctl dispatch focuswindow "address:$SP_ADDR"
        sleep 0.1
        hyprctl dispatch togglefloating "address:$SP_ADDR"
        sleep 0.2
    fi

    # Get x positions to determine which side each window landed on
    MB_X=$(hyprctl -j clients | jq -r ".[] | select(.address==\"$MB_ADDR\") | .at[0]")
    SP_X=$(hyprctl -j clients | jq -r ".[] | select(.address==\"$SP_ADDR\") | .at[0]")
    echo "MB_X: $MB_X, SP_X: $SP_X"

    # Focus musicboard
    hyprctl dispatch focuswindow "address:$MB_ADDR"
    sleep 0.15

    # We want musicboard on the LEFT. If it landed on the right, swap with spotify.
    if [ -n "$MB_X" ] && [ -n "$SP_X" ] && [ "$MB_X" -gt "$SP_X" ]; then
        echo "swapping musicboard to the left"
        hyprctl dispatch swapnext
        sleep 0.25
        hyprctl dispatch focuswindow "address:$MB_ADDR"
        sleep 0.15
    fi

    # Resize musicboard (active) to 28% — spotify expands to fill the rest
    hyprctl dispatch resizeactive exact 28% 100%
    sleep 0.2

    echo "--- final state ---"
    hyprctl -j clients | jq '.[] | select(.class=="Spotify" or (.title | startswith("Musicboard"))) | {class, title: .title[0:30], at, size, floating, workspace: .workspace.name}'
    exit 0
fi

hyprctl dispatch togglespecialworkspace music
