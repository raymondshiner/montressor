#!/usr/bin/env python3
"""Waybar module: CUPS print queue. Local lpstat calls — fast, no network."""
import json
import subprocess


def sh(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=3).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ''


printers = []
for line in sh(['lpstat', '-p']).splitlines():
    if line.startswith('printer '):
        name = line.split()[1]
        if 'disabled' in line:
            state = 'disabled'
        elif 'printing' in line:
            state = 'printing'
        else:
            state = 'idle'
        printers.append((name, state))

jobs = [l for l in sh(['lpstat', '-o']).splitlines() if l.strip()]
n = len(jobs)

if not printers:
    out = {'text': '󰐪', 'class': 'unknown', 'tooltip': 'no printers configured'}
elif any(s == 'disabled' for _, s in printers):
    bad = ', '.join(p for p, s in printers if s == 'disabled')
    out = {'text': '󰐪 !', 'class': 'off', 'tooltip': f'printer disabled: {bad}'}
elif n or any(s == 'printing' for _, s in printers):
    lines = [f'{n} job{"s" if n != 1 else ""} in queue'] + jobs
    out = {'text': f'󰐪 {n}', 'class': 'active', 'tooltip': '\n'.join(lines)}
else:
    tip = '\n'.join(f'{p} — idle' for p, _ in printers) + '\nqueue empty'
    out = {'text': '󰐪', 'class': 'idle', 'tooltip': tip}

print(json.dumps(out, ensure_ascii=False))
