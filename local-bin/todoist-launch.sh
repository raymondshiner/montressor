#!/bin/bash
# Super+T: Todoist overlay on special:todoist.
#   left half  = Todoist GUI app (class "todoist")
#   right half = dedicated jarvis instance wired to the Todoist MCP (class "jarvis-todoist")
# Mirrors music-launch.sh: special workspace + dwindle tiling. First launch builds
# and shows the overlay; afterwards Super+T just toggles it. A stray Todoist window
# already open elsewhere is captured into the overlay rather than duplicated.

WS="special:todoist"
LOG=/tmp/todoist-launch.log
: > "$LOG"
exec >>"$LOG" 2>&1
echo "=== $(date) ==="

# Todoist's main window class is "Todoist"; a secondary settings window is "todoist" — match either.
td_addr()    { hyprctl -j clients | jq -r '.[] | select(.class|ascii_downcase=="todoist") | .address' | head -1; }
jv_addr()    { hyprctl -j clients | jq -r '.[] | select(.class=="jarvis-todoist") | .address' | head -1; }
ws_of()      { hyprctl -j clients | jq -r ".[] | select(.address==\"$1\") | .workspace.name"; }
x_of()       { hyprctl -j clients | jq -r ".[] | select(.address==\"$1\") | .at[0]"; }
floating_of(){ hyprctl -j clients | jq -r ".[] | select(.address==\"$1\") | .floating"; }

TD=$(td_addr); JV=$(jv_addr)
echo "todoist=$TD jarvis=$JV"

# Fully built already (both windows live on the overlay) -> plain toggle.
if [ -n "$TD" ] && [ -n "$JV" ] \
   && [ "$(ws_of "$TD")" = "$WS" ] && [ "$(ws_of "$JV")" = "$WS" ]; then
    echo "overlay built -> toggle"
    hyprctl dispatch togglespecialworkspace todoist
    exit 0
fi

# --- Build the overlay: show it, then populate + arrange while visible ---
hyprctl dispatch togglespecialworkspace todoist
sleep 0.2

# Todoist GUI app — move an existing window in, else spawn fresh.
if [ -n "$TD" ]; then
    hyprctl dispatch movetoworkspacesilent "$WS,address:$TD"
else
    hyprctl dispatch exec "[workspace $WS silent; tile] env DESKTOPINTEGRATION=false /usr/bin/todoist --ozone-platform=x11"
    for _ in $(seq 1 150); do TD=$(td_addr); [ -n "$TD" ] && break; sleep 0.1; done
fi
echo "todoist addr: $TD"

# Jarvis instance wired to the Todoist MCP — move existing, else spawn seeded.
if [ -n "$JV" ]; then
    hyprctl dispatch movetoworkspacesilent "$WS,address:$JV"
else
    # No seed prompt — just a ready Todoist-wired jarvis waiting for instructions.
    hyprctl dispatch exec "[workspace $WS silent; tile] kitty --class=jarvis-todoist --title=JarvisTodoist -e env JARVIS_MCP=todoist AGENT_ALLOWED_TOOLS=mcp__todoist__* $HOME/.local/bin/jarvis"
    for _ in $(seq 1 100); do JV=$(jv_addr); [ -n "$JV" ] && break; sleep 0.1; done
fi
echo "jarvis addr: $JV"

# Let dwindle settle.
sleep 0.6

# Force-tile anything that floated.
for A in "$TD" "$JV"; do
    [ -n "$A" ] || continue
    if [ "$(floating_of "$A")" = "true" ]; then
        hyprctl dispatch focuswindow "address:$A"; sleep 0.1
        hyprctl dispatch togglefloating "address:$A"; sleep 0.2
    fi
done

# Ensure Todoist landed on the LEFT (lower x). Swap if it's on the right.
TD_X=$(x_of "$TD"); JV_X=$(x_of "$JV")
echo "TD_X=$TD_X JV_X=$JV_X"
hyprctl dispatch focuswindow "address:$TD"; sleep 0.15
if [ -n "$TD_X" ] && [ -n "$JV_X" ] && [ "$TD_X" -gt "$JV_X" ]; then
    echo "swapping todoist to the left"
    hyprctl dispatch swapnext; sleep 0.25
    hyprctl dispatch focuswindow "address:$TD"; sleep 0.15
fi

# Todoist (active) -> 50% width; jarvis expands to fill the other half.
hyprctl dispatch resizeactive exact 50% 100%
sleep 0.2

echo "--- final ---"
hyprctl -j clients | jq '.[] | select((.class|ascii_downcase=="todoist") or .class=="jarvis-todoist") | {class, at, size, floating, ws: .workspace.name}'
