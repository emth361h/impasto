{ lib, desktopPkgs, impastoSrc, ... }:
let
  p = desktopPkgs;
  thunar = p.thunar or p.xfce.thunar;
  optionalPath = name: if builtins.hasAttr name p then toString p.${name} else null;
  paths = p.writeText "impasto-nixos-paths.json" (builtins.toJSON {
    polkit = toString p.kdePackages.polkit-kde-agent-1;
    papirus = toString p.papirus-icon-theme;
    isoCodes = toString p.iso-codes;
    xkb = optionalPath "xkeyboard-config";
    emoji = optionalPath "unicode-emoji";
    cldr = optionalPath "cldr-annotations";
  });
  runtime = (with p; [
    quickshell awww imagemagick python3 grim wl-clipboard
    gtk3 libnotify fontconfig wireplumber playerctl
    xdg-user-dirs xdg-utils brightnessctl networkmanager bluez
    pulseaudio hyprpicker hyprsunset
    coreutils findutils gnugrep gnused gawk procps bash dbus
    papirus-icon-theme bibata-cursors
    kdePackages.qt6ct kdePackages.kconfig
  ]) ++ [ thunar ];

  impasto = p.stdenvNoCC.mkDerivation {
    pname = "impasto-mba2019";
    version = "0.5.0-nixos1";
    src = impastoSrc;
    nativeBuildInputs = [ p.python3 p.makeWrapper p.lua5_5 ];
    dontConfigure = true;
    dontBuild = true;
    postPatch = ''
      python ${./port.py} . ${paths}
      python -m compileall -q home/.config/quickshell/scripts
      python -c "import py_compile; py_compile.compile('home/.local/bin/impasto', doraise=True)"
      find home/.config/hypr -name '*.lua' -print0 | xargs -0 -n 1 luac -p
    '';
    installPhase = ''
      runHook preInstall
      mkdir -p "$out/share/impasto/config" "$out/share/impasto/data" "$out/bin"
      cp -r home/.config/hypr home/.config/quickshell "$out/share/impasto/config/"
      cp -r home/.local/share/wallpapers home/.local/share/impasto "$out/share/impasto/data/"
      mkdir -p "$out/share/fonts/truetype"
      cp home/.local/share/fonts/GrapeNuts-Regular.ttf "$out/share/fonts/truetype/"
      cp home/.local/share/fonts/GrapeNuts-OFL.txt "$out/share/fonts/truetype/"
      install -m755 home/.local/bin/impasto "$out/bin/impasto"
      cp LICENSE "$out/share/impasto/LICENSE"
      patchShebangs "$out/share/impasto/config/quickshell/scripts" "$out/bin/impasto"
      wrapProgram "$out/bin/impasto" --prefix PATH : ${lib.makeBinPath runtime}
      makeWrapper ${p.quickshell}/bin/qs "$out/bin/impasto-shell" \
        --prefix PATH : ${lib.makeBinPath runtime}
      runHook postInstall
    '';
  };
  setup = p.writeShellApplication {
    name = "impasto-setup";
    runtimeInputs = [ p.python3 ];
    text = ''
      exec python3 ${./setup-user.py} ${impasto}/share/impasto "$@"
    '';
  };
in {
  # Existing desktop.nix / desktop-extras.nix may still refer to these names.
  # Select each complete desktop package, rather than mixing library overrides.
  nixpkgs.overlays = [
    (_final: _prev: {
      kitty = p.kitty;
      firefox = p.firefox;
      xwayland = p.xwayland;
      waybar = p.waybar;
      mako = p.mako;
      hyprpaper = p.hyprpaper;
      wofi = p.wofi;
    })
  ];

  environment.systemPackages = runtime ++ [ impasto setup ];
  fonts.packages = [
    impasto p.inter p.nerd-fonts.jetbrains-mono
    p.noto-fonts p.noto-fonts-cjk-sans p.noto-fonts-color-emoji
  ];
  security.polkit.enable = true;
  security.pam.services.impasto = {};
  services.upower.enable = true;
  programs.dconf.enable = true;
}
