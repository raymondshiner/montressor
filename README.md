# crew-quarters

Personal dotfiles. Portable across **Arch Linux / Hyprland** and **macOS**. Andromeda theme throughout.

---

## Quick setup

### macOS
```bash
git clone git@github.com:raymondshiner/crew-quarters.git ~/crew-quarters
cd ~/crew-quarters
./bootstrap-mac.sh
```

### Arch / CachyOS
```bash
git clone git@github.com:raymondshiner/crew-quarters.git ~/crew-quarters
cd ~/crew-quarters
./bootstrap-linux.sh
```

Both scripts are idempotent — safe to re-run.

---

## What it sets up

**Desktop (Linux)**
- Hyprland, waybar, swaync, dunst, kitty, fish, walker

**Desktop (macOS)**
- AeroSpace (tiling WM), SketchyBar (status bar), Karabiner-Elements, kitty, VS Code

---

## Layout

```
crew-quarters/
├── bootstrap-mac.sh           # macOS installer
├── bootstrap-linux.sh         # Arch installer
├── hypr/, waybar/, swaync/, dunst/, fish/, greetd/, walker/   # Linux configs
├── kitty/, vscode/                                            # Cross-platform
├── mac/{aerospace,sketchybar,karabiner}/                      # macOS configs
├── local-bin/                                                 # Helper scripts
├── packages/                                                  # Package snapshots
└── zsh/                                                       # Shell config
```

---

## How edits flow

Live system files are **symlinks into this repo**. Edit inside `~/crew-quarters/`, reload the relevant service, commit, push.

```bash
nvim ~/crew-quarters/hypr/hyprland.conf
hyprctl reload                     # Linux
# or: aerospace reload-config      # macOS

cd ~/crew-quarters && git add -A && git commit -m "tweak: ..." && git push
```

---

## Adding a new machine

1. SSH key → GitHub (`ssh-keygen -t ed25519 && gh ssh-key add ~/.ssh/id_ed25519.pub`)
2. `git clone git@github.com:raymondshiner/crew-quarters.git ~/crew-quarters`
3. Run the appropriate bootstrap script
