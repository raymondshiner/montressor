source /usr/share/cachyos-fish-config/cachyos-config.fish

# Dark mode — tells Qt and GTK apps to use dark theme
set -gx GTK_THEME adw-gtk3-dark
set -gx QT_QPA_PLATFORMTHEME qt5ct
set -gx QT_STYLE_OVERRIDE adwaita-dark
set -gx COLORTERM truecolor

# overwrite greeting
# potentially disabling fastfetch
#function fish_greeting
#    # smth smth
#end
