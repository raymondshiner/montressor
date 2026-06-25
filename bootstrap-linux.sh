#!/usr/bin/env bash
# Bootstrap a fresh Arch/CachyOS machine to "Jarvis + Friday ready".
# Mirror of bootstrap-mac.sh — same agent setup, native Linux tooling.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRIVATE_REPO_DIR="${PRIVATE_REPO_DIR:-$HOME/avengers}"
PRIVATE_REPO_URL="git@github.com:raymondshiner/avengers.git"
CYAN=$'\033[38;2;0;232;198m'
MUTED=$'\033[38;2;103;118;145m'
GREEN=$'\033[38;2;168;255;96m'
RED=$'\033[38;2;238;93;67m'
RESET=$'\033[0m'

say()  { printf "${CYAN}==>${RESET} %s\n" "$1"; }
note() { printf "${MUTED}    %s${RESET}\n" "$1"; }
ok()   { printf "${GREEN}    ✓ %s${RESET}\n" "$1"; }
warn() { printf "${RED}    ! %s${RESET}\n" "$1"; }

if [[ "$(uname -s)" != "Linux" ]]; then
  warn "This script is for Linux. Use bootstrap-mac.sh on macOS."
  exit 1
fi
if ! command -v pacman >/dev/null 2>&1; then
  warn "This script targets Arch / CachyOS. Adapt for other distros."
  exit 1
fi

# ----------------------------------------------------------------------
# 1. Packages
# ----------------------------------------------------------------------
say "Installing seed CLI tools (pacman)..."
SEED_PKGS=(git github-cli jq fzf ripgrep fd nodejs npm neovim zsh libnotify base-devel)
sudo pacman -S --needed --noconfirm "${SEED_PKGS[@]}"

if [[ -s "$REPO_DIR/packages/pacman.txt" ]]; then
  say "Installing native packages from packages/pacman.txt..."
  # shellcheck disable=SC2046
  sudo pacman -S --needed --noconfirm $(grep -v '^\s*\(#\|$\)' "$REPO_DIR/packages/pacman.txt") || \
    warn "some pacman packages failed — check above"
fi

say "Ensuring yay (AUR helper) is installed..."
if ! command -v yay >/dev/null 2>&1; then
  tmp="$(mktemp -d)"
  git clone https://aur.archlinux.org/yay-bin.git "$tmp/yay-bin"
  ( cd "$tmp/yay-bin" && makepkg -si --noconfirm )
  rm -rf "$tmp"
else
  ok "yay"
fi

if [[ -s "$REPO_DIR/packages/aur.txt" ]]; then
  say "Installing AUR packages from packages/aur.txt..."
  # shellcheck disable=SC2046
  yay -S --needed --noconfirm $(grep -v '^\s*\(#\|$\)' "$REPO_DIR/packages/aur.txt") || \
    warn "some AUR packages failed — check above"
fi

say "Installing Claude Code..."
if ! command -v claude >/dev/null 2>&1; then
  sudo npm install -g @anthropic-ai/claude-code
else
  ok "claude"
fi

# ----------------------------------------------------------------------
# 1b. Private companion repo (agents, prompts, hooks, memory)
# ----------------------------------------------------------------------
say "Ensuring private repo at $PRIVATE_REPO_DIR..."
if [[ ! -d "$PRIVATE_REPO_DIR/.git" ]]; then
  if ! git clone "$PRIVATE_REPO_URL" "$PRIVATE_REPO_DIR"; then
    warn "Failed to clone $PRIVATE_REPO_URL"
    warn "Add your SSH key to GitHub (gh ssh-key add ~/.ssh/id_ed25519.pub) and re-run."
    exit 1
  fi
else
  ok "$PRIVATE_REPO_DIR"
fi

# ----------------------------------------------------------------------
# 2. Directories
# ----------------------------------------------------------------------
say "Creating config directories..."
mkdir -p "$HOME/.claude/agents" \
         "$HOME/.claude/hooks" \
         "$HOME/.local/bin" \
         "$HOME/.config/claude" \
         "$HOME/.config/kitty" \
         "$HOME/.config/hypr" \
         "$HOME/.config/waybar" \
         "$HOME/.config/swaync" \
         "$HOME/.config/dunst" \
         "$HOME/.config/fish" \
         "$HOME/.config/Code/User" \
         "$HOME/.kodi/userdata"

# ----------------------------------------------------------------------
# 3. Symlinks
# ----------------------------------------------------------------------
say "Symlinking config files..."
link() {
  local src="$1" dst="$2"
  if [[ -e "$dst" && ! -L "$dst" ]]; then
    mv "$dst" "$dst.bak.$(date +%s)"
    warn "backed up existing $dst → $dst.bak.*"
  fi
  ln -sfn "$src" "$dst"
  ok "$dst"
}

