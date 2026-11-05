# Vanilla OS Workstation

Ansible for my Vanilla OS 3 laptop (ThinkPad T14s Gen 6, GNOME on Wayland). It records what was
set up by hand on this machine so it can be rebuilt or kept in sync.

Vanilla OS is immutable (`/usr` is read-only under ABRoot) and the host has **no sudo, pip, git
or sshd**. So:

- Ansible runs on the host from a repo-local venv that `run.sh` builds with a pinned
  [uv](https://github.com/astral-sh/uv) (uv also supplies the Python).
- Root-level work is one play (`system.yml`) run under `pkexec`: one password prompt.
- Root changes only touch `/etc`, `/var` and `/usr/local` (= `/var/usrlocal`, kept across ABRoot updates).
- The apx subsystems are configured with the `containers.podman` connection (`podman exec`).
  They aren't listed anywhere: `inventory/apx.podman_containers.yml` finds every container apx
  made, so a subsystem created by hand (apx CLI or GUI) gets the same setup. The
  `apx-autoconfig` user service runs the containers play on each new one as soon as distrobox
  has finished its first start (`journalctl --user -fu apx-autoconfig`). Subsystems must be
  Debian/Ubuntu-based (everything is apt).
- What's shared vs. per subsystem: tools are installed in each subsystem (same set everywhere,
  except Bitwarden and 1Password skip the DevOps set) plus the static binaries in the host `~/.local/bin`. A
  subsystem with its own home includes the host `.bashrc` and `.gitconfig`, and its `~/.ssh` is a
  symlink to the host's (one SSH config, known_hosts and signing key everywhere).
  Logins are per home and never linked: gh's account file, `~/.docker`, and the cloud CLIs
  (`~/.aws`, `~/.config/gcloud`, `~/.azure`, `~/.kube`, `~/.terraform.d`). Make work and
  personal subsystems with separate homes (`apx subsystems new -n <name> -s ubuntu -H
  ~/.apx-homes/<name>`); a subsystem without `-H` shares the host home's logins with
  `vso-native` and `ansible`.

## Usage

```sh
cp vars/vars.example.yml vars/vars.yml   # gitignored; fill in Twingate account ids etc.
./run.sh                    # system (pkexec), then user, then containers
./run.sh user --check --diff
./run.sh system | user | containers
```

`run.sh` works from a terminal inside an apx container too (it re-runs itself on the host via
`host-spawn`).

## Rebuilding this machine

1. **Install Vanilla OS 3**, create the user `tharpem`, and log in to GNOME. The OS creates
   `apx-vso-native`; the default terminal (Ptyxis) opens in it.
2. **Get this repo.** The host has no git, so clone from `apx-vso-native`, which shares your
   home (and has passwordless sudo):
   ```sh
   sudo apt install -y git
   git clone https://github.com/mtharpe/ansible-vanillaos-workstation.git ~/src/github/mtharpe/ansible-vanillaos-workstation
   ```
   (Private repo: sign in first with `gh auth login`, or clone with a token.)
3. **Fill in the vars**: `cp vars/vars.example.yml vars/vars.yml` and set the real values
   (Twingate account ids, etc.). `password_manager` picks what serves SSH keys, git signing
   and Ctrl+Shift+Space quick access: `1password` (default) or `bitwarden` (rbw's agent and
   the rbw-quick-access fork). Save the home CA certificate from 1Password as
   `vars/axis.lan-ca.crt` (gitignored; the CA step is skipped without it).
4. **Run it**: `./run.sh`. It asks for your password once (pkexec) for the root play, then runs
   the user and container plays. The containers play creates/configures the apx subsystems,
   builds the Gmail/Calendar/... web apps (several minutes the first time) and, with
   `password_manager: bitwarden`, clones the quick-access fork.
5. **Log out and back in**, so GNOME loads the extensions and the new settings.
6. **1Password**: open it from the app menu and sign in. Settings → Security → turn on
   "Unlock using system authentication"; Settings → Developer → turn on "Use the SSH agent"
   (the SSH key must be an SSH Key item in the Personal vault). SSH and git signing work once
   it's unlocked. Then re-run `./run.sh user`: it reads the git signing key from 1Password's
   agent, which wasn't available on the first run.

   With `password_manager: bitwarden` instead, set up rbw once (in a terminal):
   ```sh
   host-shell /usr/share/apx/distrobox/distrobox-enter -n apx-bitwarden -- sh -c 'rbw config set email <email> && rbw register && rbw login'
   ```
   `rbw register` asks for the personal API key (web vault: Settings → Security → Keys → View
   API key); Bitwarden rejects rbw's plain login as a new device. The master password typed
   at the first unlock is saved in the GNOME keyring, so later unlocks (including after a
   reboot) need no typing. SSH and git signing work once rbw is unlocked. Then re-run `./run.sh user`: it reads the
   git signing key from rbw's agent, which wasn't available on the first run.
