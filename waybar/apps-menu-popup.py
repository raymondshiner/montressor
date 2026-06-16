#!/usr/bin/env python3
"""Andromeda apps-menu popup — start-menu-style launcher anchored to waybar.

- Live-filter search (Enter launches top match)
- Favorites row at top, click to launch, right-click to unpin
- All-apps list, click to launch, right-click to pin
- Favorites persist in ~/.config/waybar/apps-menu-favorites.json
"""
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, Gio, GLib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import popup_lib

PID_FILE = '/tmp/apps-menu-popup.pid'
FAVS_FILE = os.path.expanduser('~/.config/waybar/apps-menu-favorites.json')
POPUP_WIDTH = 380 + 16
POPUP_HEIGHT = 520

# Reasonable defaults if no favorites file exists yet.
DEFAULT_FAVS = [
    'google-chrome.desktop',
    'kitty.desktop',
    'obsidian.desktop',
    'firefox.desktop',
    'org.mozilla.firefox.desktop',
    'brave-browser.desktop',
]

# Category buckets — first matching key (case-insensitive substring) wins.
# Order matters: more specific buckets come first.
CATEGORIES = [
    ('Web',       ['WebBrowser']),
    ('Dev',       ['Development', 'IDE', 'Building']),
    ('Media',     ['AudioVideo', 'Audio', 'Video', 'Player', 'Music', 'TV', 'Mixer']),
    ('Office',    ['Office', 'Finance', 'Chat']),
    ('Network',   ['Network', 'FileTransfer', 'P2P']),
    ('Settings',  ['HardwareSettings', 'DesktopSettings', 'Settings', 'Printing']),
    ('System',    ['System', 'Filesystem', 'FileManager', 'TerminalEmulator', 'Monitor']),
    ('Utilities', ['Utility', 'TextEditor', 'Maps']),
]
CATEGORY_ORDER = [name for name, _ in CATEGORIES] + ['Other']


def categorize(info):
    cats = info.get_categories() or ''
    # Chrome PWAs ship with empty categories — bucket them as Web.
    if not cats.strip() and info.get_id().startswith('chrome-'):
        return 'Web'
    parts = [c.strip() for c in cats.split(';') if c.strip()]
    for bucket, keys in CATEGORIES:
        for p in parts:
            if p in keys:
                return bucket
    return 'Other'


CSS = """
window { background: transparent; }
.popup-inner {
    background-color: rgba(28, 30, 38, 0.97);
    border-radius: 10px;
    margin: 8px;
    padding: 16px;
    box-shadow:
        0 28px 28px rgba(0, 0, 0, 0.8),
        0 20px 20px rgba(0, 232, 198, 0.40),
        0 40px 40px rgba(0, 232, 198, 0.18);
}
.section-label {
    color: #677691;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 11px;
    margin-top: 8px;
    margin-bottom: 6px;
}
entry.search {
    background-color: #23262E;
    color: #D5CED9;
    border: 1px solid #2A2D3A;
    border-radius: 6px;
    padding: 6px 10px;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 13px;
}
entry.search:focus {
    border-color: #00E8C6;
}
.fav-btn {
    background: transparent;
    background-image: none;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 6px;
    box-shadow: none;
    text-shadow: none;
}
.fav-btn:hover {
    background-color: rgba(0, 232, 198, 0.10);
    border-color: rgba(0, 232, 198, 0.30);
}
.chip {
    background: transparent;
    background-image: none;
    color: #677691;
    border: 1px solid #2A2D3A;
    border-radius: 12px;
    padding: 2px 10px;
    margin: 0 4px 0 0;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 11px;
    box-shadow: none;
    text-shadow: none;
}
.chip:hover {
    color: #D5CED9;
    border-color: #00E8C6;
}
.chip.active {
    color: #00E8C6;
    border-color: #00E8C6;
    background-color: rgba(0, 232, 198, 0.12);
}
.app-row {
    background: transparent;
    background-image: none;
    color: #D5CED9;
    border: none;
    border-radius: 6px;
    padding: 6px 8px;
    box-shadow: none;
    text-shadow: none;
}
.app-row:hover {
    background-color: rgba(0, 232, 198, 0.10);
}
.app-row.top-match {
    background-color: rgba(0, 232, 198, 0.16);
}
.app-name {
    color: #D5CED9;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 13px;
}
.empty {
    color: #677691;
    font-size: 12px;
    padding: 8px;
}
scrolledwindow undershoot, scrolledwindow overshoot { background: none; }
scrollbar { background: transparent; }
scrollbar slider {
    background-color: rgba(103, 118, 145, 0.5);
    border-radius: 4px;
    min-width: 6px;
    min-height: 30px;
}
scrollbar slider:hover { background-color: rgba(0, 232, 198, 0.6); }
.divider {
    background-color: #2A2D3A;
    min-height: 1px;
    margin-top: 8px;
    margin-bottom: 4px;
}
"""


