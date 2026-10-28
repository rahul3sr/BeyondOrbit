import copy
import json
from pathlib import Path
import tempfile
import unittest
from beyond_orbit.engine import read, write, rights_check, score, render, manifest, check_approval
from integrations.youtube import publish

SPEC = read(Path(__file__).resolve().parents[1]/'examples/original.json')

class Gates(unittest.TestCase):
    def test_unknown_rights_rejected(self):
        s = copy.deepcopy(SPEC)
        s['rights']['script']['basis'] = 'found_online'
        with self.assertRaises(ValueError): rights_check(s)

    def test_missing_evidence_rejected(self):
        s = copy.deepcopy(SPEC)
        s['rights']['visuals']['evidence'] = ''
        with self.assertRaises(ValueError): rights_check(s)

    def test_absent_script_rejected(self):
        s = copy.deepcopy(SPEC)
        s['rights']['script']['basis'] = 'none'
        with self.assertRaises(ValueError): rights_check(s)

    def test_scoring_is_explainable(self):
        r = score('Can you finish 1 small step?')
        self.assertEqual(r['score'], sum(r['components'].values()))
        self.assertFalse(r['predicts_virality'])

    def test_publishing_disabled(self):
        with self.assertRaises(RuntimeError): publish()

class Functional(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.temp.name)/'review'
        cls.report = render(SPEC, cls.out, fixture=True)

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    def test_render_decode_and_captions(self):
        self.assertTrue(self.report['qc']['passed'])
        self.assertEqual(self.report['qc']['resolution'], [720,1280])
        self.assertEqual((self.out/'captions.srt').read_text().count('-->'),len(SPEC['scenes']))
        self.assertEqual(self.report['state'], 'awaiting_human_approval')

    def test_approval_and_mutation(self):
        # Synthetic approval fixture, never a real user's approval.
        p = Path(self.temp.name)/'fixture-approval.json'
        a = {'decision':'approved','reviewer':'TEST FIXTURE','approved_at':'fixture',
             'manifest_sha256':manifest(self.out)['sha256'],
             'destination':read(self.out/'metadata.json')['destination']}
        write(p,a)
        self.assertTrue(check_approval(self.out,p))
        for name in ('video.mp4','captions.srt','metadata.json','spec.json','report.json'):
            target = self.out/name
            original = target.read_bytes()
            try:
                target.write_bytes(original+b' ')
                with self.assertRaises(ValueError): check_approval(self.out,p)
            finally: target.write_bytes(original)
        a['destination']['privacy']='public'
        write(p,a)
        with self.assertRaises(ValueError): check_approval(self.out,p)

    def test_rejected_approval(self):
        p = Path(self.temp.name)/'rejected.json'
        write(p,{'decision':'rejected'})
        with self.assertRaises(ValueError): check_approval(self.out,p)

if __name__ == '__main__': unittest.main()
