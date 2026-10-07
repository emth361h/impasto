#!/usr/bin/env python3
"""Check source adaptation without executing any upstream script."""
from pathlib import Path
import ast
import importlib.util
import shutil
import sys
import tempfile
import uuid

sys.dont_write_bytecode = True
repo = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("impasto_port", repo / "nix/port.py")
port = importlib.util.module_from_spec(spec)
spec.loader.exec_module(port)
scratch_parent = Path(tempfile.gettempdir()).resolve()
scratch = scratch_parent / ("impasto-port-" + uuid.uuid4().hex)
scratch.mkdir()
try:
    fixtures = {
        "polkit": ["libexec/polkit-kde-authentication-agent-1"],
        "papirus": ["share/icons/Papirus-Dark/22x22/panel/example.svg"],
        "isoCodes": ["share/iso-codes/json/iso_3166-1.json"],
        "xkb": ["share/X11/xkb/rules/evdev.lst", "share/X11/xkb/rules/base.lst"],
        "emoji": ["share/unicode/emoji/emoji-test.txt"],
        "cldr": ["share/unicode/cldr/common/annotations/en.xml"],
    }
    paths = {}
    for name, filenames in fixtures.items():
        paths[name] = (scratch / "packages" / name).as_posix()
        for filename in filenames:
            target = Path(paths[name]) / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("fixture", encoding="utf-8")
    for name, supplied in [
        ("all-data", paths),
        ("optional-data-absent", {**paths, "emoji": None, "cldr": None, "xkb": None}),
    ]:
        tree = scratch / name
        shutil.copytree(repo / "home/.config/hypr", tree / "home/.config/hypr")
        shutil.copytree(repo / "home/.config/quickshell", tree / "home/.config/quickshell")
        port.adapt(tree, supplied)
        scripts = list(tree.rglob("*.py"))
        for script in scripts:
            ast.parse(script.read_text(encoding="utf-8"), filename=str(script))
        keys = (tree / "home/.config/hypr/modules/keybinds.lua").read_text(encoding="utf-8")
        assert "*apple::kbd_backlight*" in keys
        assert "hyprshutdown" not in keys
        auto = (tree / "home/.config/hypr/modules/autostart.lua").read_text(encoding="utf-8")
        assert "impasto-shell" in auto and "hyprpm" not in auto
        print(f"{name}: source replacements applied; {len(scripts)} Python scripts parse")
    for script in (repo / "nix").glob("*.py"):
        ast.parse(script.read_text(encoding="utf-8"), filename=str(script))
    print("Adapter Python files parse. Nix/Qt/Lua runtime checks remain separate.")
finally:
    resolved = scratch.resolve()
    if resolved.parent != scratch_parent or not resolved.name.startswith("impasto-port-"):
        raise RuntimeError("Refusing to clean an unexpected scratch directory")
    shutil.rmtree(resolved)
