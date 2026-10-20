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

## What it manages

| Play / role | What |
|---|---|
| `system.yml` / `system` | Home CA (`axis.lan`) in the host trust store and the Qt-Flatpak cert dir; udev rule so plugging in the dock wakes the laptop with the lid closed; Twingate client unpacked into `/usr/local` with a weekly updater timer, the `twingate-switch` root helper, and a polkit rule allowing passwordless pkexec of it |
| `user.yml` / `cli_tools` | Pinned static binaries in `~/.local/bin`: eza, rg, bat, fzf, zoxide, fd, btop, lazygit, delta |
| `user.yml` / `dotfiles` | `.bashrc`, `.bash_aliases` (incl. the `twingate`, `git_all`, apt helpers), `.inputrc`, `.gitconfig` (delta), `.ssh/config` (rbw SSH agent), lazygit config |
| `user.yml` / `desktop` | Work/Personal launchers for Claude Desktop and Zed, Bitwarden menu entry, `claude://` and `bitwarden://` handlers, autostart (Bitwarden quick access hidden, which keeps rbw's SSH agent up; Nextcloud), `power-profile-auto` service (AC: performance, battery: balanced), Hatter icons + weekly updater, screenshots (GNOME's Print tool, Gradia editor on Alt+5, no "Screenshot captured" notifications (local `quiet-screenshots` extension), portal screenshots moved into `~/Pictures/Screenshots`), Nerd Fonts, Flatpak apps + overrides, GNOME extensions/settings/shortcuts, twingate-panel, Twingate account ids, shared Zed config |
| `user.yml` / `apx_host` | Creates the `claude-work`, `claude-personal` and `bitwarden` subsystems |
| `containers.yml` / `apx_container` | Claude Desktop, claude CLI, Node, Zed and the shared Zed config link in both Claude subsystems; Bitwarden .deb plus rbw and the deps for Bitwarden quick access (`rbw-quick-access` fork, Ctrl+Shift+Space); `xdg-open` → host `gio`; apt cache fix |
| `containers.yml` / `vso_native` | In the OS-provided `apx-vso-native`: tmux, git, neovim, jq; `~/.tmux.conf` and its plugins (TPM, tmux-sensible) |

## Not automated (do by hand)

- **Flatpak Chrome's CA**: Chrome uses its own NSS DB. With Chrome closed, from an apx
  container with `libnss3-tools`:
  `certutil -d sql:$HOME/.var/app/com.google.Chrome/data/pki/nssdb -A -t C,, -n "axis.lan CA" -i roles/system/files/axis.lan-ca.crt`
  (use `/home/<user>/...` explicitly; `~` in a container is its own home).
- **Sign-ins**: Twingate accounts (`twingate add`), Claude in each profile, Bitwarden, Nextcloud.
  For quick access, in apx-bitwarden: `rbw config set email <email>` then `rbw login`.
- **Quick access checkout**: clone the `rbw-quick-access` fork to `~/src/github/mtharpe/rbw-quick-access`.
- **Zed's default agent**: Zed keeps the last-used agent in its per-profile state DB; pick
  "Claude Agent" once in each profile.
- **GNOME extensions** installed or enabled here load at the next login (Wayland).
- **Ptyxis profile** that opens tmux in `apx-vso-native`.
