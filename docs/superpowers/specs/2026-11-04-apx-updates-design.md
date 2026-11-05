# Automatic APX updates

User chose fully automatic maintenance with no regular intervention.

Use a daily persistent systemd user timer, matching existing desktop update timers. Discover APX-managed containers and the existing apx-prefixed Distrobox container each run; initialize/start stopped containers, then update sequentially. Update APT/DNF packages noninteractively, preserving config files and version holds. Run installed native Claude/Codex updaters as the desktop user, with the correct container home. Keep application self-updates (Zed) enabled. Never recreate containers, reboot, or restart running apps.

Failures must not prevent other containers/tools from being attempted. Return failure to systemd, notify locally, retry through systemd, and keep journal logs. Serialize manual and scheduled runs. Bound network and package-lock waits. Unsupported package managers fail visibly.

Approaches considered: manual APX upgrades require recurring management; per-container timers duplicate scheduling; one host user timer discovers containers and centralizes logs, so use that. Maintain installation in the workstation Ansible role and remove personal Claude from local/example subsystem lists; preserve work-only launchers in the role.

Scope: distribution packages and installed native AI CLIs. Vendor-pinned/downloaded DevOps binaries retain their existing version policy. No distribution release migrations or host OS/Flatpak updates.
