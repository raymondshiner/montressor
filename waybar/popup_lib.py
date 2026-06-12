"""Shared scaffolding for Andromeda waybar popups.

Each popup is a single full-screen layer-shell overlay window that:
  - Centers its body horizontally under the bar icon that triggered it
    (using hyprctl cursorpos as the click point).
  - Sets a Wayland input region that EXCLUDES the waybar strip at the top
    of the screen, so clicks on other bar icons still reach waybar and
    can open a different popup in one click.
  - Catches clicks anywhere else (the desktop below the bar) and dismisses
    via the outer EventBox.
  - Blocks clicks on the popup body itself so they don't bubble up.
  - On launch, SIGTERMs any other popup that's currently open so only one
    is on screen at a time.
"""
import os
import signal
import subprocess
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
from gi.repository import Gtk, Gdk, GtkLayerShell
import cairo

WAYBAR_HEIGHT = 38

# Every popup script writes to one of these. Update this list whenever you
# add a new popup so click-switching keeps working.
ALL_POPUP_PIDS = (
    '/tmp/battery-popup.pid',
    '/tmp/drives-popup.pid',
    '/tmp/bluetooth-popup.pid',
    '/tmp/sound-popup.pid',
    '/tmp/calendar-popup.pid',
    '/tmp/workspace-popup.pid',
)


def kill_other_popups(own_pid_file):
    for pf in ALL_POPUP_PIDS:
        if pf == own_pid_file or not os.path.exists(pf):
            continue
        try:
            pid = int(open(pf).read().strip())
            os.kill(pid, signal.SIGTERM)
        except (ProcessLookupError, ValueError, OSError):
            pass
        try:
            os.remove(pf)
        except OSError:
            pass


def get_cursor_x():
    try:
        out = subprocess.check_output(['hyprctl', 'cursorpos'],
                                      text=True, timeout=0.5).strip()
        # Format: "1599, 996"
        return int(out.split(',')[0].strip())
    except Exception:
        return None


def _monitor_for_cursor(cursor_x):
    """Pick the monitor containing cursor_x. Falls back to monitor 0."""
    display = Gdk.Display.get_default()
    if not display:
        return None
    n = display.get_n_monitors()
    if cursor_x is not None:
        for i in range(n):
            m = display.get_monitor(i)
            g = m.get_geometry()
            if g.x <= cursor_x < g.x + g.width:
                return m
    return display.get_monitor(0) if n else None


def setup_window(window):
    """Full-screen overlay layer-shell window with RGBA visual."""
    window.set_decorated(False)
    screen = window.get_screen()
    visual = screen.get_rgba_visual()
    if visual:
        window.set_visual(visual)

    GtkLayerShell.init_for_window(window)
    GtkLayerShell.set_layer(window, GtkLayerShell.Layer.OVERLAY)
    for edge in (GtkLayerShell.Edge.TOP, GtkLayerShell.Edge.RIGHT,
                 GtkLayerShell.Edge.BOTTOM, GtkLayerShell.Edge.LEFT):
        GtkLayerShell.set_anchor(window, edge, True)
    # -1 = ignore other surfaces' exclusive zones, so our overlay actually
    # spans y=0 → screen height (otherwise waybar's exclusive zone shifts
    # everything down by WAYBAR_HEIGHT and the popup floats below the bar).
    GtkLayerShell.set_exclusive_zone(window, -1)
    GtkLayerShell.set_keyboard_mode(window, GtkLayerShell.KeyboardMode.ON_DEMAND)


def wrap_with_click_outside(window, popup_width, center=False):
    """Add catcher/positioner/blocker chain to `window`. Returns the blocker
    EventBox — caller adds their popup-inner Box to it.

    popup_width is the visible width including the .popup-inner CSS margins
    (typically size_request_width + 16).

    If center=True, the popup is centered on the active monitor (both axes)
    instead of being anchored under the cursor below the bar.
    """
    cursor_x = get_cursor_x()
    monitor = _monitor_for_cursor(cursor_x)
    if monitor:
        geo = monitor.get_geometry()
        screen_x0 = geo.x
        screen_w = geo.width
    else:
        screen_x0 = 0
        screen_w = 1920

    catcher = Gtk.EventBox()
    catcher.connect('button-press-event', lambda *_: window.destroy() or True)
    window.add(catcher)

    positioner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
    if center:
        positioner.set_valign(Gtk.Align.CENTER)
        positioner.set_halign(Gtk.Align.CENTER)
    else:
        positioner.set_valign(Gtk.Align.START)
        # WAYBAR_HEIGHT - 12: positioner sits 12px below bar top, then the
        # .popup-inner CSS margin (8px) lifts the visible body to y=34, giving
        # a 4px overlap with the bar so the popup feels attached.
        positioner.set_margin_top(WAYBAR_HEIGHT - 12)

        if cursor_x is None:
            positioner.set_halign(Gtk.Align.END)
            positioner.set_margin_end(2)
        else:
            # Clamp so the popup never spills off the active monitor
            local_x = cursor_x - screen_x0
            margin_left = max(2, min(screen_w - popup_width - 2,
                                      local_x - popup_width // 2))
            positioner.set_halign(Gtk.Align.START)
            positioner.set_margin_start(margin_left)
    catcher.add(positioner)

    blocker = Gtk.EventBox()
    blocker.connect('button-press-event', lambda *_: True)
    positioner.pack_start(blocker, False, False, 0)

    def _apply_input_region(*_):
        gdkwin = window.get_window()
        if not gdkwin:
            return False
        mon = (Gdk.Display.get_default().get_monitor_at_window(gdkwin)
               or monitor)
        if not mon:
            return False
        g = mon.get_geometry()
        # Below-bar strip: catches dismissals from clicks on the desktop.
        # Waybar strip itself is excluded so other icons still work.
        region = cairo.Region(
            cairo.RectangleInt(0, WAYBAR_HEIGHT, g.width,
                               max(1, g.height - WAYBAR_HEIGHT))
        )
        # Add the popup body — without this, the 4px popup→bar overlap
        # wouldn't accept clicks and they'd fall through to waybar.
        alloc = blocker.get_allocation()
        if alloc.width > 0 and alloc.height > 0:
            region.union(cairo.RectangleInt(alloc.x, alloc.y,
                                            alloc.width, alloc.height))
        gdkwin.input_shape_combine_region(region, 0, 0)
        return False

    window.connect('map-event', _apply_input_region)
    window.connect('size-allocate', _apply_input_region)

    return blocker


def run_popup(pid_file, build_window):
    """Standard main(): PID-toggle, kill-other-popups, then run.

    build_window() should return a Gtk.Window ready to show.
    """
    if os.path.exists(pid_file):
        try:
            pid = int(open(pid_file).read().strip())
            os.kill(pid, signal.SIGTERM)
            try: os.remove(pid_file)
            except OSError: pass
            return
        except (ProcessLookupError, ValueError, OSError):
            try: os.remove(pid_file)
            except OSError: pass

    kill_other_popups(pid_file)

    with open(pid_file, 'w') as f:
        f.write(str(os.getpid()))

    def _cleanup():
        try: os.remove(pid_file)
        except OSError: pass

    win = build_window()
    win.connect('destroy', lambda _w: _cleanup() or Gtk.main_quit())
    Gtk.main()
