# ImpastoのNixOS向け移植案（MacBook Air 2019）

[Andreu MassanetによるImpasto](https://github.com/andreumassanet/impasto)を、
MacBook Air 2019/T2・8GB・JISキーボード・通常CLI起動のNixOSに組み込むためのアダプターです。
上流のArch用インストーラーは実行しません。ライセンスはリポジトリの[GPL-3.0](../LICENSE)に従います。

**開発中です。NixOSでの評価・ビルド、Impastoの画面表示・ロック解除は検証待ちです。**
Hyprland 0.56.2への更新と、デスクトップ側のパッケージにそろえたKittyの起動は対象Macで確認済みです。

## ファイルの役割

| ファイル | 役割 |
|---|---|
| `flake.nix` | 既存のMBA2019構成に使う入力とモジュールの例 |
| `impasto.nix` | パッケージ、フォント、PAM、GUIパッケージの選択 |
| `port.py` | 固定した上流ソースへのNixOS・Mac向け修正 |
| `setup-user.py` | バックアップを作ってユーザー設定を配置 |
| `check-port.py` | ソース修正とPython構文の検査 |

この例の `flake.nix` は単独でOSを構築するものではありません。
起動できるNixOSの `/etc/nixos/configuration.nix`、ハードウェア設定、T2ファームウェア等がすでにあることを前提にします。
それらの実機ファイルや既存の `flake.lock` はリポジトリに含めません。

## 固定している入力

- OS: 既存の `nixos-26.05` 入力とMacにある `flake.lock` を使用。
- デスクトップ: nixpkgs `151fa4e8ddfdd8dd25d945ad94ed54a13de9f6e4`。
- T2用nixpkgs: `567a49d1913ce81ac6e9582e3553dd90a955875f`。
- nixos-hardware: `875776f0252fcb8618bb948640a0d1f7a5b362be`。
- Impasto: 上流v0.5.0のコミット `6d759aa3fe16e3b40641beeb9b24e3c4afcfeefe` をこのforkから取得。

ここではHyprland 0.56.2・Quickshell 0.3.1・Kitty 0.49.2を使用します。
描画ライブラリとの世代差を避けるため、XwaylandやFirefox等も同じデスクトップ入力から選びます。
T2カーネルの入力をデスクトップ入力に追従させない構成です。

## 対応内容

- Impastoのバー・通知・ランチャー・壁紙・テーマ・ロックを導入。
- JIS配列、画面倍率2、画面とキーボードの明るさ操作。
- UWSMでアプリを起動し、`uwsm stop` でGUIを終了。
- パスが固定されたArch用の処理を、Nixのパッケージのパスへ修正。
- パスワード認証はNixOSの `security.pam.services.impasto` を使用。
- 導入前にユーザーの設定をバックアップ。

SDDM・顔認証・Hyprlandプラグイン・仮想マシン環境はこのアダプターの対象外です。
絵文字や配列名のデータは対応するnixpkgs属性がある場合に使用し、絵文字データがなければ検索結果は空になります。

## 既存のMBA2019構成への配置

まずファイルを読み、入力・ホスト名・既存モジュールが自分の構成に合うことを確認します。
すでに他の独自入力を追加している場合は、`flake.nix` をそのまま置き換えず変更を取り込んでください。

```bash
git clone --branch nixos-mba2019 https://github.com/emth361h/impasto.git
cd impasto

backup="/etc/nixos.before-impasto-$(date +%Y%m%d-%H%M%S)"
sudo cp -a /etc/nixos "$backup"
printf 'Backup: %s\n' "$backup"

sudo install -m 644 nix/flake.nix nix/impasto.nix nix/port.py nix/setup-user.py /etc/nixos/
sudo nix flake lock 'path:/etc/nixos'
```

新しいImpasto入力の追加は想定どおりです。すでに上流URLを使っていた場合、`impasto-src` の取得先だけがこのforkに変わります。
既存のOS/T2入力が意図せず更新されていないことを確認してから進みます。
`configuration.nix` や `hardware-configuration.nix`、ファームウェアを上書きする手順ではありません。

```bash
sudo nixos-rebuild boot --flake 'path:/etc/nixos#mba2019' \
  --option max-jobs 1 --option cores 2
```

成功した場合のみ作業を保存して再起動します。失敗したら、まずそのエラーを解消してください。

再起動後、Hyprlandを起動する前に通常ユーザーで実行します。

```bash
impasto-setup
uwsm start -g -1 -- hyprland.desktop
```

`impasto-setup` にsudoは付けません。通常のバックアップ先は
`~/.local/state/impasto-nixos-backups/日時/` です。
既存のHyprland/Quickshell設定を退避してから配置し、Kittyにはパレットのincludeを追加します。
テーマの変更はGTK・Qtなどの設定にも反映されるため、`~/.config` 全体をバックアップします。
初回のJIS配列、履歴無効、自動ロック等のタイマー0を保持するように初期設定を作ります。

## 起動後

| キー | 操作 |
|---|---|
| Cmd+Enter | Kitty |
| Cmd+Space | ランチャー |
| Cmd+A | クイック設定 |
| Cmd+T | 外観・壁紙 |
| Cmd+, | 詳細設定 |
| Cmd+Shift+E | CLIへ戻る |

```bash
hyprctl configerrors
impasto status
journalctl --user -b --no-pager | rg -i 'glamor|GBM|EGL|quickshell|impasto' | tail -n 60
```

パッケージをそろえただけでXwaylandの描画問題が直ったとは判断せず、新しいセッションのログで確認します。
ロック解除も別途確認が必要です。ロックのテスト時はSSH接続を残すと、失敗時に `uwsm stop` で終了して調査できます。

## 設定を戻す

NixOSの世代を戻しても、ホームディレクトリに配置した設定は戻りません。
GUIを終了し、バックアップ内の `config` と `locations.json` を確認します。
現在の設定を別名で退避したうえで、バックアップから元の設定を戻してください。
OS側の構成も戻す場合は `/etc/nixos.before-impasto-日時/` に保存した `flake.nix` と `flake.lock` を使います。

## 開発・検証

```bash
python3 nix/check-port.py
```

チェックは上流のスクリプトを実行せず、コピーしたソースに対する修正の適用とPython構文を検査します。
Windowsでこの検査を実行済みです。Nixのビルド内ではLua構文もチェックします。
Nixの評価・ビルド、Quickshellの表示、PAM認証、各周辺機能の実機確認は検証待ちです。

UI本体をこのforkで変更したときは、その変更を含むコミットを `impasto-src.url` に指定します。
現状は既知の上流コミットを固定しているため、`home/` を編集するだけではその編集はビルドへ入りません。
`port.py` と `impasto.nix` の変更は、Mac上の `/etc/nixos/` へ反映して再ビルドします。
`impasto-setup` の再実行はバックアップを作って設定を再配置するため、手編集した設定を先にコードへ取り込んでください。
