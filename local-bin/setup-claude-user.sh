#!/bin/bash
# One-shot setup for the dedicated `claude` user with bind-mounted shared paths.
# Run as your normal user; will prompt for sudo password and a new claude password.

set -euo pipefail

REAL_USER="sirlexicon"
REAL_HOME="/home/$REAL_USER"
CLAUDE_HOME="/home/claude"

echo "==> Creating claude user..."
if id claude &>/dev/null; then
    echo "    user already exists, skipping"
else
    sudo useradd -m -G wheel,video,audio,input -s /bin/zsh claude
    echo "    Set a password for the claude user:"
    sudo passwd claude
fi

echo "==> Creating claude-share group..."
if getent group claude-share &>/dev/null; then
    echo "    group already exists, skipping"
else
    sudo groupadd claude-share
fi
sudo usermod -aG claude-share "$REAL_USER"
sudo usermod -aG claude-share claude

echo "==> Locking down /home/$REAL_USER..."
sudo chmod 700 "$REAL_HOME"

echo "==> Creating mount-point directories in $CLAUDE_HOME..."
SHARED_DIRS=(
    "Projects"
    "montressor"
    "montressor-private"
    "Downloads"
    "Media"
    "Music"
    "Videos"
    ".config/hypr"
    ".config/waybar"
    ".config/swaync"
    ".config/kitty"
    ".config/dunst"
    ".config/gtk-3.0"
    ".local/bin"
)
for d in "${SHARED_DIRS[@]}"; do
    sudo -u claude mkdir -p "$CLAUDE_HOME/$d"
done

echo "==> Adding bind mounts to /etc/fstab..."
FSTAB_MARK="# claude user bind mounts"
if ! grep -q "$FSTAB_MARK" /etc/fstab; then
    sudo tee -a /etc/fstab > /dev/null <<EOF

$FSTAB_MARK
$REAL_HOME/Projects        $CLAUDE_HOME/Projects        none bind 0 0
$REAL_HOME/montressor        $CLAUDE_HOME/montressor        none bind 0 0
$REAL_HOME/montressor-private $CLAUDE_HOME/montressor-private none bind 0 0
$REAL_HOME/Downloads       $CLAUDE_HOME/Downloads       none bind 0 0
$REAL_HOME/Media           $CLAUDE_HOME/Media           none bind 0 0
$REAL_HOME/Music           $CLAUDE_HOME/Music           none bind 0 0
$REAL_HOME/Videos          $CLAUDE_HOME/Videos          none bind 0 0
$REAL_HOME/.config/hypr    $CLAUDE_HOME/.config/hypr    none bind 0 0
$REAL_HOME/.config/waybar  $CLAUDE_HOME/.config/waybar  none bind 0 0
$REAL_HOME/.config/swaync  $CLAUDE_HOME/.config/swaync  none bind 0 0
$REAL_HOME/.config/kitty   $CLAUDE_HOME/.config/kitty   none bind 0 0
$REAL_HOME/.config/dunst   $CLAUDE_HOME/.config/dunst   none bind 0 0
$REAL_HOME/.config/gtk-3.0 $CLAUDE_HOME/.config/gtk-3.0 none bind 0 0
$REAL_HOME/.local/bin      $CLAUDE_HOME/.local/bin      none bind 0 0
EOF
    echo "    fstab updated"
else
    echo "    bind mounts already present, skipping"
fi

echo "==> Mounting shared paths..."
sudo mount -a

echo "==> Setting group ownership and write perms on shared paths..."
SHARED_PATHS=(
    "$REAL_HOME/Projects"
    "$REAL_HOME/montressor"
    "$REAL_HOME/montressor-private"
    "$REAL_HOME/Downloads"
    "$REAL_HOME/Media"
    "$REAL_HOME/Music"
    "$REAL_HOME/Videos"
    "$REAL_HOME/.config/hypr"
    "$REAL_HOME/.config/waybar"
    "$REAL_HOME/.config/swaync"
    "$REAL_HOME/.config/kitty"
    "$REAL_HOME/.config/dunst"
    "$REAL_HOME/.config/gtk-3.0"
    "$REAL_HOME/.local/bin"
)
for p in "${SHARED_PATHS[@]}"; do
    [ -e "$p" ] || { echo "    skipping missing $p"; continue; }
    sudo chgrp -R claude-share "$p"
    sudo chmod -R g+rw "$p"
    sudo find "$p" -type d -exec chmod g+s {} \;
done

echo "==> Sharing .zshrc via group perms..."
sudo chgrp claude-share "$REAL_HOME/.zshrc"
sudo chmod 640 "$REAL_HOME/.zshrc"
# Symlink the real zshrc into claude's home so it sources the same config
sudo -u claude ln -sf "$REAL_HOME/.zshrc" "$CLAUDE_HOME/.zshrc" 2>/dev/null || true

echo "==> Generating SSH key for claude user..."
if [ ! -f "$CLAUDE_HOME/.ssh/id_ed25519" ]; then
    sudo -u claude mkdir -p "$CLAUDE_HOME/.ssh"
    sudo -u claude chmod 700 "$CLAUDE_HOME/.ssh"
    sudo -u claude ssh-keygen -t ed25519 -f "$CLAUDE_HOME/.ssh/id_ed25519" -N "" -C "claude@$(hostname)"
    echo ""
    echo "    Public key (add to GitHub for dotfiles + Projects access):"
    echo "    ----------------------------------------------------------"
    sudo cat "$CLAUDE_HOME/.ssh/id_ed25519.pub"
    echo "    ----------------------------------------------------------"
else
    echo "    SSH key already exists"
fi

echo ""
echo "==> Done. Next steps:"
echo "    1. Add the public key above to GitHub (Settings > SSH keys)"
echo "    2. Log out and back in (so your group membership in claude-share takes effect)"
echo "    3. Add this alias to ~/.zshrc:  alias jeeves='sudo -iu claude claude'"
echo "    4. Type 'jeeves' to start an isolated Claude session"
