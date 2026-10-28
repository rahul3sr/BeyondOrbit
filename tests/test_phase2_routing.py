"""Mocked CLI routing only; not a real-source production demonstration."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest
from beyond_orbit.engine import write
from beyond_orbit.store import Store
from test_phase2_safeguards import unit_artifact

class PipelineRouting(unittest.TestCase):
    def test_passing_render_routes_to_pending_review_not_publication(self):
        from beyond_orbit.pipeline import main
        with TemporaryDirectory() as t:
            root=Path(t);output=root/'output';unit_artifact(output)
            for name in ('selection','metadata'):write(root/(name+'.json'),{})
            argv=['pipeline','render','--asset','UNIT','--transcript','UNIT','--selection',str(root/'selection.json'),
                  '--metadata',str(root/'metadata.json'),'--out',str(output),'--db',str(root/'db.sqlite')]
            with patch('sys.argv',argv),patch('beyond_orbit.pipeline.render_clip',return_value=output):main()
            state=Store(root/'db.sqlite').dashboard()
            self.assertEqual(len(state['assets']),1);self.assertEqual(state['assets'][0]['state'],'pending')
            self.assertEqual(state['jobs'],[]);self.assertEqual(state['approvals'],[])
