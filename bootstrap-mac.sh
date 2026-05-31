#!/usr/bin/env bash
# Bootstrap a fresh macOS machine to "Jeeves + Friday ready".
# Idempotent — safe to re-run. Run from inside the cloned dotfiles repo.
#
# Usage:
#   git clone git@github.com:<you>/crew-quarters.git ~/crew-quarters
#   cd ~/crew-quarters && ./bootstrap-mac.sh

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CYAN=$'\033[38;2;0;232;198m'
MUTED=$'\033[38;2;103;118;145m'
GREEN=$'\033[38;2;168;255;96m'
RED=$'\033[38;2;238;93;67m'
RESET=$'\033[0m'

say() { printf "${CYAN}==>${RESET} %s\n" "$1"; }
note() { printf "${MUTED}    %s${RESET}\n" "$1"; }
ok()  { printf "${GREEN}    ✓ %s${RESET}\n" "$1"; }
warn(){ printf "${RED}    ! %s${RESET}\n" "$1"; }

# ----------------------------------------------------------------------
# 0. Sanity
# ----------------------------------------------------------------------
if [[ "$(uname -s)" != "Darwin" ]]; then
  warn "This script is for macOS. Use bootstrap-linux.sh on Arch."
  exit 1
fi

# ----------------------------------------------------------------------
# 1. Xcode Command Line Tools
# ----------------------------------------------------------------------
say "Checking Xcode Command Line Tools..."
if ! xcode-select -p >/dev/null 2>&1; then
  note "Installing CLT — a system dialog will appear. Re-run this script after it finishes."
  xcode-select --install || true
  exit 0
else
  ok "CLT installed"
fi

# ----------------------------------------------------------------------
# 2. Homebrew
# ----------------------------------------------------------------------
say "Checking Homebrew..."
if ! command -v brew >/dev/null 2>&1; then
  note "Installing Homebrew..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  # Add brew to PATH for this session (Apple Silicon vs Intel)
  if [[ -x /opt/homebrew/bin/brew ]]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  elif [[ -x /usr/local/bin/brew ]]; then
    eval "$(/usr/local/bin/brew shellenv)"
  fi
else
  ok "Homebrew installed"
fi

# ----------------------------------------------------------------------
# 3. Packages
# ----------------------------------------------------------------------
say "Installing seed CLI tools..."
BREW_CLI=(gh git jq fzf ripgrep fd node neovim zsh terminal-notifier zsh-syntax-highlighting zsh-autosuggestions zsh-history-substring-search spaceship)
for pkg in "${BREW_CLI[@]}"; do
  if brew list --formula "$pkg" >/dev/null 2>&1; then
    ok "$pkg"
  else
    note "Installing $pkg..."
    brew install "$pkg"
  fi
done