7. **Sign in** to everything else listed under "Not automated" below.
8. **Check**: `./run.sh --check --diff` should report no changes.

## What it manages

| Play / role | What |
|---|---|
| `system.yml` / `system` | Home CA (`axis.lan`) in the host trust store and the Qt-Flatpak cert dir; udev rules so plugging in the dock, or the Bluetooth keyboard/mouse, wakes the laptop with the lid closed; Twingate client unpacked into `/usr/local` with a weekly updater timer, the `twingate-switch` root helper, and a polkit rule allowing passwordless pkexec of it; 1Password on the host (`1password-host-update`: the signed tarball in `/opt/1Password` and `op` in `/usr/local/bin`, the post-install groups and setuid/setgid bits, a `chrome-flatpak` stand-in in `custom_allowed_browsers` so Flatpak Chrome's extension can connect, and a weekly update timer; not in an apx subsystem because its system authentication unlock refuses the host's D-Bus as seen from a rootless container); Bitwarden's and 1Password's polkit actions (in `/usr/local/share/polkit-1/actions`) for unlocking with system authentication; a polkit rule letting the desktop user change the time zone; YubiKey on the lock screen (Debian's `pam_u2f` unpacked into `/usr/local`, keys from `yubikey_u2f_keys` in `/etc/security/u2f_keys`, tried before the password in `gdm-password` only while the session is locked, so the first login still takes the password and unlocks the keyring) and `yubikey-enroll-disk` for the boot-time disk unlock |
| `user.yml` / `cli_tools` | Pinned static binaries in `~/.local/bin`: eza, rg, bat, fzf, zoxide, fd, btop, lazygit, delta, yq, k9s |
| `user.yml` / `dotfiles` | `.bashrc`, `.bash_aliases` (incl. the `twingate`, `git_all`, apt helpers), `.inputrc`, `.gitconfig` (delta), `.ssh/config` and `~/.config/ssh-agent.bash` (the chosen password manager's SSH agent), git signing key + `allowed_signers` (read from that agent; not stored in the repo), lazygit config |
| `user.yml` / `desktop` | Work-account launchers for Claude Desktop and Zed, 1Password and Bitwarden menu entries (`1password-desktop` / `bitwarden-desktop` point the apps at the host's system D-Bus so they can reach polkit), `claude://`, `bitwarden://` and `onepassword://` handlers, quick access on Ctrl+Shift+Space (1Password Quick Access, or Bitwarden quick access via rbw; Bitwarden desktop on Ctrl+Alt+Shift+Space), autostart per `password_manager` (1Password in the tray with no window, which keeps its SSH agent up; or Bitwarden quick access hidden, which keeps rbw's agent up, plus Bitwarden desktop in the tray; Nextcloud), native messaging hosts so the 1Password and Bitwarden extensions in every Flatpak Chrome profile reach the desktop apps (1Password on the host, Bitwarden in `apx-bitwarden`), SSH only through the chosen password manager's agent (session `SSH_AUTH_SOCK` via environment.d; GNOME's and OpenSSH's agents masked), `power-profile-auto` service (AC: performance, battery: balanced), `podman.socket` (Docker API for the subsystems) and the `apx-autoconfig` service (sets up new apx subsystems), Hatter icons + weekly updater, ArtCraft Craft apps (PhotoCraft, VectorCraft, LightCraft, FilmCraft, EffectCraft, DesignCraft, PdfCraft, CADCraft, FigCraft, SoundCraft: Flatpak bundles from GitHub, not Flathub) + weekly `update-craft-apps` timer, `Adwaita-NoBusy` cursor theme (no spinner cursor; a full copy so Flatpaks can read it, via a global Flatpak override), `xcursor-refresh` service (re-applies the cursor size after login and monitor changes, so X11 apps don't keep a double-size pointer), sleep after 15 idle minutes on AC too (waking re-lights the dock monitors), screenshots (GNOME's Print tool, screenshot shortcuts Shift+Alt+3 (window) / 4 (screenshot UI) / 5 (edit last in Gradia), no "Screenshot captured" notifications (local `quiet-screenshots` extension), banner-only notifications (local `banner-only-notifications` extension: apps picked in its settings, Slack by default, pop up but are not kept in the notification list), portal screenshots moved into `~/Pictures/Screenshots`), Nerd Fonts, Flatpak apps + overrides, Ptyxis terminal (opens tmux in `apx-vso-native`), GNOME extensions/settings/shortcuts (incl. `displays-reset` on Super+Alt+D / Super+Alt+Shift+D for dock monitors that stay dark), `zoom-bt-mic` user service (laptop mic is the default; while a call app such as Zoom, Slack, Messenger, Chrome/Meet, Discord, Webex or Teams records, the default mic becomes the connected Bluetooth headset, so headsets stay in high-quality A2DP outside calls), per-headset Bluetooth codec profile and latency offset in WirePlumber's state (`bt_audio_devices` in `vars.yml`, by Bluetooth address: the Pixel Buds Pro 2 on SBC-XQ at −100 ms, which keeps YouTube in Chrome in sync), `bt-av-resync` user service (when a multipoint switch brings a Bluetooth headset back, pauses and resumes what's playing so Chrome re-reads its latency), twingate-panel, Twingate account ids, shared Zed config |
| `user.yml` / `apx_host` | Creates the `claude-work`, `codex` and `ansible` subsystems (`ansible` shares the host `$HOME`) |
| `containers.yml` / `apx_container` | Claude Desktop, claude CLI, Node, Zed and the shared Zed config link in the work Claude subsystem; Bitwarden .deb; with `password_manager: bitwarden`, rbw (then the SSH agent for SSH and git signing), the keyring-backed `pinentry-keyring` and the `rbw-quick-access` fork checkout for Bitwarden quick access; `xdg-open` → host `gio`; in every subsystem with its own home, managed blocks that include the host `.bashrc` and `.gitconfig`, and `~/.ssh` linked to the host's; Python bootstrap and an apt check; in every subsystem gh (GitHub apt repo, logged in from whichever subsystem already is; git credential helper) and a common package set (git, curl, jq, file, neovim, dig, shellcheck, unzip); apt cache fix |
| `containers.yml` / `devops_tools` | In every subsystem but Bitwarden (`apx_dev`): Terraform, terraform-ls, Packer, Vault, Consul, Nomad, Boundary (HashiCorp apt repo), kubectl (pkgs.k8s.io, minor pinned), Helm, AWS CLI v2, gcloud (+ GKE auth plugin), Azure CLI, Docker CLI + buildx + compose (a `host-podman` context on the host's rootless podman socket, `podman.socket` enabled by `desktop`; builds run in a BuildKit container on host podman and load into it), Ansible + ansible-lint, yamllint, Go, Node + npm, Hugo, build-essential, python3-venv/pip, pipx, git-lfs, tmux, httpie and network tools |
| `containers.yml` / `vso_native` | In the OS-provided `apx-vso-native`: tmux, git, neovim, jq; `~/.tmux.conf` and its plugins (TPM, tmux-sensible), `tmux-split` (prefix `|` / `-` split a pane that has entered another subsystem into that same subsystem); Node and the [electron-apps](https://github.com/mtharpe/electron-apps) web apps (Gmail, Calendar, Tasks, Keep, Messages, Messenger), built here into `~/.local` |

## Not automated (do by hand)

- **Flatpak Chrome's CA**: Chrome uses its own NSS DB. With Chrome closed, from an apx
  container with `libnss3-tools`:
  `certutil -d sql:$HOME/.var/app/com.google.Chrome/data/pki/nssdb -A -t C,, -n "axis.lan CA" -i vars/axis.lan-ca.crt`
  (use `/home/<user>/...` explicitly; `~` in a container is its own home).
- **Bitwarden biometric unlock**: in the desktop app, Settings → turn on "Unlock with system
  authentication" and "Allow browser integration"; then in each Chrome profile, the extension's
  Settings → Account security → "Unlock with biometrics".
- **1Password in Chrome**: install the 1Password extension in each Chrome profile. With the
  app running it picks up the app's sign-in through the native messaging bridge; the app may
  ask to confirm the new browser connection the first time.
- **Sign-ins**: Twingate accounts (`twingate add`), Claude in each profile, Nextcloud, the web
  apps (Gmail etc.); 1Password or rbw as in step 6 above.
- **Zed's default agent**: Zed keeps the last-used agent in its per-profile state DB; pick
  "Claude Agent" once in each profile.
- **YubiKey disk unlock at boot**: after `./run.sh system`, run
  `host-shell pkexec /usr/local/sbin/yubikey-enroll-disk` in a terminal. It asks for the disk
  passphrase, adds a FIDO2 keyslot (touch only, no PIN) to the encrypted `/var`, and tests it.
  The passphrase keyslot stays. At boot, press Enter at the passphrase prompt and touch the
  key, or type the passphrase. This works because Vanilla's `abroot unlock-var` runs a plain
  `cryptsetup luksOpen`, which tries FIDO2 tokens before the passphrase. A new key for the lock
  screen: `pamu2fcfg -u "$USER" -o pam://tharpem-laptop -i pam://tharpem-laptop`, then add
  the line to `yubikey_u2f_keys` (keep `vars.yml` backed up; it holds the registration).
- **GNOME extensions** installed or enabled here load at the next login (Wayland).

## Automatic APX updates

`update-apx-containers.timer` updates containers daily, catches up after downtime, and retries failed runs up to twice at hourly intervals. It discovers APX-managed containers and older `apx-*` Distrobox containers (including Bitwarden), initializes/starts stopped ones, and updates APT/DNF packages sequentially. Installed native Claude and Codex CLIs update as the container user, using that user's home. The installed Codex ACP adapter is updated separately through its npm package. Zed retains its existing self-updater. Running applications/containers are not restarted, and containers started for maintenance remain available.

APT configuration files and package holds are preserved; package removal, distribution release migrations and container recreation are excluded. Manually installed/pinned DevOps binaries retain their existing update policy. Unsupported package managers and failed repository refreshes cause a visible failure, while remaining containers are still attempted. Failures produce a desktop notification and journal logs. Concurrent manual/timer runs are serialized.

Inspect: `systemctl --user list-timers update-apx-containers.timer` and `journalctl --user -u update-apx-containers.service`. Run immediately with `systemctl --user start update-apx-containers.service`. The desktop role installs/enables the updater; no recurring manual action is needed.

## Immutable host startup

The system role masks host `apt-daily`/`apt-daily-upgrade` services and timers only on a read-only Vanilla OS base without executable host APT. ABRoot remains responsible for OS updates, and the APX package updater is unaffected. When NetworkManager is active and networkd reports every link unmanaged, it also masks `systemd-networkd-wait-online.service`, avoiding its two-minute boot timeout. NetworkManager and networkd themselves remain available. Masks live in `/etc/systemd/system`, without changing `/usr` or the base image. To undo, unmask the five units; the prior enablement links are retained.

## Background build priority and image retention

Automatic Hylki builds use `Nice=10`, `CPUWeight=20`, `IOWeight=20` and idle I/O scheduling. Foreground applications take priority during contention; builds remain automatic and no power-profile settings change.

`retain-container-images.timer` runs daily around 03:00–04:00 local time and catches up after downtime. It only considers numbered `scu-vN` releases in the existing Moodle and Moodle staging-tools ECR repositories, keeps the five newest version numbers per repository, and gives new images a 24-hour grace period. Any other tag, local image alias, unknown repository digest, unknown creation time or container reference preserves the entire image. All running/stopped container references and tags are checked again before each deletion. It removes only the selected release tags/digests without force or implicit parent pruning, so a concurrently added local tag survives. A separate Podman cleanup expires unused, untagged images older than seven days; tagged local images, container/volume data and active external build containers are preserved. It never performs system/container/volume pruning. Unknown digest-only release images are retained for manual review.

The script defaults to dry-run: `~/.local/bin/retain-container-images`. The timer uses `--apply`; failures are logged and notified. Inspect with `journalctl --user -u retain-container-images.service`.

The desktop role merges Chrome Memory Saver at its Balanced level into the Flatpak browser's existing `Local State` file. Only the two memory-saver preferences are managed; site exceptions and battery settings stay user-owned. An already-configured browser needs no rewrite. If Chrome is running and an update is needed, the task reports deferral rather than overwriting live preferences; close Chrome and rerun the user play. Settings remain adjustable in Chrome Settings → Performance. New helper backups are private under `~/.local/state/workstation-settings/`; the original one-time backup remains under `~/.local/state/chrome-memory-saver/`.

## Zed with work Claude and personal Codex

Zed continues to launch in `apx-claude-work`. In the Agent Panel's new-thread menu choose **Claude Agent** for the work account or **Codex (Personal)** for the personal ChatGPT account. Both use external ACP agents; no Zed model/API subscription is required for these existing agent logins. `claude-acp` remains the registry integration already configured in Zed.

The Codex entry invokes `~/.local/bin/zed-codex-acp`. It starts `apx-codex` if needed and uses host Podman with interactive stdin and no terminal allocation to relay ACP. Working-directory and command arguments are preserved. The adapter runs as the desktop user with the Codex container's own `HOME`, `CODEX_HOME` and native `CODEX_PATH`; credentials are never copied into the Claude home or committed to Ansible. The maintained `@agentclientprotocol/codex-acp` package is installed in the Codex user's `~/.local` by `apx_container/tasks/codex.yml` and kept current by the daily updater.

`desktop/tasks/launchers.yml` seeds shared Zed settings for new installs, then merges the two managed agent entries into existing `~/.apx-homes/zed-config/settings.json`. Other agents, Claude options, fonts/themes and unrelated preferences survive. JSONC comments outside edited objects are retained, writes are atomic and backups private. The settings helper also supports Ansible check mode. Zed detects settings changes automatically; reopening the Agent Panel or starting a new thread loads the agents.

Reapply helpers/agent entries and Chrome preferences on an existing machine with `./run.sh user --tags agent_setup`. Normal `./run.sh user containers` also provisions the containers and installs the Codex adapter on a new machine. Native agent account sign-in remains a user action; existing work Claude and personal ChatGPT logins are reused.

## Machine maintenance changes recorded on 2026-11-04

| Change | Ansible representation |
|---|---|
| Claude uses only work; Zed supports both accounts | Work-only launchers/menu entries, dotfiles Bash wrapper, Zed settings merge and Codex ACP container installation |
| Retired personal Claude and Bitwarden containers | Excluded from the current `apx_subsystems` declarations; `password_manager: 1password`. Optional Bitwarden role support remains available but is inactive |
| Daily APX package/native tool updates | Desktop helper, systemd service/timer and installation/enablement tasks |
| Daily image retention | Tested Moodle release retention helper and systemd service/timer; preserves recent releases, tagged local images and container/volume data |
| Immutable-host startup fixes | `roles/system/tasks/immutable_host.yml`: guarded `/etc/systemd/system` masks, with ABRoot and NetworkManager preserved |
| Automatic Hylki build priority | Resource settings in `update-hylki-custom.service` |
| Chrome Memory Saver | Desktop role and tested settings merge helper; memory preferences only |

The approved one-time disk cleanup recovered about 111 GiB: retired personal-Claude home data, Chrome caches, Hylki/Calendar build outputs, Trash and old local copies of registry releases/build layers. These data deletions are documented history, not destructive Ansible tasks that repeat on each run. Project source, application databases, current containers and volumes were retained. Cleanup manifests/results are in `~/.local/state/machine-cleanup/20261104-171518/`. Automatic retention now handles future image buildup.

The native Vanilla OS host update check reported no available system image update. Its existing `vanilla-updates.timer` remains enabled. Battery management and the existing automatic power-profile switching were left unchanged.

## Keybase in its own Debian container

`apx_subsystems` includes `keybase` with the Debian stack and its private `~/.apx-homes/keybase` home. Inventory excludes it from `apx_dev`; the container role takes an application-only branch before shared shell/git/SSH settings or common development tools. Only Debian/Distrobox base dependencies, Ansible's package runtime, Keybase and its GUI requirements are installed. Claude, Codex, Zed and DevOps packages remain in their existing containers.

The Keybase role verifies the [official Debian package](https://keybase.io/docs/the_app/install_linux)'s detached signature against the [published signing-key fingerprint](https://book.keybase.io/docs/server/our-code-signing-key) (`222B85B0F90BE2D24CFEB93F47484E50656D16C7`), installs the package, and uses its scoped signing key over HTTPS for future APT updates. The existing daily APX maintenance discovers this container automatically. The immutable Vanilla OS host gets no Keybase packages.

Open **Keybase** from GNOME's application grid, or use the Bash function: `keybase` opens its GUI; `keybase login`, `keybase status`, `keybase --version`, etc. run the CLI in the same container with arguments and working directory preserved. Existing terminals need `source ~/.bashrc` once. The host launcher and URL handlers route into the dedicated container. Keybase runs as container processes with `KEYBASE_SYSTEMD=0`; it never starts host Keybase systemd units. The optional root `/keybase` redirector is disabled, leaving any KBFS mount in the container. Host login autostart is not enabled.

Account sign-in is completed in Keybase's GUI or CLI and stored only in the Keybase home; credentials are not part of Ansible. Reapply with the normal user and container plays.
