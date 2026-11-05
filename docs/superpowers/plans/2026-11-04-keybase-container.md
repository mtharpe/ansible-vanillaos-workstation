# Dedicated Keybase Debian container

User explicitly requests Keybase in its own APX Debian container, without development tools or other applications. Use apx-keybase, separate home ~/.apx-homes/keybase. Keep the immutable host unchanged; GNOME integration is through a host launcher, icon and desktop/URI entry.

1. Add the Keybase subsystem declaration and inventory group, excluding it from apx_dev. Route it to a dedicated setup path before shared home/.ssh/git/common CLI tasks. Base Debian/Distrobox and Ansible runtime dependencies only.
2. Install official stable Debian package and its signed APT repository inside the container. Verify package signature/signing fingerprint; normal daily APX updates maintain it. Configure container-local processes, avoiding host systemd user-unit execution. Use host URL opening and install only required desktop dependencies.
3. Add launcher with separate container runtime/home and GNOME desktop entry/icon, URI handling and normal window behavior. Do not enable host login autostart unless needed/requested; user signs in through GUI.
4. Create/install through APX and scoped Ansible, verify CLI/package/repository state, launch GUI and inspect logs/processes, validate host desktop entry and Ansible idempotence. Do not change other accounts, power management or host OS packages.

## Verification

Dedicated Debian13 apx-keybase created with home mode0700. APX autoconfig applied the application-only role and skipped devops/shared workstation setup. Official Keybase6.6.3 signature and pinned primary key verified, signed HTTPS APT repository refresh passed. GUI, service and KBFS report running; no account was signed in by the agent. Keybase CLI wrapper passed a live keybase --version call from apx-vso-native. Claude/Codex/Zed/npm/Terraform/kubectl and shared .ssh/.gitconfig are absent from the new container.

Independent review found cold-start URI loss, fresh check-mode artifact reads and bundled-key trust scope. Cold-start URI regression reproduced RED, fixed by starting backend/KBFS with run_keybase -g then executing the GUI with all arguments; warm/cold tests GREEN. Bootstrap verification is skipped in check mode; planned installation is reported without reading nonexistent downloads. Verification keyring exports only the pinned primary fingerprint. Final suite38 tests passed; Bash/shellcheck/desktop validation passed. Second pre-review Ansible apply had changed=0; final apply changed only the corrected entrypoint. Installed-container check mode validates the final configuration. No host OS or power-profile changes were made.