def load_favs():
    try:
        with open(FAVS_FILE) as f:
            data = json.load(f)
        if isinstance(data, list):
            return [str(x) for x in data]
    except (OSError, ValueError):
        pass
    return list(DEFAULT_FAVS)


def save_favs(favs):
    os.makedirs(os.path.dirname(FAVS_FILE), exist_ok=True)
    with open(FAVS_FILE, 'w') as f:
        json.dump(favs, f, indent=2)


def all_apps():
    """Return list of Gio.DesktopAppInfo, sorted by display name."""
    apps = []
    for info in Gio.AppInfo.get_all():
        if not isinstance(info, Gio.DesktopAppInfo):
            continue
        if info.get_nodisplay():
            continue
        if not info.should_show():
            continue
        apps.append(info)
    apps.sort(key=lambda a: (a.get_display_name() or '').lower())
    return apps


def icon_image(info, size):
    icon = info.get_icon()
    img = Gtk.Image()
    if icon:
        img.set_from_gicon(icon, Gtk.IconSize.DIALOG)
    img.set_pixel_size(size)
    return img


def launch(info):
    try:
        info.launch_uris_as_manager(
            [], None,
            GLib.SpawnFlags.SEARCH_PATH,
            None, None, None, None,
        )
    except Exception:
        # Fallback: spawn detached via Exec line stripped of field codes.
        cmd = info.get_commandline() or ''
        if cmd:
            import shlex, re
            cmd = re.sub(r'%[fFuUdDnNickvm]', '', cmd).strip()
            try:
                GLib.spawn_command_line_async(cmd)
            except Exception:
                pass


