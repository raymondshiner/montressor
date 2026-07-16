#!/usr/bin/env python3
"""Project picker overlay (Super+Shift+P).

Lists ACTIVE code projects — click one to open it in a launch workspace.
Each active row has a ✕ that archives it (moves it to Previous). A foldout
shows previous projects (reopen restores them) and a foldout lets you add
any launch-ready ~/src project to the active list.

Registry is managed by the `project-active` bin.
"""
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk
import subprocess
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import popup_lib

PID_FILE = '/tmp/project-picker.pid'
WIDTH = 340
POPUP_WIDTH = WIDTH + 16

HOME = os.path.expanduser('~')
BIN = os.path.join(HOME, '.local', 'bin')
SRC = os.path.join(HOME, 'src')
PA = os.path.join(BIN, 'project-active')
LAUNCH = os.path.join(BIN, 'launch')
CURRENT_PROJECT = os.path.join(BIN, 'current-project')

CSS = """
window { background: transparent; }
.popup-inner {
    background-color: rgba(28, 30, 38, 0.98);
    border-radius: 10px;
    margin: 8px;
    padding: 16px;
    box-shadow:
        0 28px 28px rgba(0, 0, 0, 0.8),
        0 20px 20px rgba(220, 220, 220, 0.55),
        0 40px 40px rgba(220, 220, 220, 0.25);
}
.picker-title {
    color: #D5CED9;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 15px;
    font-weight: bold;
}
.section-label {
    color: #677691;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 10px;
    letter-spacing: 1px;
    margin-top: 10px;
    margin-bottom: 2px;
}
.empty-hint {
    color: #677691;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 12px;
    font-style: italic;
    padding: 4px 2px;
}
.proj-btn {
    background: transparent;
    background-image: none;
    border: 1px solid #2A2D3A;
    border-radius: 6px;
    padding: 8px 12px;
    box-shadow: none;
    text-shadow: none;
}
.proj-btn:hover {
    background-color: #2A2D3A;
    border-color: #00E8C6;
}
.proj-name {
    color: #D5CED9;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 13px;
    font-weight: bold;
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
    border: 1px solid #2A2D3A;
    border-radius: 6px;
    padding: 4px 10px;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 13px;
    box-shadow: none;
    text-shadow: none;
}
.icon-btn:hover {
    background-color: #2A2D3A;
    color: #EE5D43;
    border-color: #EE5D43;
}
.add-btn:hover {
    color: #A8FF60;
    border-color: #A8FF60;
}
expander {
    color: #677691;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 11px;
}
expander title { color: #677691; }
"""


def registry(kind):
    """Return list of project dicts for 'active' or 'archived'."""
    try:
        out = subprocess.check_output([PA, 'list', kind, '--json'], text=True)
        return json.loads(out or '[]')
    except Exception:
        return []


def launch_ready_srcs():
    """~/src dirs with a .project.json, as bare names."""
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

        provider = Gtk.CssProvider()
        provider.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        blocker = popup_lib.wrap_with_click_outside(self, POPUP_WIDTH, center=True)

        self.root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.root.get_style_context().add_class('popup-inner')
        self.root.set_size_request(WIDTH, -1)
        blocker.add(self.root)

        title = Gtk.Label(label='Projects')
        title.get_style_context().add_class('picker-title')
        title.set_xalign(0)
        self.root.pack_start(title, False, False, 0)

        self.body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.root.pack_start(self.body, False, False, 0)

        self._rebuild()
        self.connect('key-press-event', self._on_key)
        self.show_all()
        self.present()

    # ── UI construction ──────────────────────────────────────────────────────
    def _rebuild(self):
        for c in self.body.get_children():
            self.body.remove(c)

        # ── Active ──
        self._section_label('ACTIVE')
        active = registry('active')
        active_names = {p['name'] for p in active}
        if active:
            for p in active:
                self.body.pack_start(self._active_row(p), False, False, 0)
        else:
            hint = Gtk.Label(label='No active projects — add one below')
            hint.get_style_context().add_class('empty-hint')
            hint.set_xalign(0)
            self.body.pack_start(hint, False, False, 0)

        # ── Previous (foldout) ──
        archived = registry('archived')
        if archived:
            exp = Gtk.Expander(label=f'  Previous ({len(archived)})')
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            box.set_margin_top(4)
            for p in archived:
                box.pack_start(self._archived_row(p), False, False, 0)
            exp.add(box)
            self.body.pack_start(exp, False, False, 0)

        # ── Add (foldout) — launch-ready ~/src projects not already tracked ──
        addable = [n for n in launch_ready_srcs()
                   if n not in active_names
                   and n not in {p['name'] for p in archived}]
        if addable:
            exp = Gtk.Expander(label=f'  ＋ Add project ({len(addable)})')
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            box.set_margin_top(4)
            for n in addable:
                box.pack_start(self._add_row(n), False, False, 0)
            exp.add(box)
            self.body.pack_start(exp, False, False, 0)

        self.body.show_all()

    def _section_label(self, text):
        lbl = Gtk.Label(label=text)
        lbl.get_style_context().add_class('section-label')
        lbl.set_xalign(0)
        self.body.pack_start(lbl, False, False, 0)

    def _proj_button(self, name, subtitle):
        btn = Gtk.Button()
        btn.get_style_context().add_class('proj-btn')
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        nl = Gtk.Label(label=name)
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
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        sub = f"opened {p.get('lastOpened') or p.get('added') or '—'}"
        btn = self._proj_button(p['name'], sub)
        btn.connect('clicked', lambda *_: self._open(p['name']))
        row.pack_start(btn, True, True, 0)

        arch = Gtk.Button(label='✕')
        arch.get_style_context().add_class('icon-btn')
        arch.set_tooltip_text('Archive (move to Previous)')
        arch.set_valign(Gtk.Align.CENTER)
        arch.connect('clicked', lambda *_: self._run(PA, 'archive', p['name']))
        row.pack_start(arch, False, False, 0)
        return row

    def _archived_row(self, p):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        sub = f"closed {p.get('closed') or '—'}"
        btn = self._proj_button(p['name'], sub)
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
        btn = Gtk.Button()
        btn.get_style_context().add_class('proj-btn')
        btn.get_style_context().add_class('add-btn')
        lbl = Gtk.Label(label=f'＋  {name}')
        lbl.get_style_context().add_class('proj-name')
        lbl.set_xalign(0)
        btn.add(lbl)
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

    def _open(self, name):
        # Point current-project at it, bump lastOpened, then launch detached
        # so the workspace switch survives this popup being destroyed.
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
