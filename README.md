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
   (Twingate account ids, etc.). Save the home CA certificate from Bitwarden as
   `vars/axis.lan-ca.crt` (gitignored; the CA step is skipped without it).
4. **Run it**: `./run.sh`. It asks for your password once (pkexec) for the root play, then runs
   the user and container plays. The containers play creates/configures the apx subsystems,
   builds the Gmail/Calendar/... web apps (several minutes the first time) and clones the
   quick-access fork.
5. **Log out and back in**, so GNOME loads the extensions and the new settings.
6. **Bitwarden / rbw**, once (in a terminal):
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
| `system.yml` / `system` | Home CA (`axis.lan`) in the host trust store and the Qt-Flatpak cert dir; udev rules so plugging in the dock, or the Bluetooth keyboard/mouse, wakes the laptop with the lid closed; Twingate client unpacked into `/usr/local` with a weekly updater timer, the `twingate-switch` root helper, and a polkit rule allowing passwordless pkexec of it; Bitwarden's polkit action (in `/usr/local/share/polkit-1/actions`) for unlocking with system authentication |
| `user.yml` / `cli_tools` | Pinned static binaries in `~/.local/bin`: eza, rg, bat, fzf, zoxide, fd, btop, lazygit, delta, yq, k9s |
| `user.yml` / `dotfiles` | `.bashrc`, `.bash_aliases` (incl. the `twingate`, `git_all`, apt helpers), `.inputrc`, `.gitconfig` (delta), `.ssh/config` (rbw SSH agent), git signing key + `allowed_signers` (read from rbw's agent; not stored in the repo), lazygit config |
| `user.yml` / `desktop` | Work/Personal launchers for Claude Desktop and Zed, Bitwarden menu entry, `claude://` and `bitwarden://` handlers, autostart (Bitwarden quick access hidden, which keeps rbw's SSH agent up; Bitwarden desktop hidden to tray, for the browser extension's biometric unlock (launched by `bitwarden-desktop`, which points it at the host's system D-Bus so it can reach polkit); Nextcloud), a native messaging host so the Bitwarden extension in every Flatpak Chrome profile reaches the desktop app in `apx-bitwarden`, SSH only through rbw's agent (session `SSH_AUTH_SOCK` via environment.d; GNOME's and OpenSSH's agents masked), `power-profile-auto` service (AC: performance, battery: balanced), Hatter icons + weekly updater, `Adwaita-NoBusy` cursor theme (no spinner cursor; a full copy so Flatpaks can read it, via a global Flatpak override), `xcursor-refresh` service (re-applies the cursor size after login and monitor changes, so X11 apps don't keep a double-size pointer), sleep after 15 idle minutes on AC too (waking re-lights the dock monitors), screenshots (GNOME's Print tool, screenshot shortcuts Shift+Alt+3 (window) / 4 (screenshot UI) / 5 (edit last in Gradia), no "Screenshot captured" notifications (local `quiet-screenshots` extension), portal screenshots moved into `~/Pictures/Screenshots`), Nerd Fonts, Flatpak apps + overrides, Ptyxis terminal (opens tmux in `apx-vso-native`), GNOME extensions/settings/shortcuts (incl. `displays-reset` on Super+Alt+D / Super+Alt+Shift+D for dock monitors that stay dark), `zoom-bt-mic` user service (laptop mic is the default; while a call app such as Zoom, Slack, Messenger, Chrome/Meet, Discord, Webex or Teams records, the default mic becomes the connected Bluetooth headset, so headsets stay in high-quality A2DP outside calls), twingate-panel, Twingate account ids, shared Zed config |
| `user.yml` / `apx_host` | Creates the `claude-work`, `claude-personal`, `bitwarden` and `ansible` subsystems (`ansible` shares the host `$HOME`) |
| `containers.yml` / `apx_container` | Claude Desktop, claude CLI, Node, Zed and the shared Zed config link in both Claude subsystems; Bitwarden .deb; rbw (also the SSH agent for SSH and git signing), the keyring-backed `pinentry-keyring` and the `rbw-quick-access` fork checkout for Bitwarden quick access (Ctrl+Shift+Space); `xdg-open` → host `gio`; a managed block in each Claude subsystem's `~/.bashrc` that sources the host `~/.bashrc`; in every subsystem gh (GitHub apt repo, logged in from whichever subsystem already is; git credential helper) and a common package set (git, curl, jq, file, neovim, dig, shellcheck, unzip); apt cache fix |
| `containers.yml` / `devops_tools` | In the dev subsystems (`apx_dev`: both Claude subsystems, `ansible`, `vso-native`): Terraform, terraform-ls, Packer, Vault, Consul, Nomad, Boundary (HashiCorp apt repo), kubectl (pkgs.k8s.io, minor pinned), Helm, AWS CLI v2, gcloud (+ GKE auth plugin), Azure CLI, Ansible + ansible-lint, yamllint, Go, Node + npm, Hugo, build-essential, python3-venv/pip, pipx, git-lfs, tmux, httpie and network tools |
| `containers.yml` / `vso_native` | In the OS-provided `apx-vso-native`: tmux, git, neovim, jq; `~/.tmux.conf` and its plugins (TPM, tmux-sensible); Node and the [electron-apps](https://github.com/mtharpe/electron-apps) web apps (Gmail, Calendar, Tasks, Keep, Messages, Messenger), built here into `~/.local` |

## Not automated (do by hand)

- **Flatpak Chrome's CA**: Chrome uses its own NSS DB. With Chrome closed, from an apx
  container with `libnss3-tools`:
  `certutil -d sql:$HOME/.var/app/com.google.Chrome/data/pki/nssdb -A -t C,, -n "axis.lan CA" -i vars/axis.lan-ca.crt`
  (use `/home/<user>/...` explicitly; `~` in a container is its own home).
- **Bitwarden biometric unlock**: in the desktop app, Settings → turn on "Unlock with system
  authentication" and "Allow browser integration"; then in each Chrome profile, the extension's
  Settings → Account security → "Unlock with biometrics".
- **Sign-ins**: Twingate accounts (`twingate add`), Claude in each profile, Nextcloud, the web
  apps (Gmail etc.), the Bitwarden browser extension; rbw as in step 6 above.
- **Zed's default agent**: Zed keeps the last-used agent in its per-profile state DB; pick
  "Claude Agent" once in each profile.
- **GNOME extensions** installed or enabled here load at the next login (Wayland).
