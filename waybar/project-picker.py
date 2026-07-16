#!/usr/bin/env python3
"""Project picker overlay (Super+P).

Styled to match the rofi Super+Space launcher: a screen-centered box with a
cyan border and a live-filter search bar on top. Type to filter, Enter opens
the top active project, Escape closes.

Lists ACTIVE code projects (click = open in a launch workspace; ✕ = archive),
then PREVIOUS projects (click = reopen/restore;  = remove) and any launch-ready
~/src project you can ADD. Registry is managed by the `project-active` bin.
"""
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
from gi.repository import Gtk, Gdk, GtkLayerShell
import subprocess
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import popup_lib

PID_FILE = '/tmp/project-picker.pid'
WIDTH = 560

HOME = os.path.expanduser('~')
BIN = os.path.join(HOME, '.local', 'bin')
SRC = os.path.join(HOME, 'src')
PA = os.path.join(BIN, 'project-active')
LAUNCH = os.path.join(BIN, 'launch')
CURRENT_PROJECT = os.path.join(BIN, 'current-project')

# Mirrors montressor/rofi/andromeda.rasi: bg-dark #1C1E26, bg #23262E,
# fg #D5CED9, muted #677691, cyan #00E8C6.
CSS = """
window { background: transparent; }
.picker-inner {
    background-color: #1C1E26;
    border: 2px solid #00E8C6;
    border-radius: 12px;
    padding: 12px;
}
.inputbar {
    background-color: #23262E;
    border-radius: 8px;
    padding: 6px 14px;
}
.prompt {
    color: #00E8C6;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 15px;
}
entry.search {
    background: transparent;
    background-image: none;
    border: none;
    box-shadow: none;
    color: #D5CED9;
    caret-color: #00E8C6;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 14px;
    padding: 4px 0;
}
entry.search selection { background-color: #00E8C6; color: #1C1E26; }
.section-label {
    color: #677691;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 10px;
    letter-spacing: 1px;
    margin-top: 8px;
    margin-bottom: 2px;
}
.empty-hint {
    color: #677691;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 13px;
    font-style: italic;
    padding: 8px 2px;
}
.row {
    background: transparent;
    background-image: none;
    border: none;
    border-radius: 8px;
    padding: 8px 10px;
    box-shadow: none;
    text-shadow: none;
}
.row:hover { background-color: #23262E; }
.row:hover .proj-name { color: #00E8C6; }
.proj-name {
    color: #D5CED9;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 14px;
}
.proj-sub {
    color: #677691;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 10px;
}
.icon-btn {
    background: transparent;
    background-image: none;
    color: #677691;
    border: none;
    border-radius: 8px;
    padding: 4px 12px;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 14px;
    box-shadow: none;
    text-shadow: none;
}
.icon-btn:hover { background-color: #23262E; color: #EE5D43; }
.add-btn:hover .proj-name { color: #A8FF60; }
"""


def registry(kind):
    try:
        out = subprocess.check_output([PA, 'list', kind, '--json'], text=True)
        return json.loads(out or '[]')
    except Exception:
        return []


def launch_ready_srcs():
    names = []
    try:
        for d in sorted(os.listdir(SRC)):
            if os.path.isfile(os.path.join(SRC, d, '.project.json')):
                names.append(d)
    except OSError:
        pass
    return names


