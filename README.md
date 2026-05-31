# crew-quarters

Personal dotfiles + Claude Code agent crew (Jeeves, Watson, Friday). Portable across **Arch Linux / Hyprland** and **macOS**. Andromeda theme throughout.

---

## Quick setup

### macOS
```bash
git clone git@github.com:raymondshiner/crew-quarters.git ~/crew-quarters
cd ~/crew-quarters
./bootstrap-mac.sh
claude --login
```

### Arch / CachyOS
```bash
git clone git@github.com:raymondshiner/crew-quarters.git ~/crew-quarters
cd ~/crew-quarters
./bootstrap-linux.sh
claude --login
```

Both scripts are idempotent — safe to re-run.

---

## What it sets up

**Claude Code**
- `~/CLAUDE.md` — main instructions
- `~/.config/claude/machine.md` — platform-specific stack details (linked to `claude/machine.{linux,mac}.md`)
- `~/.claude/agents/{jeeves,friday}.md` — the two agents
- `~/.claude/settings.json` — permissions, hooks, statusline (rendered from `claude/settings.template.json` with the local `$HOME`)
- `~/.claude/hooks/notify-stop.sh` — banner when Claude finishes a turn (swaync on Linux, Notification Center on Mac)
- `~/.local/bin/{jeeves,friday,cc-statusline.sh}` — agent wrappers + Andromeda statusline

**Desktop (Linux)**
- Hyprland, waybar, swaync, dunst, kitty, fish

**Desktop (macOS)**
- AeroSpace (tiling WM), SketchyBar (status bar), Raycast, Karabiner-Elements, kitty, VS Code

---

## Layout

```
crew-quarters/
├── bootstrap-mac.sh           # macOS installer
├── bootstrap-linux.sh         # Arch installer
├── claude/                    # Claude Code config (portable)
│   ├── CLAUDE.md
│   ├── agents/{jeeves,watson,friday}.md
│   ├── hooks/notify-stop-{linux,mac}.sh
│   ├── bin/{jeeves,friday,cc-statusline.sh}
│   ├── machine.{linux,mac}.md
│   ├── settings.template.json
│   └── memory/                # seeded into ~/.claude/projects/.../memory/
├── hypr/, waybar/, swaync/, dunst/, fish/, greetd/    # Linux configs
├── kitty/, vscode/                                     # Cross-platform
└── mac/{aerospace,sketchybar,karabiner}/               # macOS configs (placeholders)
```

---

## How edits flow

Live system files are **symlinks into this repo**. Edit inside `~/crew-quarters/`, reload the relevant service, commit, push.

```bash
# Edit
nvim ~/crew-quarters/hypr/hyprland.conf

# Reload (per machine.md)
hyprctl reload                     # Linux
# or: aerospace reload-config      # macOS

# Commit
cd ~/crew-quarters && git add -A && git commit -m "tweak: ..." && git push
```

---

## Adding a new machine

1. SSH key → GitHub (`ssh-keygen -t ed25519 && gh ssh-key add ~/.ssh/id_ed25519.pub`)
2. `git clone git@github.com:raymondshiner/crew-quarters.git ~/crew-quarters`
3. Run the appropriate bootstrap script
4. `claude --login`

Done.
