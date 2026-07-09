#!/usr/bin/env bash
# Bootstrap a Linux install to "Jarvis-ready" — dual-boot aware.
#
#   CachyOS/Arch : pacman/yay flow — packages/pacman.txt + aur.txt
#   Ubuntu       : apt/snap flow  — packages/ubuntu-apt.txt + ubuntu-snap.txt
#                  + vendor apt repos (Chrome, VS Code, Mullvad, Brave)
#
# Idempotent — safe to re-run any time; on a converged system it's a no-op.
# Skip the (slow, sudo-heavy) package step:  BOOTSTRAP_SKIP_PKGS=1 ./bootstrap-linux.sh
# Mirror of bootstrap-mac.sh for the agent setup. Runbook for the full
# dual-boot migration: ~/jarvis/claude/desktop/ubuntu-migration-runbook.md

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRIVATE_REPO_DIR="${PRIVATE_REPO_DIR:-$HOME/jarvis}"
PRIVATE_REPO_URL="git@github.com:raymondshiner/jarvis.git"
CYAN=$'\033[38;2;0;232;198m'
MUTED=$'\033[38;2;103;118;145m'
GREEN=$'\033[38;2;168;255;96m'
RED=$'\033[38;2;238;93;67m'
RESET=$'\033[0m'

say()  { printf "${CYAN}==>${RESET} %s\n" "$1"; }
note() { printf "${MUTED}    %s${RESET}\n" "$1"; }
ok()   { printf "${GREEN}    ✓ %s${RESET}\n" "$1"; }
warn() { printf "${RED}    ! %s${RESET}\n" "$1"; }
die()  { warn "$1"; exit 1; }

# ----------------------------------------------------------------------
# 0. OS detection + /shared guard
# ----------------------------------------------------------------------
[[ "$(uname -s)" == "Linux" ]] || die "Linux only — use bootstrap-mac.sh on macOS."
[[ -r /etc/os-release ]] || die "/etc/os-release missing — can't detect distro."
OS_ID="$(. /etc/os-release && echo "$ID")"
case "$OS_ID" in
  cachyos|arch) OS_FLOW=arch ;;
  ubuntu)       OS_FLOW=ubuntu ;;
  *) die "Unsupported distro '$OS_ID' — this script handles cachyos/arch and ubuntu." ;;
esac
say "Distro: $OS_ID ($OS_FLOW flow)"

# The SHARED partition carries the whole ecosystem post-migration. If the
# partition exists but isn't mounted, DO NOT silently bootstrap a brainless
# home — fail loudly. fstab: LABEL=SHARED /shared ext4 noatime,nofail 0 2
SHARED_MODE=0
if [[ -e /dev/disk/by-label/SHARED ]]; then
  mountpoint -q /shared || die "SHARED partition exists but /shared is not mounted — fix fstab / 'sudo mount /shared' first."
  SHARED_MODE=1
  say "/shared is mounted — shared-ecosystem mode"
else
  note "no SHARED partition — pre-migration single-OS mode"
fi

# ----------------------------------------------------------------------
# 1. Shared-partition home symlinks (before anything touches ~/montressor)
# ----------------------------------------------------------------------
# $HOME/<x> → /shared/<x>. Never clobbers a real dir — migrating existing
# data into /shared is a manual, verified step (see the runbook).
link_shared() {
  local src="$1" dst="$2"
  [[ -e "$src" ]] || { warn "skip $dst — $src missing on /shared"; return 0; }
  if [[ -L "$dst" || ! -e "$dst" ]]; then
    mkdir -p "$(dirname "$dst")"
    ln -sfn "$src" "$dst"
    ok "$dst → $src"
  else
    warn "$dst is a real file/dir — migrate it manually (runbook Phase 2), skipping"
  fi
}
if [[ "$SHARED_MODE" == 1 ]]; then
  say "Linking shared ecosystem into \$HOME..."
  # research/lore/gear/comms/ledger ride INSIDE ~/jarvis (linked in the manifest)
  for d in jarvis montressor src Documents Pictures Media; do
    link_shared "/shared/$d" "$HOME/$d"
  done
  link_shared /shared/claude/projects "$HOME/.claude/projects"
  link_shared /shared/claude/plans    "$HOME/.claude/plans"
