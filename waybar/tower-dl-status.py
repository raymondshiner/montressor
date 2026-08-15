#!/usr/bin/env python3
"""Waybar module: VPN-compartmented torrent stack on tower.

Same cache contract as tower-mc-status.py — no inline SSH on the bar path.
Colour semantics, strongest signal first:
  red    exit IP is not Mullvad, or gluetun is down  → traffic is unprotected
  yellow stale namespace / watchdog unhappy / a hardening setting flipped
  cyan   protected and actively downloading
  green  protected and idle
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tower_cache import load, human_rate

data = load()
dl = (data or {}).get('dl') or {}

if not data or not data.get('reachable'):
    print(json.dumps({'text': '󰇚 ?', 'class': 'unknown',
                      'tooltip': 'tower unreachable — 192.168.86.31'}, ensure_ascii=False))
    sys.exit(0)

cont = dl.get('containers') or {}
running = {c: v.get('status') == 'running' for c, v in cont.items()}
tor = dl.get('torrents') or {}
stale = dl.get('stale') or []
unhardened = dl.get('unhardened') or []
wd = dl.get('watchdog') or {}
down, total, speed = tor.get('downloading', 0), tor.get('total', 0), tor.get('speed', 0)

if not any(running.values()):
    # A stopped stack is a resting state, not an alarm — nothing is at risk.
    cls, text, head = 'down', '󰇚 off', 'Stack is down'
elif not running.get('gluetun'):
    cls, text, head = 'leak', '󰇚 NO VPN', 'gluetun is down — downloaders unprotected'
elif not dl.get('mullvad'):
    cls, text, head = 'leak', '󰇚 NO VPN', 'Exit IP is NOT Mullvad — traffic is not protected'
else:
    warn = []
    if stale:
        warn.append('stale namespace: ' + ', '.join(stale))
    if wd.get('state') and wd['state'] != 'OK':
        warn.append(f"watchdog {wd['state']}")
    if wd.get('timer') != 'active':
        warn.append('watchdog timer inactive')
    if unhardened:
        warn.append('hardening off: ' + ', '.join(unhardened))
    stopped = [c for c, up in running.items() if not up]
    if stopped:
        warn.append('not running: ' + ', '.join(stopped))

    if warn:
        cls, head = 'warn', ' · '.join(warn)
    elif down:
        cls, head = 'active', 'Protected — downloading'
    else:
        cls, head = 'ok', 'Protected — idle'
    text = f'󰇚 {down}  {human_rate(speed)}' if down else f'󰇚 {total}'

lines = [head]
if dl.get('mullvad'):
    lines.append(f"{dl.get('exit_ip')}  {dl.get('city') or ''}  {dl.get('server') or ''}".strip())
lines.append('')
lines.append('  '.join(f"{c}{'' if up else ' ✗'}" for c, up in running.items()) or 'no containers')
lines.append(f'torrents: {total} total, {down} downloading, {human_rate(speed)}')
if stale:
    lines.append('namespace STALE — run: dl restart')
disk = dl.get('disk') or {}
lines.append(f"incomplete {disk.get('incomplete', '?')}   media {disk.get('media', '?')}")
lines.append(f"snapshot {int(time.time() - data['ts'])}s ago")

print(json.dumps({'text': text, 'class': cls, 'tooltip': '\n'.join(lines)}, ensure_ascii=False))
