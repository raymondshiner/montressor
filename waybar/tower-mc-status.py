#!/usr/bin/env python3
"""Waybar module: Minecraft server on tower.

Reads the shared /tmp/waybar-tower.json snapshot — never SSHes inline, because a
multi-second round trip on the bar-refresh path would stall waybar. When the
snapshot goes stale it fires tower-refresh.sh in the background and renders the
last known state; the next tick picks up the fresh one.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tower_cache import load, human_dt

data = load()
mc = (data or {}).get('mc') or {}

if not data or not data.get('reachable'):
    print(json.dumps({'text': '󰍳 ?', 'class': 'unknown',
                      'tooltip': 'tower unreachable — 192.168.86.31'}, ensure_ascii=False))
    sys.exit(0)

active = mc.get('active')
players = mc.get('players', 0)
names = mc.get('names') or []

if active == 'active':
    cls = 'active' if players else 'ok'
    text = f'󰍳 {players}'
else:
    cls = 'off'
    text = '󰍳 ·'

lines = [f"Minecraft — {active or 'unknown'}"]
if mc.get('version'):
    lines.append(mc['version'])
if active == 'active':
    lines.append(f"up {human_dt(mc.get('uptime', 0))}   heap {mc.get('mem', 0) / 1e9:.1f} GB")
    lines.append(f"players: {', '.join(names) if names else 'nobody online'}")
    lines.append(f"load {mc.get('load', '?')}")
lines.append('192.168.86.31:25565')
lines.append(f"snapshot {int(time.time() - data['ts'])}s ago")

print(json.dumps({'text': text, 'class': cls, 'tooltip': '\n'.join(lines)}, ensure_ascii=False))