fi

# ----------------------------------------------------------------------
# 2. Packages (BOOTSTRAP_SKIP_PKGS=1 to skip)
# ----------------------------------------------------------------------
strip_comments() { grep -v '^\s*\(#\|$\)' "$1"; }

if [[ "${BOOTSTRAP_SKIP_PKGS:-0}" == 1 ]]; then
  say "Skipping package step (BOOTSTRAP_SKIP_PKGS=1)"
elif [[ "$OS_FLOW" == arch ]]; then
  say "Installing seed CLI tools (pacman)..."
  sudo pacman -S --needed --noconfirm git github-cli jq fzf ripgrep fd nodejs npm zsh libnotify base-devel

  if [[ -s "$REPO_DIR/packages/pacman.txt" ]]; then
    say "Installing native packages from packages/pacman.txt..."
    # shellcheck disable=SC2046
    sudo pacman -S --needed --noconfirm $(strip_comments "$REPO_DIR/packages/pacman.txt") || \
      warn "some pacman packages failed — check above"
  fi

  say "Ensuring yay (AUR helper)..."
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
    yay -S --needed --noconfirm $(strip_comments "$REPO_DIR/packages/aur.txt") || \
      warn "some AUR packages failed — check above"
  fi
else # ---------------------------------------------------------- ubuntu
  say "Installing seed CLI tools (apt)..."
  sudo apt update
  sudo apt install -y git gh jq fzf ripgrep fd-find zsh curl wget unzip \
    build-essential libnotify-bin ca-certificates

  # Ubuntu names fd's binary fdfind — shim it
  mkdir -p "$HOME/.local/bin"
  command -v fd >/dev/null 2>&1 || ln -sfn "$(command -v fdfind)" "$HOME/.local/bin/fd"

  say "Configuring vendor apt repos (Chrome, VS Code, Mullvad, Brave)..."
  sudo install -d -m 0755 /etc/apt/keyrings
  add_repo() { # <name> <key-url> <deb-line>  (keys used as-is; apt ≥2.4 reads .asc)
    local name="$1" key_url="$2" line="$3" list="/etc/apt/sources.list.d/$1.list"
    if [[ -f "$list" ]]; then ok "repo: $name (present)"; return 0; fi
    curl -fsSL "$key_url" | sudo tee "/etc/apt/keyrings/${key_url##*/}" >/dev/null
    echo "$line" | sudo tee "$list" >/dev/null
    ok "repo: $name"
  }
  UBU_CODENAME="$(. /etc/os-release && echo "$VERSION_CODENAME")"
  add_repo google-chrome https://dl.google.com/linux/linux_signing_key.pub \
    "deb [arch=amd64 signed-by=/etc/apt/keyrings/linux_signing_key.pub] https://dl.google.com/linux/chrome/deb/ stable main"
  add_repo vscode https://packages.microsoft.com/keys/microsoft.asc \
    "deb [arch=amd64 signed-by=/etc/apt/keyrings/microsoft.asc] https://packages.microsoft.com/repos/code stable main"
  # if apt update 404s on mullvad, drop codename to the previous LTS (see ubuntu-manual.md)
  add_repo mullvad https://repository.mullvad.net/deb/mullvad-keyring.asc \
    "deb [arch=amd64 signed-by=/etc/apt/keyrings/mullvad-keyring.asc] https://repository.mullvad.net/deb/stable $UBU_CODENAME main"
  add_repo brave-browser https://brave-browser-apt-release.s3.brave.com/brave-browser-archive-keyring.gpg \
    "deb [arch=amd64 signed-by=/etc/apt/keyrings/brave-browser-archive-keyring.gpg] https://brave-browser-apt-release.s3.brave.com/ stable main"
  sudo apt update

  if [[ -s "$REPO_DIR/packages/ubuntu-apt.txt" ]]; then
    say "Installing apt packages from packages/ubuntu-apt.txt..."
    # shellcheck disable=SC2046
    if ! sudo apt install -y $(strip_comments "$REPO_DIR/packages/ubuntu-apt.txt"); then
      warn "bulk install failed — retrying per package (unknown names become warnings)"
      while read -r p; do
        sudo apt install -y "$p" >/dev/null 2>&1 || warn "apt: $p failed"
      done < <(strip_comments "$REPO_DIR/packages/ubuntu-apt.txt")
    fi
  fi

  if [[ -s "$REPO_DIR/packages/ubuntu-snap.txt" ]]; then
    say "Installing snaps from packages/ubuntu-snap.txt..."
    while read -r s; do
      snap list "${s%% *}" >/dev/null 2>&1 && { ok "snap: ${s%% *}"; continue; }
      # shellcheck disable=SC2086
      sudo snap install $s || warn "snap: $s failed"
    done < <(strip_comments "$REPO_DIR/packages/ubuntu-snap.txt")
  fi

  if ! command -v nvidia-smi >/dev/null 2>&1; then
    say "Installing NVIDIA driver (ubuntu-drivers — never hand-pick debs)..."
    sudo ubuntu-drivers install || warn "ubuntu-drivers failed — run manually"
  fi

  if ! fc-list 2>/dev/null | grep -qi "JetBrainsMono Nerd"; then
    say "Installing JetBrains Mono Nerd Font..."
    tmp="$(mktemp -d)"
    curl -fsSLo "$tmp/JetBrainsMono.zip" \
      https://github.com/ryanoasis/nerd-fonts/releases/latest/download/JetBrainsMono.zip
    mkdir -p "$HOME/.local/share/fonts/JetBrainsMonoNerd"
    unzip -oq "$tmp/JetBrainsMono.zip" -d "$HOME/.local/share/fonts/JetBrainsMonoNerd"
    fc-cache -f >/dev/null
    rm -rf "$tmp"
    ok "JetBrainsMono Nerd Font"
  fi

  # oh-my-zsh (git clone on Ubuntu; a package provides /usr/share/oh-my-zsh on Arch)
  if [[ ! -d "$HOME/.oh-my-zsh" && ! -d /usr/share/oh-my-zsh ]]; then
    say "Installing oh-my-zsh..."
    git clone --depth=1 https://github.com/ohmyzsh/ohmyzsh.git "$HOME/.oh-my-zsh"
  fi
  if [[ -d "$HOME/.oh-my-zsh" && ! -d "$HOME/.oh-my-zsh/custom/themes/spaceship-prompt" ]]; then
    say "Installing spaceship prompt (omz custom theme)..."
    git clone --depth=1 https://github.com/spaceship-prompt/spaceship-prompt.git \
      "$HOME/.oh-my-zsh/custom/themes/spaceship-prompt"
  fi

  note "AppImages / vendor .debs / source builds (walker, obsidian, discord, qmk…):"
  note "→ see packages/ubuntu-manual.md"
