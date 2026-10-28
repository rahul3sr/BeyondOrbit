"""Run and categorize all tests without claiming fixture/mocks are live integrations."""
from pathlib import Path
import json
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests'))


def tests(suite):
    for t in suite:
        if isinstance(t,unittest.TestSuite):yield from tests(t)
        else:yield t


def category(t):
    name=t.__class__.__name__
    if name in {'ApprovalRepair','QueueRepair','PipelineRouting'}:return 'mock_transport_or_identity_evidence'
    if name=='OAuthProtocol' and t._testMethodName!='test_credentials_permissions_and_no_overwrite':return 'mock_transport_or_identity_evidence'
    if name in {'Functional','State','EndToEnd','MediaPipeline','RecordedSpeechASR','CropPreview'}:return 'local_media'
    return 'pure_unit_or_local_utility'


suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
alltests=list(tests(suite));counts={}
for t in alltests:counts[category(t)]=counts.get(category(t),0)+1
mock_dependent=sum(category(t)=='mock_transport_or_identity_evidence' or (t.__class__.__name__=='State' and t._testMethodName in {
    'test_job_once_only','test_mock_platforms','test_cost_limit','test_retry_revalidates_approval'}) for t in alltests)
result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(alltests))
summary={'collected':len(alltests),'executed':result.testsRun,'passed':result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped),
    'failed':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'categories':counts,
    'mock_dependent':mock_dependent,'live_authorized_integration_tests':0,'creative_acceptance_tests':0,
    'note':'Local media tests use legal procedural fixtures and one pinned upstream natural-speech utterance, not a real campaign source.'}
print('TEST_SUMMARY_JSON='+json.dumps(summary,sort_keys=True))
if '--save-report' in sys.argv:(ROOT/'reports/phase2-tests.json').write_text(json.dumps(summary,indent=2)+'\n')
sys.exit(not result.wasSuccessful())
