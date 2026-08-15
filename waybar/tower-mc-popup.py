#!/usr/bin/env python3
"""Minecraft server popup for tower. Sibling of tower-dl-popup.py.

Opens instantly from the cached snapshot, then refreshes live in a background
thread — the SSH round trip never blocks the window appearing.
"""
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GLib
import os
import subprocess
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import popup_lib
import tower_popup_ui as ui
from tower_cache import load, refresh_now, human_dt

PID_FILE = '/tmp/tower-mc-popup.pid'
MC = os.path.expanduser('~/.local/bin/mc')
LAN = '192.168.86.31:25565'
ICON = '󰍳'


def state_of(data):
    """(icon colour, state word, subline) — the popup's whole headline."""
    if not data or not data.get('reachable'):
        return ui.DIM, 'UNREACHABLE', 'tower is not answering on 192.168.86.31'
    mc = data.get('mc') or {}
    if mc.get('active') != 'active':
        return ui.BAD, 'STOPPED', f"service is {mc.get('active') or 'unknown'} · nobody can connect"
    n = mc.get('players', 0)
    who = ', '.join(mc.get('names') or [])
    sub = f"up {human_dt(mc.get('uptime'))} · {mc.get('mem', 0) / 1e9:.1f} GB heap"
    if n:
        return ui.CY, 'RUNNING', f'{sub} · {who}'
    return ui.OK, 'RUNNING', sub


