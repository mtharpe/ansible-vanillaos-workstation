from pathlib import Path
import os,subprocess,tempfile,unittest
SCRIPT=Path(__file__).resolve().parents[1]/'roles/apx_container/files/keybase-contained'

class KeybaseEntrypointTests(unittest.TestCase):
    def test_cold_and_warm_gui_forward_urls(self):
        for running in ['0','1']:
            with self.subTest(running=running), tempfile.TemporaryDirectory() as td:
                root=Path(td)
                for name,body in {
                    'pgrep':'exit "$GUI_RUNNING"',
                    'start':'printf "start<%s>\\n" "$@"',
                    'gui':'printf "gui<%s>\\n" "$@"',
                    'cli':'printf "cli<%s>\\n" "$@"',
                }.items():
                    p=root/name;p.write_text('#!/bin/bash\n'+body+'\n');p.chmod(0o755)
                # pgrep succeeds only for an already running GUI.
                p=root/'pgrep';p.write_text('#!/bin/bash\n[[ "$GUI_RUNNING" == 1 ]]\n');p.chmod(0o755)
                source=SCRIPT.read_text().replace('/usr/bin/run_keybase',str(root/'start')).replace('/opt/keybase/Keybase',str(root/'gui')).replace('/usr/bin/keybase',str(root/'cli'))
                script=root/'entrypoint';script.write_text(source)
                r=subprocess.run(['bash',str(script),'--gui','keybase://profile/example'],env=dict(os.environ,PATH=f'{root}:/usr/bin:/bin',GUI_RUNNING=running),capture_output=True,text=True)
                self.assertEqual(r.returncode,0,r.stderr)
                self.assertIn('gui<keybase://profile/example>',r.stdout)
                if running=='0':self.assertIn('start<-g>',r.stdout)
                else:self.assertNotIn('start<',r.stdout)