if [[ -s "$REPO_DIR/packages/mac-brew.txt" ]]; then
  say "Installing brew formulae from packages/mac-brew.txt..."
  while IFS= read -r pkg; do
    [[ -z "$pkg" || "$pkg" =~ ^[[:space:]]*# ]] && continue
    if brew list --formula "$pkg" >/dev/null 2>&1; then
      ok "$pkg"
    else
      note "Installing $pkg..."
      brew install "$pkg" || warn "failed: $pkg"
    fi
  done < "$REPO_DIR/packages/mac-brew.txt"
fi

say "Installing seed desktop stack (casks)..."
BREW_CASK=(kitty raycast karabiner-elements)
for pkg in "${BREW_CASK[@]}"; do
  if brew list --cask "$pkg" >/dev/null 2>&1; then
    ok "$pkg"
  else
    note "Installing $pkg..."
    brew install --cask "$pkg"
  fi
done

if [[ -s "$REPO_DIR/packages/mac-cask.txt" ]]; then
  say "Installing brew casks from packages/mac-cask.txt..."
  while IFS= read -r pkg; do
    [[ -z "$pkg" || "$pkg" =~ ^[[:space:]]*# ]] && continue
    if brew list --cask "$pkg" >/dev/null 2>&1; then
      ok "$pkg"
    else
      note "Installing $pkg..."
      brew install --cask "$pkg" || warn "failed: $pkg"
    fi
  done < "$REPO_DIR/packages/mac-cask.txt"
fi

say "Installing AeroSpace (tiling WM)..."
if ! brew list --cask aerospace >/dev/null 2>&1; then
  brew install --cask nikitabobko/tap/aerospace
else
  ok "aerospace"
fi

say "Installing SketchyBar..."
if ! brew list --formula sketchybar >/dev/null 2>&1; then
  brew tap FelixKratz/formulae
  brew install sketchybar
else
  ok "sketchybar"
fi

say "Installing oh-my-zsh..."
if [[ ! -d "$HOME/.oh-my-zsh" ]]; then
  RUNZSH=no KEEP_ZSHRC=yes sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
else
  ok "oh-my-zsh"
fi

say "Installing Claude Code..."
if ! command -v claude >/dev/null 2>&1; then
  note "Installing via npm..."
  npm install -g @anthropic-ai/claude-code
else
  ok "claude"
fi

# ----------------------------------------------------------------------
# 4. Directories
# ----------------------------------------------------------------------
say "Creating config directories..."
mkdir -p "$HOME/.claude/agents" \
         "$HOME/.claude/hooks" \
         "$HOME/.local/bin" \
         "$HOME/.config/claude" \
         "$HOME/.config/kitty" \
         "$HOME/.config/sketchybar/plugins" \
         "$HOME/.config/karabiner" \
         "$HOME/Library/Application Support/Code/User"

# ----------------------------------------------------------------------
# 5. Symlinks (ln -sfn = idempotent)
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

link "$REPO_DIR/claude/CLAUDE.md"                  "$HOME/CLAUDE.md"
link "$REPO_DIR/claude/agents/jeeves.md"           "$HOME/.claude/agents/jeeves.md"
link "$REPO_DIR/claude/agents/friday.md"           "$HOME/.claude/agents/friday.md"
link "$REPO_DIR/claude/agents/watson.md"           "$HOME/.claude/agents/watson.md"
link "$REPO_DIR/claude/hooks/notify-stop-mac.sh"   "$HOME/.claude/hooks/notify-stop.sh"
link "$REPO_DIR/claude/bin/cc-statusline.sh"       "$HOME/.local/bin/cc-statusline.sh"
link "$REPO_DIR/claude/bin/jeeves"                 "$HOME/.local/bin/jeeves"
link "$REPO_DIR/claude/bin/friday"                 "$HOME/.local/bin/friday"
link "$REPO_DIR/claude/machine.mac.md"             "$HOME/.config/claude/machine.md"
link "$REPO_DIR/kitty/kitty.conf"                  "$HOME/.config/kitty/kitty.conf"
link "$REPO_DIR/vscode/settings.json"              "$HOME/Library/Application Support/Code/User/settings.json"
[[ -f "$REPO_DIR/zsh/zshrc" ]] && link "$REPO_DIR/zsh/zshrc" "$HOME/.zshrc"

# Mac-specific scaffolds (only if present in repo)
[[ -f "$REPO_DIR/mac/aerospace/.aerospace.toml"     ]] && link "$REPO_DIR/mac/aerospace/.aerospace.toml"     "$HOME/.aerospace.toml"
[[ -f "$REPO_DIR/mac/sketchybar/sketchybarrc"       ]] && link "$REPO_DIR/mac/sketchybar/sketchybarrc"       "$HOME/.config/sketchybar/sketchybarrc"
[[ -f "$REPO_DIR/mac/karabiner/karabiner.json"      ]] && link "$REPO_DIR/mac/karabiner/karabiner.json"      "$HOME/.config/karabiner/karabiner.json"

chmod +x "$REPO_DIR/claude/hooks/notify-stop-mac.sh" \
         "$REPO_DIR/claude/bin/cc-statusline.sh" \
         "$REPO_DIR/claude/bin/jeeves" \
         "$REPO_DIR/claude/bin/friday"

# ----------------------------------------------------------------------
# 6. Render settings.json template
# ----------------------------------------------------------------------
say "Rendering Claude settings.json..."
sed "s|__HOME__|$HOME|g" "$REPO_DIR/claude/settings.template.json" > "$HOME/.claude/settings.json"
ok "$HOME/.claude/settings.json"

# ----------------------------------------------------------------------
# 6b. Ensure ~/src exists (Watson's home; per-agent MCPs live in watson.md)
# ----------------------------------------------------------------------
mkdir -p "$HOME/src"
link "$REPO_DIR/claude/SRC.md" "$HOME/src/CLAUDE.md"

# ----------------------------------------------------------------------
# 7. Seed memory files
# ----------------------------------------------------------------------
say "Seeding Claude memory..."
MEM_DIR="$HOME/.claude/projects/$(echo "$HOME" | sed 's|/|-|g')/memory"
mkdir -p "$MEM_DIR"
for f in "$REPO_DIR"/claude/memory/*.md; do
  cp -n "$f" "$MEM_DIR/" 2>/dev/null || true
done
ok "$MEM_DIR"

# ----------------------------------------------------------------------
# 8. PATH check
# ----------------------------------------------------------------------
say "Verifying PATH..."
if ! echo "$PATH" | tr ':' '\n' | grep -qx "$HOME/.local/bin"; then
  warn "$HOME/.local/bin is not in PATH"
  note "Add this to ~/.zshrc:    export PATH=\"\$HOME/.local/bin:\$PATH\""
else
  ok "PATH includes ~/.local/bin"
fi

# ----------------------------------------------------------------------
# 9. Final guidance
# ----------------------------------------------------------------------
echo
say "Done. Next steps:"
note "1. Run:    claude --login        (one-time auth)"
note "2. Run:    gh auth login         (if not already)"
note "3. Start AeroSpace: open /Applications/AeroSpace.app  (grant Accessibility access)"
note "4. Start SketchyBar:  brew services start sketchybar"
note "5. Launch Karabiner-Elements once to grant Input Monitoring permission"
note "6. Type 'claude' — Jeeves is ready."
echo