fi

if [[ "${BOOTSTRAP_SKIP_PKGS:-0}" != 1 ]] && ! command -v claude >/dev/null 2>&1; then
  say "Installing Claude Code..."
  if [[ "$OS_FLOW" == arch ]]; then
    sudo pacman -S --needed --noconfirm claude-code || sudo npm install -g @anthropic-ai/claude-code
  else
    sudo npm install -g @anthropic-ai/claude-code
  fi
fi

# ----------------------------------------------------------------------
# 3. Private companion repo (agent brain) — usually already on /shared
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
# 4. Directories
# ----------------------------------------------------------------------
say "Creating config directories..."
mkdir -p "$HOME/.claude/agents" "$HOME/.claude/hooks" "$HOME/.claude/skills" \
         "$HOME/.claude/commands" "$HOME/.claude/plans" \
         "$HOME/.local/bin" "$HOME/.local/share/fonts" \
         "$HOME/.config/claude" "$HOME/.config/kitty" "$HOME/.config/hypr" \
         "$HOME/.config/waybar" "$HOME/.config/swaync" "$HOME/.config/dunst" \
         "$HOME/.config/fish" "$HOME/.config/rofi" "$HOME/.config/walker" \
         "$HOME/.config/systemd/user" "$HOME/.config/environment.d" \
         "$HOME/.config/Code/User" "$HOME/.kodi/userdata" "$HOME/src"

