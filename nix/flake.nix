{
  description = "MacBook Air 2019";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";

    # Desktop packages: Hyprland 0.56.2.
    nixpkgs-desktop.url =
      "github:NixOS/nixpkgs/151fa4e8ddfdd8dd25d945ad94ed54a13de9f6e4";

    impasto-src = {
      url = "github:emth361h/impasto/6d759aa3fe16e3b40641beeb9b24e3c4afcfeefe";
      flake = false;
    };

    nixpkgs-t2.url =
      "github:NixOS/nixpkgs/567a49d1913ce81ac6e9582e3553dd90a955875f";

    nixos-hardware.url =
      "github:NixOS/nixos-hardware/875776f0252fcb8618bb948640a0d1f7a5b362be";

    nixos-hardware.inputs.nixpkgs.follows = "nixpkgs-t2";
  };

  outputs = { nixpkgs, nixpkgs-desktop, nixpkgs-t2, nixos-hardware, impasto-src, ... }:
    let
      desktopPkgs = nixpkgs-desktop.legacyPackages.x86_64-linux;
      t2Pkgs = nixpkgs-t2.legacyPackages.x86_64-linux;

      t2Kernel = t2Pkgs.callPackage
        "${nixos-hardware}/apple/t2/pkgs/linux-t2"
        {};
    in {
      nixosConfigurations.mba2019 = nixpkgs.lib.nixosSystem {
        system = "x86_64-linux";

        specialArgs = {
          inherit desktopPkgs;
          impastoSrc = impasto-src;
        };

        modules = [
          ./configuration.nix
          ./impasto.nix
          nixos-hardware.nixosModules.apple-t2

          ({ lib, ... }: {
            boot.kernelPackages = lib.mkForce (
              t2Pkgs.linuxPackagesFor t2Kernel
            );

            programs.hyprland.package = desktopPkgs.hyprland;
            programs.hyprland.portalPackage =
              desktopPkgs.xdg-desktop-portal-hyprland;
            hardware.graphics.package = desktopPkgs.mesa;

            nix.settings.extra-substituters = [
              "https://t2linux.cachix.org"
            ];

            nix.settings.extra-trusted-public-keys = [
              "t2linux.cachix.org-1:P733c5Gt1qTcxsm+Bae0renWnT8OLs0u9+yfaK2Bejw="
            ];
          })
        ];
      };
    };
}