link "$PRIVATE_REPO_DIR/claude/CLAUDE.md"                  "$HOME/CLAUDE.md"
link "$PRIVATE_REPO_DIR/claude/agents/jarvis.md"           "$HOME/.claude/agents/jarvis.md"
link "$PRIVATE_REPO_DIR/claude/agents/friday.md"           "$HOME/.claude/agents/friday.md"
link "$PRIVATE_REPO_DIR/claude/agents/smith.md"            "$HOME/.claude/agents/smith.md"
link "$PRIVATE_REPO_DIR/claude/hooks/notify-stop-linux.sh" "$HOME/.claude/hooks/notify-stop.sh"
link "$PRIVATE_REPO_DIR/claude/bin/cc-statusline.sh"       "$HOME/.local/bin/cc-statusline.sh"
link "$PRIVATE_REPO_DIR/claude/bin/jarvis"                 "$HOME/.local/bin/jarvis"
link "$PRIVATE_REPO_DIR/claude/bin/friday"                 "$HOME/.local/bin/friday"
link "$PRIVATE_REPO_DIR/claude/bin/smith"                  "$HOME/.local/bin/smith"
link "$PRIVATE_REPO_DIR/claude/bin/smith-init"             "$HOME/.local/bin/smith-init"
link "$PRIVATE_REPO_DIR/claude/bin/launch"                 "$HOME/.local/bin/launch"
link "$PRIVATE_REPO_DIR/claude/machine.linux.md"           "$HOME/.config/claude/machine.md"

[[ -d "$REPO_DIR/hypr"     ]] && for f in "$REPO_DIR"/hypr/*;    do link "$f" "$HOME/.config/hypr/$(basename "$f")";    done
[[ -d "$REPO_DIR/waybar"   ]] && for f in "$REPO_DIR"/waybar/*;  do link "$f" "$HOME/.config/waybar/$(basename "$f")";  done
[[ -d "$REPO_DIR/swaync"   ]] && for f in "$REPO_DIR"/swaync/*;  do link "$f" "$HOME/.config/swaync/$(basename "$f")";  done
[[ -d "$REPO_DIR/dunst"    ]] && for f in "$REPO_DIR"/dunst/*;   do link "$f" "$HOME/.config/dunst/$(basename "$f")";   done
[[ -d "$REPO_DIR/fish"     ]] && for f in "$REPO_DIR"/fish/*;    do link "$f" "$HOME/.config/fish/$(basename "$f")";    done
[[ -f "$REPO_DIR/kitty/kitty.conf"             ]] && link "$REPO_DIR/kitty/kitty.conf"             "$HOME/.config/kitty/kitty.conf"
[[ -f "$REPO_DIR/vscode/settings.json"         ]] && link "$REPO_DIR/vscode/settings.json"         "$HOME/.config/Code/User/settings.json"
[[ -f "$REPO_DIR/kodi/playercorefactory.xml"   ]] && link "$REPO_DIR/kodi/playercorefactory.xml"   "$HOME/.kodi/userdata/playercorefactory.xml"
[[ -f "$REPO_DIR/zsh/zshrc"                    ]] && link "$REPO_DIR/zsh/zshrc"                    "$HOME/.zshrc"

[[ -f "$REPO_DIR/walker/config.toml"           ]] && link "$REPO_DIR/walker/config.toml"           "$HOME/.config/walker/config.toml"
[[ -d "$REPO_DIR/walker/themes/andromeda"      ]] && link "$REPO_DIR/walker/themes/andromeda"      "$HOME/.config/walker/themes/andromeda"
[[ -f "$REPO_DIR/systemd-user/elephant.service" ]] && link "$REPO_DIR/systemd-user/elephant.service" "$HOME/.config/systemd/user/elephant.service"
[[ -f "$REPO_DIR/systemd-user/walker.service"  ]] && link "$REPO_DIR/systemd-user/walker.service"  "$HOME/.config/systemd/user/walker.service"

chmod +x "$PRIVATE_REPO_DIR/claude/hooks/notify-stop-linux.sh" \
         "$PRIVATE_REPO_DIR/claude/bin/cc-statusline.sh" \
         "$PRIVATE_REPO_DIR/claude/bin/jarvis" \
         "$PRIVATE_REPO_DIR/claude/bin/friday" \
         "$PRIVATE_REPO_DIR/claude/bin/smith" \
         "$PRIVATE_REPO_DIR/claude/bin/smith-init" \
         "$PRIVATE_REPO_DIR/claude/bin/launch"

# ----------------------------------------------------------------------
# 4. Render settings.json template
# ----------------------------------------------------------------------
say "Rendering Claude settings.json..."
sed "s|__HOME__|$HOME|g" "$PRIVATE_REPO_DIR/claude/settings.template.json" > "$HOME/.claude/settings.json"
ok "$HOME/.claude/settings.json"

# ----------------------------------------------------------------------
# 4b. Ensure ~/src exists (Smith's home; per-agent MCPs live in smith.md)
# ----------------------------------------------------------------------
mkdir -p "$HOME/src"
link "$PRIVATE_REPO_DIR/claude/SRC.md" "$HOME/src/CLAUDE.md"

# ----------------------------------------------------------------------
# 5. Seed memory files
# ----------------------------------------------------------------------
say "Seeding Claude memory..."
MEM_DIR="$HOME/.claude/projects/$(echo "$HOME" | sed 's|/|-|g')/memory"
mkdir -p "$MEM_DIR"
for f in "$PRIVATE_REPO_DIR"/claude/memory/*.md; do
  cp -n "$f" "$MEM_DIR/" 2>/dev/null || true
done
ok "$MEM_DIR"

# ----------------------------------------------------------------------
# 6. Final
# ----------------------------------------------------------------------
echo
say "Done. Next steps:"
note "1. Run:    claude --login"
note "2. Run:    gh auth login"
note "3. Reload Hyprland:    hyprctl reload"
note "4. Restart waybar:     pkill waybar && waybar &"
note "5. Type 'claude' — Jarvis is ready."
echo
