# Maintenance optimization implementation plan

User approved automatic image retention, background build priority and Chrome Memory Saver. Power-profile switching and battery settings must remain unchanged.

1. Test a conservative image selector and mocked apply path before implementation: allowlist the two existing allowlisted registry repositories, keep five newest numbered rel-v releases per repository, retain all IDs with any other tag/name, local images and every image referenced by running/stopped containers. Require image creation to be at least 24h old. Unknown metadata and failed discovery must prevent deletion. No system/container/volume prune. Separate default-dangling-only image cleanup has a seven-day age filter and excludes tagged local images and external build containers. Default to dry-run. Recheck references immediately before deletion and remove only validated release references with --no-prune and no rmi force.
2. Implement Python runner using the existing host /usr/bin/python3 interpreter; schedule daily persistent systemd user timer, serialize runs, lower resource priority and notify on failure. Preserve current APX updater and all existing repository edits.
3. Add Nice=10, CPUWeight=20, IOWeight=20 and IOSchedulingClass=idle to automatic Hylki build service; do not restart a running build.
4. While Chrome is closed, atomically update only browser-wide performance_tuning.high_efficiency_mode.state=2 and aggressiveness=1 in Local State; back up the existing state privately and preserve every other preference and all profile data. Browser setting is persistent and user-adjustable.
5. Verify tests, shell/unit/Ansible syntax, live dry-run and scheduled runner; verify installed unit properties and Chrome JSON delta. Independently review retention safety before enabling deletions.

## Verification and review

Independent review identified deletion-by-ID retagging risk, implicit parent deletion, and malformed-date/tag-field handling. Reproducing tests failed before fixes. Switched release deletion to explicit tag/digest references with --no-prune; introduced separate seven-day dangling-only cache expiry to prevent build layer accumulation while preserving tagged local/test images. Date checks reject non-finite values; both tag metadata fields are validated and combined. Final retention tests: 15 passed, plus 11 existing APX updater tests.

Chrome's existing Local State was backed up privately and changed atomically while closed. Exact JSON diff contains only memory-saver state=2 and aggressiveness=1. No battery or power-profile preference was changed.

Deployment verified: retention service completed successfully (ExecMainStatus=0), no additional old images eligible after cleanup, timer active for daily 03:00–04:00 local runs. Live Hylki unit properties: Nice=10, CPUWeight=20, IOWeight=20, IOSchedulingClass=3 (idle). All 26 tests passed, systemd unit and Ansible user playbook syntax verified. Installed files match the role sources. Power-profile helper has no diff. No Git commit was made because the checkout contains pre-existing unrelated work.
