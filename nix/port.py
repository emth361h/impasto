"""Adapt Impasto 6d759aa for NixOS. Run only inside the Nix build directory."""
import json
from pathlib import Path
import sys


def adapt(root, paths):
    root = Path(root)
    qs = root / "home/.config/quickshell"
    hypr = root / "home/.config/hypr"

    def replace(path, old, new, count=1):
        text = path.read_text(encoding="utf-8")
        found = text.count(old)
        if found != count:
            raise RuntimeError(f"{path}: expected {count} matches for {old!r}, got {found}")
        path.write_text(text.replace(old, new), encoding="utf-8", newline="\n")

    def find_file(base, name):
        found = sorted(Path(base).rglob(name))
        if not found:
            raise RuntimeError(f"Missing {name} under {base}")
        return found[0].as_posix()

    def write_module(name, body):
        path = hypr / "modules" / name
        # Keep the upstream attribution banner when replacing module behavior.
        header = path.read_text(encoding="utf-8").split("\n\n", 1)[0]
        path.write_text(header + "\n\n" + body, encoding="utf-8", newline="\n")

    agent = find_file(paths["polkit"], "polkit-kde-authentication-agent-1")
    replace(qs / "services/PolkitService.qml",
            "/usr/lib/polkit-kde-authentication-agent-1", agent)
    replace(qs / "services/LockService.qml", 'config: "login"', 'config: "impasto"')
    replace(qs / "services/SessionService.qml",
            'Hyprland.dispatch("hl.dsp.exit()")', 'root.exec(["uwsm", "stop"])')
    # This port is updated by Nix, never through the Arch setup program.
    replace(qs / "services/VersionService.qml",
            'readonly property string repo: (root.lines[2] ?? "").trim()',
            'readonly property string repo: ""')

    replace(qs / "components/TrayIcon.qml", "/usr/share/icons/Papirus-Dark/",
            paths["papirus"] + "/share/icons/Papirus-Dark/")
    replace(qs / "scripts/theme_manager.py",
            '(XDG_DATA_HOME, "/usr/local/share", "/usr/share")',
            '(XDG_DATA_HOME, ' + repr(paths["papirus"] + "/share") + ', "/usr/local/share", "/usr/share")')
    replace(qs / "scripts/emoji.py", "/usr/share/iso-codes/json/iso_3166-1.json",
            find_file(paths["isoCodes"], "iso_3166-1.json"))
    if paths.get("emoji"):
        replace(qs / "scripts/emoji.py", "/usr/share/unicode/emoji/emoji-test.txt",
                find_file(paths["emoji"], "emoji-test.txt"))
    else:
        # Emoji search remains optional when this nixpkgs does not package its data.
        replace(qs / "scripts/emoji.py", "def read(language):",
                'def read(language):\n    if not os.path.isfile(SOURCE):\n        return []')
    if paths.get("cldr"):
        annotations = sorted(Path(paths["cldr"]).rglob("annotations/en.xml"))
        if annotations:
            replace(qs / "scripts/emoji.py", "/usr/share/unicode/cldr/common/annotations",
                    annotations[0].parent.as_posix())
    if paths.get("xkb"):
        for name in ("evdev.lst", "base.lst"):
            replace(qs / "scripts/compositor.py", "/usr/share/X11/xkb/rules/" + name,
                    find_file(paths["xkb"], name))

    replace(hypr / "modules/monitors.lua", "scale    = 1,", "scale    = 2,")
    replace(hypr / "modules/input.lua", 'kb_layout  = "us",', 'kb_layout  = "jp",')
    replace(hypr / "modules/env.lua", 'hl.env("HYPRCURSOR_THEME", "impasto-cursor")',
            '-- NixOS: use the packaged Bibata XCursor fallback.')
    replace(qs / "services/SettingsService.qml", 'property string animationPreset: "macos"',
            'property string animationPreset: "off"')
    replace(qs / "services/SettingsService.qml", 'property bool clipboardHistory: true',
            'property bool clipboardHistory: false')

    # Keep upstream's profile-aware shortcuts; replace only Mac/session actions.
    keys = hypr / "modules/keybinds.lua"
    replace(keys, 'command -v hyprshutdown >/dev/null 2>&1 && hyprshutdown || hyprctl dispatch \'hl.dsp.exit()\'',
            'uwsm stop')
    replace(keys, 'pkill -x quickshell; pkill -x qs; sleep 0.5; qs -d',
            'pkill -x quickshell; pkill -x qs; sleep 0.5; uwsm app -s b -- impasto-shell')
    replace(keys, 'hl.dsp.global("quickshell:brightnessUp")',
            'hl.dsp.exec_cmd("brightnessctl -c backlight set +5%")')
    replace(keys, 'hl.dsp.global("quickshell:brightnessDown")',
            'hl.dsp.exec_cmd("brightnessctl -c backlight --min-value=1 set 5%-")')
    with keys.open("a", encoding="utf-8", newline="\n") as out:
        out.write('''
-- MBA2019: confirmed keyboard backlight device pattern.
bind("XF86KbdBrightnessUp", hl.dsp.exec_cmd("brightnessctl -d '*apple::kbd_backlight*' set +10%"),
    { repeating = true, description = "Mac · Keyboard backlight up" })
bind("XF86KbdBrightnessDown", hl.dsp.exec_cmd("brightnessctl -d '*apple::kbd_backlight*' set 10%-"),
    { repeating = true, description = "Mac · Keyboard backlight down" })
''')
    write_module("programs.lua", '''-- NixOS/UWSM application commands.
return {
    terminal = "uwsm app -- kitty",
    file_manager = "uwsm app -- thunar",
    browser = "uwsm app -- firefox",
}
''')
    write_module("autostart.lua", '''-- NixOS: Impasto owns the bar and notifications in this session.
hl.on("hyprland.start", function()
    hl.exec_cmd("uwsm app -s b -- awww-daemon")
    hl.exec_cmd("uwsm app -s b -- impasto-shell")
end)
''')


if __name__ == "__main__":
    adapt(sys.argv[1], json.loads(Path(sys.argv[2]).read_text(encoding="utf-8")))
