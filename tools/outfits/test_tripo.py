import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('tripo', Path(__file__).with_name('tripo.py'))
tripo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tripo)


class SubmissionSafetyTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.image = self.root / 'input.png'
        self.image.write_bytes(b'reference')
        self.record = self.root / 'record.json'
        self.config = {'image': {'path': str(self.image), 'sha256': tripo.digest(self.image)},
                       'estimated_credits': 120, 'parameters': {'quad': True, 'face_limit': 6000}}

    def test_changed_input_does_not_upload_or_spend(self):
        self.image.write_bytes(b'changed')
        with patch.object(tripo, 'api') as api:
            with self.assertRaisesRegex(RuntimeError, 'hash changed'):
                tripo.submit(self.config, self.record, 'test-key')
            api.assert_not_called()
        self.assertFalse(self.record.exists())

    def test_lost_response_keeps_uncertain_record_and_blocks_resubmission(self):
        responses = [{'balance': 1000}, {'file_token': 'uploaded-image'}, TimeoutError('lost response')]
        with patch.object(tripo, 'api', side_effect=responses) as api:
            with self.assertRaises(TimeoutError):
                tripo.submit(self.config, self.record, 'test-key')
            self.assertEqual(api.call_count, 3)
        record = json.loads(self.record.read_text())
        self.assertEqual(record['status'], 'SUBMITTING')
        self.assertEqual(record['request']['input'], 'uploaded-image')
        with patch.object(tripo, 'api') as api:
            with self.assertRaises(FileExistsError):
                tripo.submit(self.config, self.record, 'test-key')
            api.assert_not_called()

    def test_success_saves_task_id(self):
        responses = [{'balance': 1000}, {'file_token': 'uploaded-image'}, {'task_id': 'created-task'}]
        with patch.object(tripo, 'api', side_effect=responses):
            tripo.submit(self.config, self.record, 'test-key')
        self.assertEqual(json.loads(self.record.read_text())['task_id'], 'created-task')

    def multiview_config(self):
        side = self.root / 'side.png'
        side.write_bytes(b'side reference')
        config = dict(self.config)
        config['images'] = [{**config.pop('image'), 'view': 'front'},
                            {'path': str(side), 'sha256': tripo.digest(side), 'view': 'left'}]
        return config

    def test_multiview_changed_side_does_not_upload_or_spend(self):
        config = self.multiview_config()
        Path(config['images'][1]['path']).write_bytes(b'changed')
        with patch.object(tripo, 'api') as api:
            with self.assertRaisesRegex(RuntimeError, 'hash changed'):
                tripo.submit(config, self.record, 'test-key')
            api.assert_not_called()

    def test_multiview_records_views_before_paid_submission(self):
        config = self.multiview_config()

        def respond(key, method, endpoint, **kwargs):
            if endpoint == '/account/balance':
                return {'balance': 1000}
            if endpoint == '/files':
                return {'file_token': kwargs['files']['file'][0]}
            self.assertEqual(endpoint, '/generation/multiview-to-model')
            record = json.loads(self.record.read_text())
            self.assertEqual(record['status'], 'SUBMITTING')
            self.assertEqual(record['request']['inputs'],
                             [{'front': 'input.png'}, {'left': 'side.png'}])
            raise TimeoutError('lost response')

        with patch.object(tripo, 'api', side_effect=respond):
            with self.assertRaises(TimeoutError):
                tripo.submit(config, self.record, 'test-key')
        with patch.object(tripo, 'api') as api:
            with self.assertRaises(FileExistsError):
                tripo.submit(config, self.record, 'test-key')
            api.assert_not_called()


if __name__ == '__main__':
    unittest.main()
