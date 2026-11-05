import importlib.machinery
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'roles/desktop/files/bin/retain-container-images'
loader = importlib.machinery.SourceFileLoader('retention', str(SCRIPT))
spec = importlib.util.spec_from_loader(loader.name, loader)
retention = importlib.util.module_from_spec(spec)
loader.exec_module(retention)
REPO = '123456789012.dkr.ecr.us-east-1.amazonaws.com/example-app'
NOW = 200000


def image(n, names=None, created=100):
    return {'Id': f'{n:064x}', 'Names': names if names is not None else [f'{REPO}:rel-v{n}'],
            'RepoDigests': [f'{REPO}@sha256:{n:064x}'], 'Created': created, 'Containers': 0}


class SelectionTests(unittest.TestCase):
    def test_keeps_five_newest_versions(self):
        images = [image(i) for i in range(1, 9)]
        self.assertEqual(retention.select_candidates(images, [], NOW), [x['Id'] for x in images[:3]])

    def test_other_tags_and_local_aliases_protect_entire_image(self):
        images = [image(i) for i in range(1, 9)]
        images[0]['Names'].append('localhost/test:e2e')
        images[1]['Names'].append(f'{REPO}:rollback')
        self.assertEqual(retention.select_candidates(images, [], NOW), [images[2]['Id']])

    def test_protects_images_referenced_by_any_container(self):
        images = [image(i) for i in range(1, 9)]
        containers = [{'ImageID': images[0]['Id'], 'State': 'exited'},
                      {'ImageID': images[1]['Id'], 'State': 'running'}]
        self.assertEqual(retention.select_candidates(images, containers, NOW), [images[2]['Id']])

    def test_grace_period_and_unknown_creation_time(self):
        images = [image(i) for i in range(1, 9)]
        images[0]['Created'] = NOW - 100
        images[1].pop('Created')
        images[2]['Created'] = NOW + 100
        self.assertEqual(retention.select_candidates(images, [], NOW), [])

    def test_newest_versions_with_aliases_count_as_versions(self):
        images = [image(i) for i in range(1, 9)]
        images[6]['Names'].append(f'{REPO}:rel-v9')
        self.assertEqual(retention.select_candidates(images, [], NOW), [x['Id'] for x in images[:4]])

    def test_unknown_repo_digest_protects_image(self):
        images = [image(i) for i in range(1, 9)]
        images[0]['RepoDigests'].append('example.com/important@sha256:123')
        self.assertNotIn(images[0]['Id'], retention.select_candidates(images, [], NOW))

    def test_malformed_ids_and_container_metadata_fail_closed(self):
        with self.assertRaises(ValueError):
            retention.select_candidates([dict(image(1), Id='not-an-id')], [], NOW)
        with self.assertRaises(ValueError):
            retention.select_candidates([image(1)], [{'ImageID': ''}], NOW)

    def test_non_finite_dates_and_conflicting_tag_fields_are_preserved(self):
        images = [image(i) for i in range(1, 9)]
        images[0]['Created'] = float('nan')
        images[1]['Created'] = float('inf')
        images[2]['RepoTags'] = ['localhost/important:new']
        self.assertEqual(retention.select_candidates(images, [], NOW), [])
        with self.assertRaises(ValueError):
            retention.select_candidates([dict(image(1), RepoDigests=0)], [], NOW)

    def test_unknown_images_and_digest_only_images_are_preserved(self):
        images = [image(i) for i in range(1, 9)]
        images[0]['Names'] = []
        images[1]['Names'] = ['example.com/other:v1']
        self.assertEqual(retention.select_candidates(images, [], NOW), [images[2]['Id']])


class ApplyTests(unittest.TestCase):
    def test_deletes_only_explicit_references_without_parent_pruning(self):
        refs = [f'{REPO}:rel-v1', f'{REPO}@sha256:{1:064x}']
        with patch.object(retention, 'podman', return_value='') as command:
            retention.delete_image(image(1)['Id'], refs)
        args = command.call_args.args
        self.assertEqual(args, ('rmi', '--no-prune', '--ignore', '--', *refs))
        self.assertNotIn(image(1)['Id'], args)
        self.assertNotIn('--force', args)

    def test_cache_expiry_only_prunes_old_dangling_images(self):
        with patch.object(retention, 'podman', return_value='') as command:
            retention.prune_old_dangling()
        self.assertEqual(command.call_args.args,
                         ('image', 'prune', '--force', '--filter', 'until=168h'))
        self.assertNotIn('--all', command.call_args.args)
        self.assertNotIn('--external', command.call_args.args)

    def test_default_dry_run_never_deletes(self):
        images = [image(i) for i in range(1, 9)]
        with patch.object(retention, 'snapshot', return_value=(images, [])), \
             patch.object(retention, 'delete_image') as delete:
            retention.run(False, NOW)
        delete.assert_not_called()

    def test_rechecks_retagging_before_each_delete(self):
        images = [image(i) for i in range(1, 7)]
        changed = [dict(x, Names=list(x['Names'])) for x in images]
        changed[0]['Names'].append('localhost/new-work:test')
        with patch.object(retention, 'snapshot', side_effect=[(images, []), (changed, [])]), \
             patch.object(retention, 'delete_image') as delete:
            retention.run(True, NOW)
        delete.assert_not_called()

    def test_failed_discovery_causes_no_deletion(self):
        with patch.object(retention, 'snapshot', side_effect=RuntimeError('podman unavailable')), \
             patch.object(retention, 'delete_image') as delete:
            with self.assertRaises(RuntimeError):
                retention.run(True, NOW)
        delete.assert_not_called()

    def test_apply_deletes_selected_ids_and_isolates_failure(self):
        images = [image(i) for i in range(1, 9)]
        with patch.object(retention, 'snapshot', return_value=(images, [])), \
             patch.object(retention, 'delete_image', side_effect=[RuntimeError('protected'), None, None]) as delete:
            self.assertEqual(retention.run(True, NOW), 1)
        self.assertEqual([c.args[0] for c in delete.call_args_list], [x['Id'] for x in images[:3]])


if __name__ == '__main__':
    unittest.main()
