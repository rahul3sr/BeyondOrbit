import copy
from pathlib import Path
import tempfile
import unittest
from beyond_orbit.engine import read,manifest
from beyond_orbit.operations import demo
from beyond_orbit.video import clip,transcript

class EndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t=tempfile.TemporaryDirectory();cls.root=Path(cls.t.name)/'demo'
        cls.result=demo(cls.root)
    @classmethod
    def tearDownClass(cls):cls.t.cleanup()
    def test_demo_both_outputs_and_approval(self):
        self.assertTrue(self.result['fixture'])
        self.assertTrue(self.result['approval_gate_blocked_upload'])
        self.assertTrue(self.result['qc']['passed'])
        for directory in ('original','campaign-clip'):
            self.assertEqual(manifest(self.root/directory),read(self.root/directory/'manifest.json'))
        from beyond_orbit.engine import probe
        for directory in ('original','campaign-clip'):
            self.assertTrue(any(s['codec_type']=='audio' for s in probe(self.root/directory/'video.mp4')['streams']))
    def test_clip_fixture_cannot_authorize_live(self):
        spec=read(self.root/'campaign-clip/spec.json')
        with self.assertRaisesRegex(ValueError,'Test fixture'):
            clip(self.root/'authorized-source.mp4',self.root/'source-transcript.json',self.root/'should-not-exist',
                 start=0,duration=32,evidence=spec['rights'],metadata=read(self.root/'campaign-clip/metadata.json'),
                 campaign_context=spec['campaign'],campaign=read(self.root/'campaign-fixture.json'),
                 account={'followers':0,'country':'US','platform':'youtube'})
        self.assertFalse((self.root/'should-not-exist').exists())
    def test_context_changes_are_bound(self):
        p=self.root/'campaign-clip/context.json';old=p.read_bytes()
        try:
            p.write_bytes(old+b' ')
            self.assertNotEqual(manifest(p.parent),read(p.parent/'manifest.json'))
        finally:p.write_bytes(old)
    def test_nonfinite_transcript(self):
        from beyond_orbit.engine import write
        p=Path(self.t.name)/'bad.json';write(p,{'segments':[{'start':0,'end':float('nan'),'text':'test'}]})
        with self.assertRaises(ValueError):transcript(p)