# ----------------------------------------------------------------------
# 5. Symlink manifest (Read/Edit rule: always operate on the repo path)
# ----------------------------------------------------------------------
say "Symlinking config files..."
link() {
  local src="$1" dst="$2"
  if [[ -e "$dst" && ! -L "$dst" ]]; then
    mv "$dst" "$dst.bak.$(date +%s)"
    warn "backed up existing $dst → $dst.bak.*"
  fi
  ln -sfn "$src" "$dst"
}

# --- jarvis (the agent's brain) ---
link "$PRIVATE_REPO_DIR/claude/CLAUDE.md"                    "$HOME/CLAUDE.md"
link "$PRIVATE_REPO_DIR/claude/agents/jarvis.md"             "$HOME/.claude/agents/jarvis.md"
link "$PRIVATE_REPO_DIR/claude/hooks/notify-stop-linux.sh"   "$HOME/.claude/hooks/notify-stop.sh"
link "$PRIVATE_REPO_DIR/claude/hooks/deny-sensitive-linux.sh" "$HOME/.claude/hooks/deny-sensitive.sh"
for f in "$PRIVATE_REPO_DIR"/claude/skills/*.md;   do link "$f" "$HOME/.claude/skills/$(basename "$f")"; done
for f in "$PRIVATE_REPO_DIR"/claude/commands/*.md; do link "$f" "$HOME/.claude/commands/$(basename "$f")"; done
for f in "$PRIVATE_REPO_DIR"/claude/bin/*; do
  base="$(basename "$f")"
  [[ "$base" == _* || "$base" == *.md ]] && continue
  chmod +x "$f"
  link "$f" "$HOME/.local/bin/$base"
done
link "$PRIVATE_REPO_DIR/claude/bin/dots"   "$HOME/.local/bin/dots-private"
link "$PRIVATE_REPO_DIR/claude/SRC.md"     "$HOME/src/CLAUDE.md"
# domain data lives inside the private repo (GitHub-backed) — ledger pattern
for d in ledger research lore gear comms; do
  link "$PRIVATE_REPO_DIR/claude/$d" "$HOME/$d"
done
chmod +x "$PRIVATE_REPO_DIR"/claude/hooks/*.sh

# per-OS: machine.md + Claude settings (one settings file serves both Linux
# installs — same $HOME; the Mac renders its own from settings.template.json)
if [[ "$OS_FLOW" == ubuntu ]]; then
  link "$PRIVATE_REPO_DIR/claude/machine.ubuntu.md" "$HOME/.config/claude/machine.md"
else
  link "$PRIVATE_REPO_DIR/claude/machine.arch.md"   "$HOME/.config/claude/machine.md"
fi
link "$PRIVATE_REPO_DIR/claude/settings.linux.json" "$HOME/.claude/settings.json"

# --- montressor (desktop dotfiles) ---
for f in "$REPO_DIR"/hypr/*; do
  base="$(basename "$f")"
  [[ "$base" == os-*.conf ]] && continue   # per-OS fragments linked below
  link "$f" "$HOME/.config/hypr/$base"
done
if [[ "$OS_FLOW" == ubuntu ]]; then
  link "$REPO_DIR/hypr/os-ubuntu.conf" "$HOME/.config/hypr/os.conf"
else
  link "$REPO_DIR/hypr/os-arch.conf"   "$HOME/.config/hypr/os.conf"
fi
# nwg-displays owns these per-machine files; hyprland.conf sources them — seed empty
[[ -e "$HOME/.config/hypr/monitors.conf" ]] || touch "$HOME/.config/hypr/monitors.conf"

for f in "$REPO_DIR"/waybar/*; do
  base="$(basename "$f")"
  [[ "$base" == __pycache__ ]] && continue
  link "$f" "$HOME/.config/waybar/$base"
done
for f in "$REPO_DIR"/swaync/*;         do link "$f" "$HOME/.config/swaync/$(basename "$f")"; done
for f in "$REPO_DIR"/dunst/*;          do link "$f" "$HOME/.config/dunst/$(basename "$f")"; done
for f in "$REPO_DIR"/fish/*;           do link "$f" "$HOME/.config/fish/$(basename "$f")"; done
for f in "$REPO_DIR"/rofi/*;           do link "$f" "$HOME/.config/rofi/$(basename "$f")"; done
for f in "$REPO_DIR"/environment.d/*;  do link "$f" "$HOME/.config/environment.d/$(basename "$f")"; done
for f in "$REPO_DIR"/local-bin/*; do chmod +x "$f"; link "$f" "$HOME/.local/bin/$(basename "$f")"; done
for f in "$REPO_DIR"/bin/*;       do chmod +x "$f"; link "$f" "$HOME/.local/bin/$(basename "$f")"; done

link "$REPO_DIR/kitty/kitty.conf"           "$HOME/.config/kitty/kitty.conf"
link "$REPO_DIR/vscode/settings.json"       "$HOME/.config/Code/User/settings.json"
link "$REPO_DIR/kodi/playercorefactory.xml" "$HOME/.kodi/userdata/playercorefactory.xml"
link "$REPO_DIR/zsh/zshrc"                  "$HOME/.zshrc"
link "$REPO_DIR/zsh/zshenv"                 "$HOME/.zshenv"
link "$REPO_DIR/git/gitconfig"              "$HOME/.gitconfig"

[[ -f "$REPO_DIR/walker/config.toml"      ]] && link "$REPO_DIR/walker/config.toml"      "$HOME/.config/walker/config.toml"
[[ -d "$REPO_DIR/walker/themes/andromeda" ]] && link "$REPO_DIR/walker/themes/andromeda" "$HOME/.config/walker/themes/andromeda"
for f in "$REPO_DIR"/systemd-user/*.service; do
  [[ -e "$f" ]] && link "$f" "$HOME/.config/systemd/user/$(basename "$f")"
done
ok "symlink manifest applied"
# greetd (Arch login manager) is system config — not linked here. Ubuntu uses GDM.

# ----------------------------------------------------------------------
# 6. Seed memory files (first run only — cp -n never overwrites)
# ----------------------------------------------------------------------
say "Seeding Claude memory..."
MEM_DIR="$HOME/.claude/projects/$(echo "$HOME" | sed 's|/|-|g')/memory"
mkdir -p "$MEM_DIR"
for f in "$PRIVATE_REPO_DIR"/claude/memory/*.md; do
  cp -n "$f" "$MEM_DIR/" 2>/dev/null || true
done
ok "$MEM_DIR"

# ----------------------------------------------------------------------
# 7. Default shell
# ----------------------------------------------------------------------
if [[ "$(basename "${SHELL:-}")" != "zsh" ]] && command -v zsh >/dev/null 2>&1; then
  say "Setting zsh as default shell (will prompt for your password)..."
  chsh -s "$(command -v zsh)" || warn "chsh failed — run: chsh -s $(command -v zsh)"
fi

# ----------------------------------------------------------------------
# 8. Final
# ----------------------------------------------------------------------
echo
say "Done ($OS_ID). Next steps:"
note "1. claude --login        (agent auth)"
note "2. gh auth login          (repo auth)"
if [[ "$OS_FLOW" == ubuntu ]]; then
  note "3. mullvad account login"
  note "4. Log out → GDM gear icon → Hyprland session"
  note "5. Manual installs: packages/ubuntu-manual.md (walker, obsidian, discord, qmk…)"
  note "6. Secrets checklist (user-only): runbook Phase 3.2"
else
  note "3. hyprctl reload && pkill waybar && waybar &"
fi
note "Then Super+J — Jarvis is ready."
echo
