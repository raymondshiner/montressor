# moonlander

Source-of-truth for the ZSA Moonlander keymap on `sirlexicon-laptop`.

The keymap lives here in git. QMK builds it locally. `kontroll` flashes it. Oryx is no longer in the loop.

## Layout

```
~/montressor/moonlander/
├── keymap/                 # QMK keymap source (keymap.c, rules.mk, config.h, rgb.c, ...)
├── firmware/               # built .bin lands here (gitignored)
└── Makefile                # link / compile / flash wrappers
```

The keymap directory is symlinked into `~/qmk_firmware/keyboards/zsa/moonlander/keymaps/sirlexicon` so QMK sees it at compile time.

## One-time setup

Already done by Jarvis on this machine:

- `pacman -S qmk` — CLI + toolchain
- `yay -S zsa-kontroll-bin` — `kontroll` CLI for flashing
- `git clone --depth 1 https://github.com/zsa/qmk_firmware ~/qmk_firmware`
- `qmk config user.qmk_home=~/qmk_firmware`

## Seeding the keymap from Oryx

1. Open your Moonlander layout in Oryx.
2. Top right → **Download** → **Source code** (`.zip`).
3. Unzip. Inside you'll find `<layout-name>/` containing `keymap.c`, `rules.mk`, `config.h`, possibly `rgb.c`.
4. Copy the contents into `~/montressor/moonlander/keymap/` (overwrite the `.gitkeep`).
5. `cd ~/montressor/moonlander && make compile` — should produce `firmware/sirlexicon.bin`.
6. `make flash` — `kontroll` waits for the board's reset combo (Moonlander: hold the small reset button on the top-left of the right half until both LEDs go red).
7. `dots "seed moonlander keymap from oryx"`

## Day-to-day

```bash
cd ~/montressor/moonlander

make status     # show paths + tool versions
make compile    # build only
make flash      # build + flash
make clean      # nuke build artefacts
```

When Jarvis edits `keymap/keymap.c` (keys) or `keymap/rgb.c` (per-layer colors), the flow is:

1. Jarvis edits the file, runs `make compile`, confirms it builds.
2. You hit the reset combo on the board and `make flash`.
3. `dots "<short msg>"` autosyncs.

## Per-layer RGB

Oryx-exported Moonlander keymaps include a `ledmap` array — one RGB triple per key per layer. To recolor a key:

```c
// keymap/keymap.c or keymap/rgb.c
[LAYER_NAV] = { [KC_INDEX] = {0x00, 0xE8, 0xC6}, ... }
```

Andromeda palette (from `CLAUDE.md`) maps to:

| Role | Hex | RGB |
|---|---|---|
| Cyan (active/super) | `#00E8C6` | `0, 232, 198` |
| Green (good) | `#A8FF60` | `168, 255, 96` |
| Yellow (warn) | `#FFE66D` | `255, 230, 109` |
| Red (critical) | `#EE5D43` | `238, 93, 67` |
| Purple (media) | `#B084EB` | `176, 132, 235` |
| Muted | `#677691` | `103, 118, 145` |
