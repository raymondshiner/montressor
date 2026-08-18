#!/usr/bin/env python3
"""Torrent-stack popup for tower. Sibling of tower-mc-popup.py.

The headline answers one question: is the traffic behind Mullvad right now.
Everything else — containers, the stale-namespace trap, the watchdog, disk —
is supporting evidence underneath it.
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
from tower_cache import load, refresh_now, human_rate

PID_FILE = '/tmp/tower-dl-popup.pid'
DL = os.path.expanduser('~/.local/bin/dl')
QBIT = 'http://192.168.86.31:8080'
PROWLARR = 'http://192.168.86.31:9696'
SONARR = 'http://192.168.86.31:8989'
RADARR = 'http://192.168.86.31:7878'
# Not part of this stack (standalone, never behind gluetun) — link only, no status coupling.
ABS = 'http://192.168.86.31:13378'
ICON = '󰇚'
CONTAINERS = ('gluetun', 'qbittorrent', 'prowlarr', 'flaresolverr', 'sonarr', 'radarr')


def warnings_of(dl):
    w = []
    if dl.get('stale'):
        w.append('namespace stale')
    wd = dl.get('watchdog') or {}
    if wd.get('timer') != 'active':
        w.append('watchdog timer inactive')
    elif wd.get('state') and wd['state'] != 'OK':
        w.append(f"watchdog {wd['state']}")
    if dl.get('unhardened'):
        w.append('hardening off: ' + ', '.join(dl['unhardened']))
    down = [c for c in CONTAINERS
            if (dl.get('containers') or {}).get(c, {}).get('status') != 'running']
    if down and (dl.get('containers') or {}).get('gluetun', {}).get('status') == 'running':
        w.append('stopped: ' + ', '.join(down))
    return w


def state_of(data):
    if not data or not data.get('reachable'):
        return ui.DIM, 'UNREACHABLE', 'tower is not answering on 192.168.86.31'
    dl = data.get('dl') or {}
    cont = dl.get('containers') or {}
    if all(cont.get(c, {}).get('status') != 'running' for c in CONTAINERS):
        return ui.DIM, 'STACK DOWN', 'nothing is running — no traffic, nothing to protect'
    if cont.get('gluetun', {}).get('status') != 'running':
        return ui.BAD, 'NOT PROTECTED', 'gluetun is down — start the stack before downloading'
    if not dl.get('mullvad'):
        return ui.BAD, 'NOT PROTECTED', f"exit IP {dl.get('exit_ip') or 'unknown'} is not Mullvad"

    where = f"{dl.get('exit_ip')} · {dl.get('city') or '?'} · {dl.get('server') or '?'}"
    w = warnings_of(dl)
    if w:
        return ui.WARN, 'PROTECTED', where + ' — ' + '; '.join(w)
    tor = dl.get('torrents') or {}
    if tor.get('downloading'):
        return ui.CY, 'DOWNLOADING', f"{where} · {human_rate(tor.get('speed'))}"
    return ui.OK, 'PROTECTED', where


class DlPopup(Gtk.Window):
    def __init__(self):
        super().__init__()
        popup_lib.setup_window(self)

        self._data = load(auto_refresh=False)
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
        self._hdr_state = hdr.get_children()[0].get_children()[1]
        root.pack_start(hdr, False, False, 0)

        self._body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.pack_start(self._body, False, False, 0)
        self._render_body()

        root.pack_start(ui.divider(), False, False, 0)

        life = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        life.set_margin_top(10)
        for label, verb, hint in (('Start', 'up', 'starting stack…'),
                                  ('Restart', 'restart', 'restarting in order…')):
            b = ui.button(label)
            b.connect('clicked', self._on_action, verb, hint)
            life.pack_start(b, True, True, 0)
        stop = ui.button('Stop', 'btn-danger')
        stop._armed = False
        stop._timer = None
        stop.connect('clicked', self._on_danger, 'Stop', 'Stop stack?',
                     'down', 'stopping stack…')
        life.pack_end(stop, False, False, 12)
        root.pack_start(life, False, False, 0)

        tools = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        tools.set_margin_top(6)
        for label, url in (('qBittorrent', QBIT), ('Prowlarr', PROWLARR)):
            b = ui.button(label, 'btn-open')
            b.connect('clicked', self._on_open, url)
            tools.pack_start(b, True, True, 0)
        logs = ui.button('Logs', 'btn-open')
        logs.connect('clicked', self._on_logs)
        tools.pack_start(logs, True, True, 0)
        root.pack_start(tools, False, False, 0)

        arrs = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        arrs.set_margin_top(6)
        for label, url in (('Sonarr', SONARR), ('Radarr', RADARR), ('Audiobooks', ABS)):
            b = ui.button(label, 'btn-open')
            b.connect('clicked', self._on_open, url)
            arrs.pack_start(b, True, True, 0)
        root.pack_start(arrs, False, False, 0)

        # Own row, well clear of everything benign: this one cuts the tunnel.
        verify = ui.button('Leak test — cuts the tunnel ~15s', 'btn-danger')
        verify._armed = False
        verify._timer = None
        verify.connect('clicked', self._on_verify)
        verify.set_margin_top(14)
        root.pack_start(verify, False, False, 0)

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
        add = lambda w: self._body.pack_start(w, False, False, 0)

        if not (self._data and self._data.get('reachable')):
            add(ui.section('Stack'))
            add(ui.row('tower', 'no answer', 'v-bad'))
            self._body.show_all()
            return

        dl = self._data.get('dl') or {}
        cont = dl.get('containers') or {}
        stale = dl.get('stale') or []

        add(ui.section('Tunnel'))
        add(ui.row('is mullvad', 'yes' if dl.get('mullvad') else 'NO',
                   'v-ok' if dl.get('mullvad') else 'v-bad'))
        add(ui.row('exit ip', dl.get('exit_ip') or 'unreachable',
                   'v-ok' if dl.get('mullvad') else 'v-bad'))
        add(ui.row('server', dl.get('server') or '—'))

        add(ui.section('Containers'))
        for c in CONTAINERS:
            info = cont.get(c) or {}
            st = info.get('status') or 'missing'
            health = info.get('health')
            label = f'{st} ({health})' if health else st
            tone = 'v-ok' if st == 'running' else 'v-bad'
            if st == 'running' and health and health != 'healthy':
                tone = 'v-warn'
            add(ui.row(c, label, tone))
        if stale:
            add(ui.row('namespace', 'STALE: ' + ', '.join(stale), 'v-bad'))
            add(ui.row('', 'unreachable on LAN — hit Restart', 'v-warn'))
        else:
            add(ui.row('namespace', 'fresh', 'v-ok'))

        add(ui.section('Activity'))
        tor = dl.get('torrents') or {}
        add(ui.row('torrents', tor.get('total', 0)))
        add(ui.row('downloading', tor.get('downloading', 0),
                   'v-cy' if tor.get('downloading') else 'v-dim'))
        add(ui.row('speed', human_rate(tor.get('speed')),
                   'v-cy' if tor.get('speed') else 'v-dim'))
        for t in (tor.get('top') or []):
            if t.get('speed') or t.get('state', '').endswith('DL'):
                name = t['name'][:26] + ('…' if len(t['name']) > 26 else '')
                add(ui.row(name, f"{t['pct']}%  {human_rate(t['speed'])}", 'v-cy'))

        add(ui.section('Guard'))
        wd = dl.get('watchdog') or {}
        add(ui.row('watchdog', wd.get('timer') or '?',
                   'v-ok' if wd.get('timer') == 'active' else 'v-bad'))
        if wd.get('state'):
            when = (wd.get('ts') or '')[11:16]
            add(ui.row('last check', f"{wd['state']}  {when}",
                       'v-ok' if wd['state'] == 'OK' else 'v-bad'))
        unh = dl.get('unhardened') or []
        add(ui.row('hardening', 'all on' if not unh else 'off: ' + ', '.join(unh),
                   'v-ok' if not unh else 'v-warn'))

        add(ui.section('Disk'))
        disk = dl.get('disk') or {}
        add(ui.row('in progress', disk.get('incomplete') or '?',
                   'v-warn' if disk.get('incomplete_pct', 0) > 85 else None))
        add(ui.row('finished', disk.get('media') or '?',
                   'v-warn' if disk.get('media_pct', 0) > 85 else None))
        add(ui.row('waiting', f"{disk.get('waiting', 0)} files"))
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
            subprocess.run([DL, verb], capture_output=True, timeout=180)
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

    def _on_verify(self, btn):
        label = 'Leak test — cuts the tunnel ~15s'
        if not btn._armed:
            btn._armed = True
            btn.set_label('Run it? downloads stall ~15s')
            btn.get_style_context().add_class('btn-armed')
            btn._timer = GLib.timeout_add_seconds(5, self._disarm, btn, label)
            return
        self._disarm(btn, label)
        subprocess.Popen(
            ['kitty', '--title', 'dl verify', '-e', 'bash', '-c',
             f'{DL} verify; echo; read -n1 -p "enter to close"'],
            start_new_session=True)
        self.destroy()

    # ---------- small actions ----------

    def _on_open(self, _btn, url):
        subprocess.Popen(['xdg-open', url], start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.destroy()

    def _on_logs(self, _btn):
        subprocess.Popen(
            ['kitty', '--title', 'torrent stack logs', '-e', 'bash', '-c',
             f'{DL} logs gluetun'],
            start_new_session=True)
        self.destroy()

    def _on_key(self, _w, event):
        if event.keyval == Gdk.KEY_Escape:
            self.destroy()


if __name__ == '__main__':
    popup_lib.run_popup(PID_FILE, DlPopup)
