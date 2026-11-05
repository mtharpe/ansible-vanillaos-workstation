from pathlib import Path
import os,re,subprocess,unittest

SOURCE=Path(__file__).resolve().parents[1]/'roles/dotfiles/files/bashrc'

class KeybaseFunctionTests(unittest.TestCase):
    def test_wrapper_targets_dedicated_container_and_forwards_arguments(self):
        match=re.search(r'(?ms)^keybase\(\) \{.*?^\}',SOURCE.read_text())
        self.assertIsNotNone(match,'Keybase Bash function is missing')
        code='host-shell() { printf "<%s>\\n" "$@"; }\n'+match.group(0)+'\nkeybase "$@"'
        for args in [[],['--version'],['id','space value']]:
            with self.subTest(args=args):
                r=subprocess.run(['bash','-c',code,'shell',*args],env=dict(os.environ,CONTAINER_ID='apx-vso-native'),capture_output=True,text=True)
                self.assertEqual(r.returncode,0,r.stderr)
                self.assertIn('<apx-keybase>',r.stdout)
                self.assertIn('keybase-contained',r.stdout)
                for arg in args:self.assertIn('<'+arg+'>',r.stdout)
