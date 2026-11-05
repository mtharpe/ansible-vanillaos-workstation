# Zed dual-agent and workstation Ansible plan

User wants Claude and Codex in Zed and all machine changes represented/documented in workstation Ansible. Preserve work/personal homes and authentication, Zed custom preferences, immutable host and existing power management.

1. Install the current official Codex ACP adapter in apx-codex, using its existing ChatGPT login/home; add installation to codex role and adapter updates to daily APX maintenance.
2. Add a stdio-safe Zed bridge from apx-claude-work to apx-codex via host Podman, preserving working directory and arguments. Add a custom Codex (Personal) agent while keeping Claude's existing registry agent.
3. Add a tested JSONC settings merge helper. Preserve unrelated settings/comments, recursively merge only managed agent entries. Represent Chrome Memory Saver in Ansible; skip writes while Chrome is running unless the desired values are already present. Keep backups private.
4. Reconcile role source seed settings and live Zed settings. Deploy scoped changes, verify ACP initialize/session setup without sending a model prompt, and check Ansible syntax and idempotence.
5. Document configuration, cleanup history and remaining manual lifecycle operations in README/machine-maintenance notes. Verify the existing update/retention timers, immutable system masks, work-only launchers, removed-container declarations, background build priority and Chrome prefs all have matching role tasks/files. Do not delete application data or commit unrelated existing work.

## Completed verification

Codex ACP2.5.0 and existing Claude ACP0.93.0 each passed ACP initialize and authenticated session/new from apx-claude-work. Codex requests traversed the actual shared bridge into apx-codex. No model prompt was sent; stdin closure shut down verification sessions.

All 36 tests passed. Shellcheck, git diff whitespace and container-playbook syntax checks passed. Tagged user-play deployment completed twice with changed=0 and failed=0. Reviewer found first-run --check used an uninstalled helper: reproduced failure using an empty temporary home, changed check mode to execute current role source, and verified success with no helper/settings writes. ACP install remains in the normal container play because it needs container-home facts.

Confirmed installed launcher/settings/update/retention helpers and systemd units match role sources; retired containers are absent from local/example subsystem declarations; immutable-host masks and timers match documented configuration. Existing power-profile service remains active and unchanged. Consolidated history and account setup are in README.md. Existing unrelated working-tree edits were preserved; no commit or push was performed.
