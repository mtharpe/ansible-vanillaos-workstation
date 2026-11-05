import importlib.machinery
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'roles/desktop/files/bin/configure-workstation-settings'
loader = importlib.machinery.SourceFileLoader('settings_helper', str(SCRIPT))
spec = importlib.util.spec_from_loader(loader.name, loader)
helper = importlib.util.module_from_spec(spec)
loader.exec_module(helper)


class MergeTests(unittest.TestCase):
    def test_jsonc_comments_urls_and_trailing_commas(self):
        text = '// User note\n{ "url": "https://example.com/a,}", /* note */ "font": 17, }\n'
        updated = helper.merge_settings(text, {'agent_servers': {'Codex': {'type': 'custom'}}})
        self.assertIn('// User note', updated)
        data = json.loads(helper.clean_jsonc(updated))
        self.assertEqual(data['url'], 'https://example.com/a,}')
        self.assertEqual(data['font'], 17)
        self.assertEqual(data['agent_servers']['Codex']['type'], 'custom')

    def test_existing_agents_and_user_choices_preserved(self):
        original = {'buffer_font_size': 16, 'agent_servers': {
            'claude-acp': {'type': 'registry', 'default_config_options': {'mode': 'auto'}},
            'my-agent': {'command': '/custom'}}}
        updated = helper.merge_settings(json.dumps(original), {'agent_servers': {
            'claude-acp': {'type': 'registry'}, 'Codex (Personal)': {'command': '/bridge', 'type': 'custom'}}})
        data = json.loads(updated)
        self.assertEqual(data['buffer_font_size'], 16)
        self.assertEqual(data['agent_servers']['my-agent'], original['agent_servers']['my-agent'])
        self.assertEqual(data['agent_servers']['claude-acp'], original['agent_servers']['claude-acp'])
        self.assertEqual(helper.merge_settings(updated, {'agent_servers': {'Codex (Personal)': {'command': '/bridge', 'type': 'custom'}}}), updated)

    def test_only_chrome_memory_settings_change(self):
        original = {'profile': {'info_cache': {}}, 'performance_tuning': {
            'battery_saver_mode': {'state': 1}, 'high_efficiency_mode': {'custom': True}}}
        data = json.loads(helper.merge_settings(json.dumps(original), helper.CHROME_PATCH))
        self.assertEqual(data['performance_tuning']['battery_saver_mode'], {'state': 1})
        self.assertTrue(data['performance_tuning']['high_efficiency_mode']['custom'])
        self.assertEqual(data['performance_tuning']['high_efficiency_mode']['state'], 2)
        self.assertEqual(data['performance_tuning']['high_efficiency_mode']['aggressiveness'], 1)

    def test_commented_or_escaped_key_is_not_overwritten(self):
        text = '{"example": "\\\"agent_servers\\\": {}", "nested":{"agent_servers":{}}, "agent_servers":{}}'
        updated = helper.merge_settings(text, {'agent_servers': {'Codex': {'type': 'custom'}}})
        data = json.loads(updated)
        self.assertEqual(data['nested'], {'agent_servers': {}})
        self.assertEqual(data['example'], json.loads(text)['example'])
        self.assertIn('Codex', data['agent_servers'])

    def test_malformed_json_aborts(self):
        with self.assertRaises(ValueError): helper.merge_settings('{broken', helper.CHROME_PATCH)


class FileTests(unittest.TestCase):
    def test_chrome_running_defers_only_when_changes_needed(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'Local State'
            path.write_text('{}')
            with patch.object(helper, 'chrome_running', return_value=True):
                self.assertTrue(helper.configure(path, helper.CHROME_PATCH, chrome=True)['deferred'])
                self.assertEqual(path.read_text(), '{}')
                path.write_text(json.dumps(helper.CHROME_PATCH))
                self.assertFalse(helper.configure(path, helper.CHROME_PATCH, chrome=True)['changed'])

    def test_check_mode_does_not_write(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'Local State'
            path.write_text('{}')
            result = helper.configure(path, helper.CHROME_PATCH, check=True)
            self.assertTrue(result['changed'])
            self.assertEqual(path.read_text(), '{}')

    def test_write_backups_and_idempotence(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'settings.json'
            path.write_text('// keep\n{"font":16}')
            with patch.object(helper, 'BACKUP_ROOT', Path(td) / 'backup'):
                result = helper.configure(path, {'agent_servers': {} })
                self.assertTrue(result['changed'])
                self.assertEqual(Path(result['backup']).read_text(), '// keep\n{"font":16}')
                self.assertEqual(Path(result['backup']).stat().st_mode & 0o777, 0o600)
                self.assertFalse(helper.configure(path, {'agent_servers': {}})['changed'])