class AppsMenu(Gtk.Window):
    def __init__(self):
        super().__init__()

        popup_lib.setup_window(self)

        provider = Gtk.CssProvider()
        provider.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        blocker = popup_lib.wrap_with_click_outside(self, POPUP_WIDTH)

        self._favs = load_favs()
        self._apps = all_apps()
        self._by_id = {a.get_id(): a for a in self._apps}
        self._cat_of = {a.get_id(): categorize(a) for a in self._apps}
        # Only show category chips that actually have apps.
        present_cats = {self._cat_of[a.get_id()] for a in self._apps}
        self._chip_cats = ['All'] + [c for c in CATEGORY_ORDER if c in present_cats]
        self._active_chip = 'All'
        self._chip_buttons = {}
        self._filtered = list(self._apps)
        self._row_widgets = []  # list of (button, info)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.get_style_context().add_class('popup-inner')
        root.set_size_request(380, POPUP_HEIGHT)
        blocker.add(root)

        # --- Search ---
        self._entry = Gtk.Entry()
        self._entry.get_style_context().add_class('search')
        self._entry.set_placeholder_text('Search apps…')
        self._entry.connect('changed', self._on_search_changed)
        self._entry.connect('activate', self._on_search_activate)
        self._entry.connect('key-press-event', self._on_entry_key)
        root.pack_start(self._entry, False, False, 0)

        # --- Favorites ---
        self._fav_label = Gtk.Label(label='FAVORITES')
        self._fav_label.get_style_context().add_class('section-label')
        self._fav_label.set_xalign(0)
        root.pack_start(self._fav_label, False, False, 0)

        self._fav_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        root.pack_start(self._fav_box, False, False, 0)
        self._render_favorites()

        div = Gtk.Box()
        div.get_style_context().add_class('divider')
        root.pack_start(div, False, False, 0)

        # --- Category chips ---
        chip_scroll = Gtk.ScrolledWindow()
        chip_scroll.set_policy(Gtk.PolicyType.EXTERNAL, Gtk.PolicyType.NEVER)
        chip_scroll.set_size_request(-1, 28)
        chip_scroll.set_margin_top(4)
        chip_scroll.set_margin_bottom(2)
        chip_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        for cat in self._chip_cats:
            btn = Gtk.Button(label=cat)
            btn.get_style_context().add_class('chip')
            if cat == self._active_chip:
                btn.get_style_context().add_class('active')
            btn.connect('clicked', self._on_chip, cat)
            self._chip_buttons[cat] = btn
            chip_row.pack_start(btn, False, False, 0)
        chip_scroll.add(chip_row)
        root.pack_start(chip_scroll, False, False, 0)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        root.pack_start(scrolled, True, True, 0)

        self._list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        scrolled.add(self._list_box)
        self._render_app_list()

        self.connect('key-press-event', self._on_key)
        self.show_all()
        self.present()
        # Focus search so typing starts filtering immediately.
        GLib.idle_add(self._entry.grab_focus)

    # ---------- rendering ----------
    def _render_favorites(self):
        for child in self._fav_box.get_children():
            self._fav_box.remove(child)
        any_shown = False
        for fav_id in self._favs:
            info = self._by_id.get(fav_id)
            if not info:
                continue
            any_shown = True
            btn = Gtk.Button()
            btn.get_style_context().add_class('fav-btn')
            btn.add(icon_image(info, 32))
            btn.set_tooltip_text(info.get_display_name() or fav_id)
            btn.connect('clicked', self._on_launch, info)
            btn.connect('button-press-event', self._on_fav_press, fav_id)
            self._fav_box.pack_start(btn, False, False, 0)
        if not any_shown:
            empty = Gtk.Label(label='Right-click any app below to pin it here.')
            empty.get_style_context().add_class('empty')
            empty.set_xalign(0)
            self._fav_box.pack_start(empty, False, False, 0)
        self._fav_box.show_all()

    def _render_app_list(self):
        for child in self._list_box.get_children():
            self._list_box.remove(child)
        self._row_widgets = []
        if not self._filtered:
            empty = Gtk.Label(label='No matches.')
            empty.get_style_context().add_class('empty')
            empty.set_xalign(0)
            self._list_box.pack_start(empty, False, False, 0)
        else:
            for i, info in enumerate(self._filtered):
                btn = Gtk.Button()
                btn.get_style_context().add_class('app-row')
                if i == 0 and self._entry.get_text().strip():
                    btn.get_style_context().add_class('top-match')
                row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
                row.pack_start(icon_image(info, 22), False, False, 0)
                name = Gtk.Label(label=info.get_display_name() or info.get_id())
                name.get_style_context().add_class('app-name')
                name.set_xalign(0)
                row.pack_start(name, True, True, 0)
                btn.add(row)
                btn.connect('clicked', self._on_launch, info)
                btn.connect('button-press-event', self._on_app_press, info)
                self._list_box.pack_start(btn, False, False, 0)
                self._row_widgets.append((btn, info))
        self._list_box.show_all()

    # ---------- handlers ----------
    def _recompute_filter(self):
        q = self._entry.get_text().strip().lower()
        # Search overrides chip filter (search across all apps).
        if q:
            scored = []
            for a in self._apps:
                name = (a.get_display_name() or '').lower()
                gname = (a.get_generic_name() or '').lower()
                kw = ' '.join(a.get_keywords() or []).lower()
                hay = f'{name} {gname} {kw}'
                if q in hay:
                    score = 0 if name.startswith(q) else (1 if q in name else 2)
                    scored.append((score, name, a))
            scored.sort(key=lambda t: (t[0], t[1]))
            self._filtered = [t[2] for t in scored]
        elif self._active_chip == 'All':
            self._filtered = list(self._apps)
        else:
            self._filtered = [a for a in self._apps
                              if self._cat_of[a.get_id()] == self._active_chip]
        self._render_app_list()

    def _on_search_changed(self, _entry):
        self._recompute_filter()

    def _on_chip(self, _btn, cat):
        self._active_chip = cat
        for name, b in self._chip_buttons.items():
            ctx = b.get_style_context()
            if name == cat:
                ctx.add_class('active')
            else:
                ctx.remove_class('active')
        self._recompute_filter()

    def _on_search_activate(self, _entry):
        if self._filtered:
            launch(self._filtered[0])
            self.destroy()

    def _on_entry_key(self, _entry, event):
        # Down arrow → focus the first row so keyboard nav works.
        if event.keyval == Gdk.KEY_Down and self._row_widgets:
            self._row_widgets[0][0].grab_focus()
            return True
        return False

    def _on_launch(self, _btn, info):
        launch(info)
        self.destroy()

    def _on_app_press(self, _btn, event, info):
        if event.button == 3:  # right-click → toggle pin
            self._toggle_fav(info.get_id())
            return True
        return False

    def _on_fav_press(self, _btn, event, fav_id):
        if event.button == 3:  # right-click → unpin
            self._toggle_fav(fav_id)
            return True
        return False

    def _toggle_fav(self, app_id):
        if not app_id:
            return
        if app_id in self._favs:
            self._favs.remove(app_id)
        else:
            self._favs.append(app_id)
        save_favs(self._favs)
        self._render_favorites()

    def _on_key(self, _w, event):
        if event.keyval == Gdk.KEY_Escape:
            self.destroy()


if __name__ == '__main__':
    popup_lib.run_popup(PID_FILE, AppsMenu)