class McPopup(Gtk.Window):
    def __init__(self):
        super().__init__()
        popup_lib.setup_window(self)

        self._data = load(auto_refresh=False)
        ip = ((self._data or {}).get('mc') or {}).get('public')
        self._public = f'{ip}:25565' if ip else None
        self._busy = False

        color, state, sub = state_of(self._data)
        self._provider = Gtk.CssProvider()
        self._apply_css(color)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), self._provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        blocker = popup_lib.wrap_with_click_outside(self, ui.POPUP_WIDTH)
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.get_style_context().add_class('popup-inner')
        root.set_size_request(ui.WIDTH, -1)
        blocker.add(root)

        hdr, self._sub = ui.header(ICON, state, sub, color)
        self._hdr_icon = hdr.get_children()[0].get_children()[0]
        self._hdr_state = hdr.get_children()[0].get_children()[1]
        root.pack_start(hdr, False, False, 0)

        self._body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.pack_start(self._body, False, False, 0)
        self._render_body()

        root.pack_start(ui.divider(), False, False, 0)

        life = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        life.set_margin_top(10)
        for label, verb in (('Start', 'start'), ('Restart', 'restart')):
            b = ui.button(label)
            b.connect('clicked', self._on_action, verb, f'{verb}ing server…')
            life.pack_start(b, True, True, 0)
        stop = ui.button('Stop', 'btn-danger')
        stop._armed = False
        stop._timer = None
        stop.connect('clicked', self._on_danger, 'Stop', 'Stop server?',
                     'stop', 'stopping server (world saves first)…')
        life.pack_end(stop, False, False, 12)
        root.pack_start(life, False, False, 0)

        tools = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        tools.set_margin_top(6)
        copy = ui.button('Copy address', 'btn-open')
        copy.connect('clicked', self._on_copy)
        logs = ui.button('Logs', 'btn-open')
        logs.connect('clicked', self._on_logs)
        tools.pack_start(copy, True, True, 0)
        tools.pack_start(logs, True, True, 0)
        root.pack_start(tools, False, False, 0)

        self._hint = Gtk.Label(label='refreshing…')
        self._hint.get_style_context().add_class('hint')
        self._hint.set_xalign(0)
        root.pack_start(self._hint, False, False, 0)

        self.connect('key-press-event', self._on_key)
        self.show_all()
        self.present()
        threading.Thread(target=self._refresh, daemon=True).start()

    # ---------- rendering ----------

    def _apply_css(self, color):
        self._provider.load_from_data(
            ui.CSS_TEMPLATE.format(state=color, glow=ui.GLOW[color]).encode())

    def _render_body(self):
        for c in self._body.get_children():
            self._body.remove(c)
        mc = (self._data or {}).get('mc') or {}
        reachable = bool(self._data and self._data.get('reachable'))

        self._body.pack_start(ui.section('Server'), False, False, 0)
        if not reachable:
            self._body.pack_start(ui.row('tower', 'no answer', 'v-bad'), False, False, 0)
        else:
            active = mc.get('active') == 'active'
            self._body.pack_start(
                ui.row('service', mc.get('active') or '?', 'v-ok' if active else 'v-bad'),
                False, False, 0)
            self._body.pack_start(ui.row('version', mc.get('version') or '—'), False, False, 0)
            names = mc.get('names') or []
            n = mc.get('players', 0)
            self._body.pack_start(
                ui.row('players', n if n else 'none', 'v-cy' if n else 'v-dim'),
                False, False, 0)
            if names:
                self._body.pack_start(ui.row('online', ', '.join(names), 'v-cy'), False, False, 0)
            self._body.pack_start(ui.row('heap', f"{mc.get('mem', 0) / 1e9:.1f} GB"), False, False, 0)
            self._body.pack_start(ui.row('load', mc.get('load') or '?'), False, False, 0)

        self._body.pack_start(ui.section('Connect'), False, False, 0)
        self._body.pack_start(ui.row('lan', LAN), False, False, 0)
        self._body.pack_start(ui.row('public', self._public or 'looking up…',
                                     'v-cy' if self._public else 'v-dim'), False, False, 0)
        self._body.show_all()

    def _render(self):
        color, state, sub = state_of(self._data)
        self._apply_css(color)
        self._hdr_state.set_label(state)
        self._sub.set_label(sub)
        self._render_body()
        return False

    # ---------- background work ----------

    def _refresh(self):
        data = refresh_now()

        def done():
            if data:
                self._data = data
            ip = ((self._data or {}).get('mc') or {}).get('public')
            self._public = f'{ip}:25565' if ip else 'unavailable'
            self._busy = False
            self._render()
            self._hint.set_label('live · Esc to close')
            return False
        GLib.idle_add(done)

    def _on_action(self, btn, verb, hint):
        if self._busy:
            return
        self._busy = True
        self._hint.set_label(hint)
        threading.Thread(target=self._run, args=(verb,), daemon=True).start()

    def _run(self, verb):
        try:
            subprocess.run([MC, verb], capture_output=True, timeout=90)
        except (OSError, subprocess.TimeoutExpired):
            pass
        self._refresh()

    # ---------- danger: two clicks, never one ----------

    def _disarm(self, btn, label):
        btn._armed = False
        btn.set_label(label)
        btn.get_style_context().remove_class('btn-armed')
        if btn._timer:
            GLib.source_remove(btn._timer)
            btn._timer = None
        return False

    def _on_danger(self, btn, label, confirm, verb, hint):
        if not btn._armed:
            btn._armed = True
            btn.set_label(confirm)
            btn.get_style_context().add_class('btn-armed')
            btn._timer = GLib.timeout_add_seconds(5, self._disarm, btn, label)
            return
        self._disarm(btn, label)
        self._on_action(btn, verb, hint)

    # ---------- small actions ----------

    def _on_copy(self, _btn):
        addr = self._public if self._public and ':' in self._public else LAN
        try:
            subprocess.run(['wl-copy', addr], timeout=3)
            self._hint.set_label(f'copied {addr}')
        except (OSError, subprocess.TimeoutExpired):
            self._hint.set_label('wl-copy failed')

    def _on_logs(self, _btn):
        subprocess.Popen(
            ['kitty', '--title', 'minecraft logs', '-e', 'bash', '-c',
             f'{MC} log 150; echo; echo "-- following --"; {MC} ssh '
             '"sudo journalctl -u minecraft -f"'],
            start_new_session=True)
        self.destroy()

    def _on_key(self, _w, event):
        if event.keyval == Gdk.KEY_Escape:
            self.destroy()


if __name__ == '__main__':
    popup_lib.run_popup(PID_FILE, McPopup)
