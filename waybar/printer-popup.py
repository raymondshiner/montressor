#!/usr/bin/env python3
"""Print queue popup. Uses the tower popups' layout grammar.

Auto-refreshes every 2s while open so a submitted job can be watched
moving through the queue — the whole point is confirming a print is
actually printing.
"""
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GLib
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import popup_lib
import tower_popup_ui as ui

PID_FILE = '/tmp/printer-popup.pid'
ICON = '󰐪'


def sh(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=3).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ''


def poll():
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

    # lpq has the document names; lpstat -o has the full job ids.
    files = {}
    for line in sh(['lpq', '-a']).splitlines():
        m = re.match(r'(\S+)\s+\S+\s+(\d+)\s+(.+?)\s+(\d+) bytes$', line)
        if m and m.group(1) != 'Rank':
            files[m.group(2)] = (m.group(3).strip(), int(m.group(4)),
                                 m.group(1) == 'active')

    jobs = []
    for line in sh(['lpstat', '-o']).splitlines():
        parts = line.split()
        if not parts:
            continue
        num = parts[0].rsplit('-', 1)[-1]
        fname, size, active = files.get(num, ('—', 0, False))
        jobs.append({'id': parts[0], 'num': num, 'file': fname,
                     'size': size, 'active': active})
    return printers, jobs


def state_of(printers, jobs):
    if not printers:
        return ui.DIM, 'NO PRINTER', 'no printers configured in CUPS'
    name = printers[0][0]
    if any(s == 'disabled' for _, s in printers):
        return ui.BAD, 'STOPPED', f'{name} is disabled · jobs will not print'
    if jobs or any(s == 'printing' for _, s in printers):
        n = len(jobs)
        return ui.CY, 'PRINTING', f'{n} job{"s" if n != 1 else ""} in queue on {name}'
    return ui.OK, 'READY', f'{name} idle · queue empty'


def human_size(b):
    if b >= 1e6:
        return f'{b / 1e6:.1f} MB'
    if b >= 1e3:
        return f'{b / 1e3:.0f} kB'
    return f'{b} B'


class PrinterPopup(Gtk.Window):
    def __init__(self):
        super().__init__()
        popup_lib.setup_window(self)

        self._printers, self._jobs = poll()
        self._busy = False

        color, state, sub = state_of(self._printers, self._jobs)
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

        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        actions.set_margin_top(10)
        web = ui.button('Web UI', 'btn-open')
        web.connect('clicked', self._on_web)
        actions.pack_start(web, True, True, 0)
        cancel = ui.button('Cancel all', 'btn-danger')
        cancel._armed = False
        cancel._timer = None
        cancel.connect('clicked', self._on_danger, 'Cancel all', 'Cancel all jobs?')
        actions.pack_end(cancel, False, False, 12)
        root.pack_start(actions, False, False, 0)

        self._hint = Gtk.Label(label='live · Esc to close')
        self._hint.get_style_context().add_class('hint')
        self._hint.set_xalign(0)
        root.pack_start(self._hint, False, False, 0)

        self.connect('key-press-event', self._on_key)
        self.show_all()
        self.present()
        GLib.timeout_add_seconds(2, self._tick)

    # ---------- rendering ----------

    def _apply_css(self, color):
        self._provider.load_from_data(
            ui.CSS_TEMPLATE.format(state=color, glow=ui.GLOW[color]).encode())

    def _render_body(self):
        for c in self._body.get_children():
            self._body.remove(c)

        self._body.pack_start(ui.section('Printer'), False, False, 0)
        if not self._printers:
            self._body.pack_start(ui.row('cups', 'no printers', 'v-dim'), False, False, 0)
        for name, state in self._printers:
            tone = {'printing': 'v-cy', 'disabled': 'v-bad'}.get(state, 'v-ok')
            self._body.pack_start(ui.row(name, state, tone), False, False, 0)

        self._body.pack_start(ui.section('Queue'), False, False, 0)
        if not self._jobs:
            self._body.pack_start(ui.row('jobs', 'empty', 'v-dim'), False, False, 0)
        for j in self._jobs:
            label = f"#{j['num']}" + ('  ▶' if j['active'] else '')
            val = j['file']
            if j['size']:
                val += f"  ·  {human_size(j['size'])}"
            tone = 'v-cy' if j['active'] else None
            self._body.pack_start(ui.row(label, val, tone), False, False, 0)
        self._body.show_all()

    def _render(self):
        color, state, sub = state_of(self._printers, self._jobs)
        self._apply_css(color)
        self._hdr_state.set_label(state)
        self._sub.set_label(sub)
        self._render_body()

    # ---------- polling ----------

    def _tick(self):
        self._printers, self._jobs = poll()
        self._render()
        return True

    # ---------- actions ----------

    def _on_web(self, _btn):
        subprocess.Popen(['xdg-open', 'http://localhost:631/jobs'],
                         start_new_session=True)
        self.destroy()

    def _disarm(self, btn, label):
        btn._armed = False
        btn.set_label(label)
        btn.get_style_context().remove_class('btn-armed')
        if btn._timer:
            GLib.source_remove(btn._timer)
            btn._timer = None
        return False

    def _on_danger(self, btn, label, confirm):
        if not btn._armed:
            btn._armed = True
            btn.set_label(confirm)
            btn.get_style_context().add_class('btn-armed')
            btn._timer = GLib.timeout_add_seconds(5, self._disarm, btn, label)
            return
        self._disarm(btn, label)
        sh(['cancel', '-a'])
        self._hint.set_label('cancelled all jobs')
        self._tick()

    def _on_key(self, _w, event):
        if event.keyval == Gdk.KEY_Escape:
            self.destroy()


if __name__ == '__main__':
    popup_lib.run_popup(PID_FILE, PrinterPopup)
