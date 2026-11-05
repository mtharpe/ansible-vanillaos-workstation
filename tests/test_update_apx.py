import os
import fcntl
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'roles/desktop/files/bin/update-apx-containers'


class UpdaterTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.log = self.root / 'calls'
        self.env = dict(os.environ, PATH=f'{self.bin}:/usr/bin:/bin',
                        XDG_RUNTIME_DIR=str(self.root), CALLS=str(self.log))
        self.mock('distrobox', 'printf "enter %s\\n" "$*" >> "$CALLS"\n')
        self.mock('notify-send', 'echo notification >> "$CALLS"\n')
        self.mock('podman', '''printf 'podman %s\\n' "$*" >> "$CALLS"
if [[ $1 == ps ]]; then
    [[ ${DISCOVERY_FAIL:-} == 1 ]] && exit 1
    if [[ $* == *manager=apx* ]]; then printf '%s\\n' apx-first apx-second
    else printf '%s\\n' apx-bitwarden; fi
elif [[ $1 == exec ]]; then
    cat >/dev/null
    [[ ${FAIL_FIRST:-} == 1 && $* == *apx-first* ]] && exit 3
fi
exit 0
''')

    def mock(self, name, body):
        p = self.bin / name
        p.write_text('#!/bin/bash\n' + body)
        p.chmod(0o755)

    def run_updater(self, *args, **env):
        return subprocess.run(['/bin/bash', str(SCRIPT), *args], env=dict(self.env, **env),
                              stdin=subprocess.DEVNULL, capture_output=True, text=True)

    def test_discovers_and_updates_every_container(self):
        r = self.run_updater()
        self.assertEqual(r.returncode, 0, r.stderr)
        calls = self.log.read_text()
        for name in ['apx-first', 'apx-second', 'apx-bitwarden']:
            self.assertIn(f'--name {name}', calls)
            self.assertIn(f'{name} timeout --kill-after=30s 45m bash -s -- --packages', calls)
            self.assertIn(f'{name} timeout --kill-after=30s 35m bash -s -- --user-tools', calls)
        self.assertNotIn(' stop ', calls)
        self.assertNotIn(' restart ', calls)

    def test_failure_attempts_remaining_containers_and_notifies(self):
        r = self.run_updater(FAIL_FIRST='1')
        self.assertNotEqual(r.returncode, 0)
        calls = self.log.read_text()
        self.assertIn('apx-second timeout --kill-after=30s 45m bash -s -- --packages', calls)
        self.assertIn('apx-first timeout --kill-after=30s 35m bash -s -- --user-tools', calls)
        self.assertIn('notification', calls)

    def test_discovery_failure_is_not_success(self):
        r = self.run_updater(DISCOVERY_FAIL='1')
        self.assertNotEqual(r.returncode, 0)

    def test_apt_uses_noninteractive_upgrade_without_removals(self):
        self.mock('apt-get', 'printf "apt %s %s\\n" "$DEBIAN_FRONTEND" "$*" >> "$CALLS"\n')
        r = self.run_updater('--packages')
        self.assertEqual(r.returncode, 0, r.stderr)
        calls = self.log.read_text()
        self.assertIn('noninteractive', calls)
        self.assertIn('Error-Mode=any', calls)
        self.assertIn('--force-confold', calls)
        self.assertIn('--no-remove', calls)
        self.assertNotIn('dist-upgrade', calls)

    def test_failed_package_refresh_does_not_upgrade_stale_indexes(self):
        self.mock('apt-get', 'echo "$*" >> "$CALLS"; exit 42\n')
        r = self.run_updater('--packages')
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn(' upgrade', self.log.read_text())

    def test_package_timeout_runs_inside_container(self):
        r = self.run_updater()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('apx-first timeout --kill-after=30s 45m bash -s -- --packages', self.log.read_text())

    def test_term_resistant_tool_is_killed_and_next_tool_attempted(self):
        profile = self.root / 'profile'
        (profile / '.local/bin').mkdir(parents=True)
        self.mock('getent', f'echo "test:x:1000:1000::{profile}:/bin/bash"\n')
        claude = profile / '.local/bin/claude'
        claude.write_text('#!/bin/bash\ntrap "" TERM\nexec sleep 10\n')
        claude.chmod(0o755)
        codex = profile / '.local/bin/codex'
        codex.write_text('#!/bin/bash\necho codex-attempted >> "$CALLS"\n')
        codex.chmod(0o755)
        script = self.root / 'short-timeout-updater'
        script.write_text(SCRIPT.read_text().replace('15m', '0.05s').replace('30s', '0.05s'))
        r = subprocess.run(['/bin/bash', str(script), '--user-tools'], env=self.env,
                           capture_output=True, text=True, timeout=3)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('codex-attempted', self.log.read_text())

    def test_dnf_container_uses_refresh_and_assume_yes(self):
        self.mock('dnf', 'echo "dnf $*" >> "$CALLS"\n')
        # Restrict discovery so the host system APT cannot mask a DNF container.
        r = self.run_updater('--packages', PATH=str(self.bin))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('dnf --assumeyes --refresh upgrade', self.log.read_text())

    def test_duplicate_run_exits_without_updating(self):
        with (self.root / 'update-apx-containers.lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            r = self.run_updater()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(self.log.exists())

    def test_failed_start_skips_container_and_continues(self):
        self.mock('distrobox', '[[ $* == *apx-first* ]] && exit 1; exit 0\n')
        r = self.run_updater()
        self.assertNotEqual(r.returncode, 0)
        calls = self.log.read_text()
        self.assertNotIn('apx-first timeout', calls)
        self.assertIn('apx-second timeout --kill-after=30s 45m bash -s -- --packages', calls)

    def test_installed_codex_adapter_updates_only_its_package(self):
        profile = self.root / 'profile'
        (profile / '.local/bin').mkdir(parents=True)
        self.mock('getent', f'echo "test:x:1000:1000::{profile}:/bin/bash"\n')
        adapter = profile / '.local/bin/codex-acp'
        adapter.write_text('#!/bin/bash\nexit 0\n')
        adapter.chmod(0o755)
        self.mock('npm', 'printf "npm <%s>\\n" "$@" >> "$CALLS"\n')
        r = self.run_updater('--user-tools')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('<@agentclientprotocol/codex-acp@latest>', self.log.read_text())
        self.assertIn(f'<{profile}/.local>', self.log.read_text())

    def test_user_tools_failure_isolated_and_home_correct(self):
        profile = self.root / 'profile'
        (profile / '.local/bin').mkdir(parents=True)
        self.mock('getent', f'echo "test:x:1000:1000::{profile}:/bin/bash"\n')
        for name, rc in [('claude', 1), ('codex', 0)]:
            p = profile / '.local/bin' / name
            p.write_text(f'#!/bin/bash\necho "{name} $HOME $*" >> "$CALLS"\nexit {rc}\n')
            p.chmod(0o755)
        r = self.run_updater('--user-tools')
        self.assertNotEqual(r.returncode, 0)
        calls = self.log.read_text()
        self.assertIn(f'claude {profile} update', calls)
        self.assertIn(f'codex {profile} update', calls)


if __name__ == '__main__':
    unittest.main()
