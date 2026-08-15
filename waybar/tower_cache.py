"""Shared access to the tower state snapshot.

One cache file feeds both waybar modules and both popups, so the whole desktop
costs at most one SSH round trip per refresh window instead of one per module.
"""
import json
import os
import subprocess
import time

CACHE = '/tmp/waybar-tower.json'
REFRESH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tower-refresh.sh')
MAX_AGE = 55  # seconds — just under the 60s waybar interval


def refresh_bg():
    """Kick a refresh without waiting. tower-refresh.sh flocks, so pile-ups are free."""
    try:
        subprocess.Popen([REFRESH], stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
    except OSError:
        pass


def load(auto_refresh=True):
    """Return the snapshot dict (possibly stale), or None if there's never been one."""
    try:
        with open(CACHE) as f:
            data = json.load(f)
    except (OSError, ValueError):
        if auto_refresh:
            refresh_bg()
        return None
    if auto_refresh and time.time() - data.get('ts', 0) > MAX_AGE:
        refresh_bg()
    return data


def refresh_now(timeout=25):
    """Blocking refresh — popups only, never the bar."""
    try:
        subprocess.run([REFRESH], capture_output=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        pass
    return load(auto_refresh=False)


def human_dt(seconds):
    seconds = int(seconds or 0)
    if seconds < 60:
        return f'{seconds}s'
    if seconds < 3600:
        return f'{seconds // 60}m'
    if seconds < 86400:
        return f'{seconds // 3600}h {seconds % 3600 // 60}m'
    return f'{seconds // 86400}d {seconds % 86400 // 3600}h'


def human_rate(bps):
    bps = int(bps or 0)
    if bps < 1000:
        return f'{bps} B/s'
    if bps < 1_000_000:
        return f'{bps / 1000:.0f} kB/s'
    return f'{bps / 1_000_000:.1f} MB/s'
