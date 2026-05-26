# packages

Snapshots of every explicitly-installed package on each machine.
The bootstrap scripts read these to restore a system back to working order.

| File | Source command | Consumed by |
|---|---|---|
| `pacman.txt` | `pacman -Qqen` | `bootstrap-linux.sh` |
| `aur.txt`    | `pacman -Qqem` | `bootstrap-linux.sh` (via `yay`) |
| `mac-brew.txt` | `brew leaves` | `bootstrap-mac.sh` |
| `mac-cask.txt` | `brew list --cask` | `bootstrap-mac.sh` |

## Regenerating

Run `dots-sync-pkgs` (zsh function) on the host machine. It refreshes the
list that matches the current OS, commits, and pushes — no-op if unchanged.
