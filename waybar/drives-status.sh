#!/bin/bash
# Emit waybar JSON only when at least one removable drive is mounted.
# Empty output => waybar hides the module.

count=$(lsblk -J -o NAME,MOUNTPOINT,RM,TYPE 2>/dev/null | \
    python3 -c '
import json,sys
try: d=json.load(sys.stdin)
except: print(0); sys.exit()
n=0
def walk(nodes):
    global n
    for x in nodes:
        if x.get("rm") and x.get("mountpoint") and x.get("type") in ("part","disk"):
            n+=1
        if x.get("children"): walk(x["children"])
walk(d.get("blockdevices",[]))
print(n)')

if [ "${count:-0}" -gt 0 ]; then
    printf '{"text":"󰋊 %d","class":"active","tooltip":"%d removable drive(s) mounted"}\n' "$count" "$count"
fi