class ProjectPicker(Gtk.Window):
    def __init__(self):
        super().__init__()
        popup_lib.setup_window(self)
        # Grab the keyboard like rofi so typing lands in the filter immediately.
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.EXCLUSIVE)

        provider = Gtk.CssProvider()
        provider.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        # Full-screen catcher → click anywhere outside the box dismisses.
        catcher = Gtk.EventBox()
        catcher.connect('button-press-event', lambda *_: self.destroy() or True)
        self.add(catcher)

        center = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        center.set_halign(Gtk.Align.CENTER)
        center.set_valign(Gtk.Align.CENTER)
        catcher.add(center)

        blocker = Gtk.EventBox()
        blocker.connect('button-press-event', lambda *_: True)
        center.pack_start(blocker, False, False, 0)

        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        inner.get_style_context().add_class('picker-inner')
        inner.set_size_request(WIDTH, -1)
        blocker.add(inner)

        # ── Search bar (matches rofi inputbar) ──
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        bar.get_style_context().add_class('inputbar')
        prompt = Gtk.Label(label='')
        prompt.get_style_context().add_class('prompt')
        bar.pack_start(prompt, False, False, 0)
        self.entry = Gtk.Entry()
        self.entry.get_style_context().add_class('search')
        self.entry.set_placeholder_text('search projects…')
        self.entry.set_has_frame(False)
        self.entry.set_hexpand(True)
        self.entry.connect('changed', lambda *_: self._rebuild())
        self.entry.connect('activate', lambda *_: self._activate_first())
        bar.pack_start(self.entry, True, True, 0)
        inner.pack_start(bar, False, False, 0)

        # ── Scrollable result list ──
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_propagate_natural_height(True)
        scroller.set_max_content_height(440)
        self.body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        scroller.add(self.body)
        inner.pack_start(scroller, True, True, 0)

        self._first_open = None
        self._rebuild()
        self.connect('key-press-event', self._on_key)
        self.show_all()
        self.present()
        self.entry.grab_focus()

    # ── UI construction ──────────────────────────────────────────────────────
    def _filter(self, names):
        q = self.entry.get_text().strip().lower()
        return [n for n in names if q in n.lower()] if q else names

    def _rebuild(self):
        for c in self.body.get_children():
            self.body.remove(c)
        self._first_open = None

        active = registry('active')
        archived = registry('archived')
        active_names = {p['name'] for p in active}
        archived_names = {p['name'] for p in archived}

        act = [p for p in active if self._passes(p['name'])]
        arc = [p for p in archived if self._passes(p['name'])]
        add = [n for n in launch_ready_srcs()
               if n not in active_names and n not in archived_names
               and self._passes(n)]

        if act:
            self._section('ACTIVE')
            for p in act:
                self.body.pack_start(self._active_row(p), False, False, 0)
        elif not self.entry.get_text().strip():
            hint = Gtk.Label(label='No active projects — add one below')
            hint.get_style_context().add_class('empty-hint')
            hint.set_xalign(0)
            self.body.pack_start(hint, False, False, 0)

        if arc:
            self._section('PREVIOUS')
            for p in arc:
                self.body.pack_start(self._archived_row(p), False, False, 0)

        if add:
            self._section('ADD')
            for n in add:
                self.body.pack_start(self._add_row(n), False, False, 0)

        self.body.show_all()

    def _passes(self, name):
        q = self.entry.get_text().strip().lower()
        return (q in name.lower()) if q else True

    def _section(self, text):
        lbl = Gtk.Label(label=text)
        lbl.get_style_context().add_class('section-label')
        lbl.set_xalign(0)
        self.body.pack_start(lbl, False, False, 0)

    def _row_button(self, name, subtitle, prefix=''):
        btn = Gtk.Button()
        btn.get_style_context().add_class('row')
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        nl = Gtk.Label(label=f'{prefix}{name}')
        nl.get_style_context().add_class('proj-name')
        nl.set_xalign(0)
        inner.pack_start(nl, False, False, 0)
        if subtitle:
            sl = Gtk.Label(label=subtitle)
            sl.get_style_context().add_class('proj-sub')
            sl.set_xalign(0)
            inner.pack_start(sl, False, False, 0)
        btn.add(inner)
        return btn

    def _active_row(self, p):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        sub = f"opened {p.get('lastOpened') or p.get('added') or '—'}"
        btn = self._row_button(p['name'], sub)
        btn.connect('clicked', lambda *_: self._open(p['name']))
        row.pack_start(btn, True, True, 0)
        if self._first_open is None:
            self._first_open = p['name']

        arch = Gtk.Button(label='✕')
        arch.get_style_context().add_class('icon-btn')
        arch.set_tooltip_text('Archive (move to Previous)')
        arch.set_valign(Gtk.Align.CENTER)
        arch.connect('clicked', lambda *_: self._run(PA, 'archive', p['name']))
        row.pack_start(arch, False, False, 0)
        return row

    def _archived_row(self, p):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        sub = f"closed {p.get('closed') or '—'}"
        btn = self._row_button(p['name'], sub)
        btn.set_tooltip_text('Reopen (restores to Active)')
        btn.connect('clicked', lambda *_: (self._run(PA, 'restore', p['name'], rebuild=False),
                                           self._open(p['name'])))
        row.pack_start(btn, True, True, 0)

        rm = Gtk.Button(label='')
        rm.get_style_context().add_class('icon-btn')
        rm.set_tooltip_text('Remove from registry')
        rm.set_valign(Gtk.Align.CENTER)
        rm.connect('clicked', lambda *_: self._run(PA, 'rm', p['name']))
        row.pack_start(rm, False, False, 0)
        return row

    def _add_row(self, name):
        btn = self._row_button(name, None, prefix='＋  ')
        btn.get_style_context().add_class('add-btn')
        btn.connect('clicked', lambda *_: self._run(PA, 'add', name))
        return btn

    # ── Actions ──────────────────────────────────────────────────────────────
    def _run(self, *args, rebuild=True):
        try:
            subprocess.run(list(args), check=False)
        except Exception:
            pass
        if rebuild:
            self._rebuild()

    def _activate_first(self):
        if self._first_open:
            self._open(self._first_open)

    def _open(self, name):
        try:
            subprocess.run([CURRENT_PROJECT, name], check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run([PA, 'touch', name], check=False)
        except Exception:
            pass
        subprocess.Popen(['setsid', LAUNCH, name],
                         stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL,
                         start_new_session=True)
        self.destroy()

    def _on_key(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.destroy()


if __name__ == '__main__':
    popup_lib.run_popup(PID_FILE, ProjectPicker)
