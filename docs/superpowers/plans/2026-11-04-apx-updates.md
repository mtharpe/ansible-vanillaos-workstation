# Automatic APX Updates Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement inline.

**Goal:** Automatic daily maintenance of the existing APX containers.
**Architecture:** A host Bash runner discovers containers, sends itself to each for package and user-tool updates, and reports failures to a systemd user service/timer.
**Tech Stack:** Bash, Podman/Distrobox, systemd, Ansible.
**Spec:** docs/superpowers/specs/2026-11-04-apx-updates-design.md

## Global Constraints
Preserve existing work, container homes, sessions, configuration files and package holds. No reboot, container replacement or app restart.

## Review Focus
Discovery failure, stopped containers, per-container and per-tool failure isolation, unattended prompts, duplicate runs.

### Task 1: Updater and integration
- [x] Write mocked execution tests for discovery, error isolation and per-container scripts; observe failure before implementation.
- [x] Implement roles/desktop/files/bin/update-apx-containers and service/timer units; exercise APT/DNF and native tool dispatch without live changes.
- [x] Add script/units to desktop role lists; synchronize work-only Claude launchers and subsystem declarations, preserving pre-existing edits.
- [x] Run tests, shellcheck and Bash syntax checks. Validate Ansible syntax and systemd units.

### Task 2: Deploy and verify
- [x] Copy tested files to home; reload host user systemd, enable timer, start a real update.
- [x] Resolve actual update failures, verify timer scheduling and inspect final journal status.

## Verification ledger

Task 1: 11/11 mocked execution tests pass; Bash syntax, shellcheck, git diff whitespace, host systemd unit verification and Ansible user playbook syntax checks passed. Existing uncommitted changes were preserved; no commit was created.

Task 2: Timer installed/enabled; first live run completed successfully across apx-ansible, apx-bitwarden, apx-claude-work, apx-codex and apx-vso-native. Independent reviewer found package payload timeout placement and TERM-resistant timeout issues. Added reproducing tests (both RED before fixes), moved payload limits inside containers and added forced termination limits; full suite 11/11 GREEN. Final deployed revision also completed successfully: systemd Result=success, ExecMainStatus=0 at 16:51:09 EST. Timer remains enabled and waiting for its next daily run.
