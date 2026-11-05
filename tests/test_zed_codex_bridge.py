import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'roles/desktop/files/bin/zed-codex-acp'


class BridgeTests(unittest.TestCase):
    def test_host_transport_keeps_stdout_clean_and_preserves_paths(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); log = root / 'calls'
            mock = root / 'host-spawn'
            mock.write_text('#!/bin/bash\nprintf "<%s>\\n" "$@" >> "$CALLS"\nif [[ $* == *exec* ]]; then cat; else echo started; fi\n')
            mock.chmod(0o755)
            env = dict(os.environ, PATH=f'{root}:/usr/bin:/bin', CALLS=str(log), CONTAINER_ID='apx-claude-work')
            r = subprocess.run(['/bin/bash',str(SCRIPT),'--flag','space value'],cwd=td,env=env,
                               input='{"jsonrpc":"2.0"}\n',capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr)
            self.assertEqual(r.stdout,'{"jsonrpc":"2.0"}\n')
            calls=log.read_text()
            self.assertIn('<--no-pty>',calls)
            self.assertIn('<apx-codex>',calls)
            self.assertIn(f'<{td}>',calls)
            self.assertIn('<space value>',calls)
            self.assertNotIn('<--tty>',calls)
