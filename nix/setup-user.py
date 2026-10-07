"""Install the prepared desktop as the logged-in user, with backups."""
import datetime
import json
import os
from pathlib import Path
import shutil
import sys


def main():
    if os.geteuid() == 0:
        raise SystemExit("Run impasto-setup as your normal user, without sudo.")
    for proc in Path("/proc").glob("[0-9]*"):
        try:
            if proc.stat().st_uid == os.getuid() and (proc / "comm").read_text().strip() == "Hyprland":
                raise SystemExit("Exit Hyprland with uwsm stop, then run this from a TTY or SSH.")
        except (OSError, ProcessLookupError):
            continue
    source = Path(sys.argv[1])
    config = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    data = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
    state = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state")
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup = state / "impasto-nixos-backups" / stamp
    backup.mkdir(parents=True)
    # The theme service can write GTK, Qt and terminal preferences.
    if config.exists():
        shutil.copytree(config, backup / "config", symlinks=True)
    # Keep previous shell state and icon overrides, including the absence of each.
    manifest = {}
    for label, target in {
        "state-quickshell": state / "quickshell",
        "state-impasto": state / "impasto",
        "data-icons": data / "icons",
        "data-impasto": data / "impasto",
    }.items():
        manifest[label] = str(target)
        if target.exists():
            shutil.copytree(target, backup / label, symlinks=True)
    (backup / "locations.json").write_text(json.dumps({
        "config": str(config), "data": str(data), "state": str(state), **manifest,
    }, indent=2))
    print(f"Backup: {backup}", flush=True)
    config.mkdir(parents=True, exist_ok=True)
    for name in ("hypr", "quickshell"):
        target = config / name
        if target.exists() or target.is_symlink():
            target.rename(backup / ("previous-" + name))
        shutil.copytree(source / "config" / name, target)
        # Source files originate in the read-only store; user configuration is editable.
        for item in [target, *target.rglob("*")]:
            if not item.is_symlink():
                item.chmod(item.stat().st_mode | 0o200)
    # Preserve existing wallpapers and per-user data; install only missing assets.
    for name in ("wallpapers", "impasto"):
        for original in (source / "data" / name).rglob("*"):
            if not original.is_file():
                continue
            target = data / name / original.relative_to(source / "data" / name)
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(original, target)
                target.chmod(target.stat().st_mode | 0o200)
    version = state / "impasto" / "version"
    version.parent.mkdir(parents=True, exist_ok=True)
    version.write_text("v0.5.0-nixos1\nnixos\n\n6d759aa3fe16e3b40641beeb9b24e3c4afcfeefe\n")
    shell_state = state / "quickshell"
    shell_state.mkdir(parents=True, exist_ok=True)
    settings_file = shell_state / "settings.json"
    if not settings_file.exists():
        settings_file.write_text(json.dumps({
            "keyboard": {"input:kb_layout": "jp"},
            "animationPreset": "off", "clipboardHistory": False,
            "idleLock": 0, "idleScreen": 0, "idleSuspend": 0,
        }, indent=2))
    theme_state = shell_state / "state.json"
    if not theme_state.exists():
        theme_state.write_text(json.dumps({
            "activeTheme": "adaptive",
            "currentWallpaper": str(data / "wallpapers/pagoda-fuji-blossom.jpeg"),
            "currentMotion": "",
        }, indent=2))
    for name, default in {
        "kitty-font.conf": "font_family JetBrainsMono Nerd Font Mono\n",
        "kitty-palette.conf": "background #101014\nforeground #eeeeee\n",
    }.items():
        fragment = shell_state / name
        if not fragment.exists():
            fragment.write_text(default)
    kitty_config = config / "kitty" / "kitty.conf"
    kitty_config.parent.mkdir(parents=True, exist_ok=True)
    kitty_text = kitty_config.read_text() if kitty_config.exists() else ""
    marker = "# Impasto NixOS palette includes"
    if marker not in kitty_text:
        kitty_text += (f"\n{marker}\n"
                       f"include {shell_state}/kitty-font.conf\n"
                       f"include {shell_state}/kitty-palette.conf\n")
        kitty_config.write_text(kitty_text)
    print("Ready. Start Hyprland using: uwsm start -g -1 -- hyprland.desktop")
    print("Change wallpaper: Cmd+T, then choose a painting.")
    print("Return to the previous desktop: see README.md and the backup path above.")


if __name__ == "__main__":
    main()
