# Ubuntu — installs outside apt/snap

Everything the Arch side gets from AUR/CachyOS repos that has no clean apt/snap
route on Ubuntu 26.04. `bootstrap-linux.sh` prints a pointer here; these are
deliberate manual steps.

| What | Route | Notes |
|---|---|---|
| walker + elephant (launcher) | source build (Go) | `github.com/abenz1267/walker` + `…/elephant`. systemd user units already in `montressor/systemd-user/`. Until built, `os-ubuntu.conf` points `$menu` at rofi — flip to walker after. |
| Obsidian | official `.deb` | obsidian.md/download |
| Discord | official `.deb` | discord.com/download |
| AppImageLauncher | upstream `.deb` | github.com/TheAssassin/AppImageLauncher (Ubuntu-native project) |
| Todoist | AppImage | todoist.com/downloads |
| Bambu Studio | AppImage (ubuntu build) | github.com/bambulab/BambuStudio/releases |
| ZSA Keymapp | tarball → `~/.local/share/keymapp/` | zsa.io/flash — `~/.local/bin/keymapp` symlink pattern as on Arch |
| balenaEtcher | AppImage → `~/.local/share/balenaEtcher/` | github.com/balena-io/etcher |
| qmk CLI | `pipx install qmk` | Moonlander firmware flow (`build-reference.md`); run `pipx ensurepath` once |
| Epson ESC/P-R 2 | Epson `.deb` | `epson-inkjet-printer-escpr2` from epson.sn; base `printer-driver-escpr` comes via apt |
| woeusb-ng | `pipx install WoeUSB-ng` | `woeusb-gui` bin execs `/usr/bin/woeusbgui` — adjust path to the pipx shim on Ubuntu |
| nativefier | `npm install -g nativefier` | |
| gmailctl | GitHub release binary | |
| glance | GitHub release binary | `glance-bin` equivalent |
| claude-desktop | no official Linux build | skip — Claude Code covers it (community repacks exist if wanted) |

## Notes

- **`ubuntu-apt.txt` is both install list and snapshot.** Bootstrap installs from
  it; after first boot, `dots-sync-pkgs` overwrites it with the flat
  `apt-mark showmanual` output (comments vanish). That's the same
  self-maintaining model as `pacman.txt` on the Arch side.
- **Mullvad repo** line uses `$VERSION_CODENAME` (`resolute`). If `apt update`
  404s because Mullvad hasn't published resolute yet, edit
  `/etc/apt/sources.list.d/mullvad.list` → replace the codename with `noble`.
- **Firefox** is Ubuntu's preinstalled snap. Chrome/Brave come from vendor apt
  repos — official vendor `.deb`s are the point of this migration.
- **adw-gtk3-theme**: package name differs from Arch's `adw-gtk-theme`; if apt
  can't find it, releases at github.com/lassekongo83/adw-gtk3.
- **greetd/regreet**: Arch-only login manager. Ubuntu uses GDM (pick the
  Hyprland session at the gear icon). greetd parity is optional, later.
