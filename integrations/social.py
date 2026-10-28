"""Separate, explicitly mocked platform adapters; no network side effects."""
import hashlib
from pathlib import Path

class MockPlatform:
    mode='mock'
    cost_usd=0
    def __init__(self,platform):
        if platform not in {'youtube','instagram','tiktok'}:raise ValueError('Unsupported platform')
        self.platform=platform
        self.calls=[]

    def upload(self,video,metadata,idempotency_key):
        if metadata['destination']['platform']!=self.platform:raise ValueError('Destination mismatch')
        self.calls.append(idempotency_key)
        return {'mode':'mock','platform':self.platform,'external_id':'mock-'+idempotency_key,
                'sha256':hashlib.sha256(Path(video).read_bytes()).hexdigest(),
                'publicly_published':False,'analytics':None}

class YouTubeMock(MockPlatform):
    def __init__(self):super().__init__('youtube')
class InstagramMock(MockPlatform):
    def __init__(self):super().__init__('instagram')
class TikTokMock(MockPlatform):
    def __init__(self):super().__init__('tiktok')

class LivePlatform:
    mode='live'
    def __init__(self,platform):self.platform=platform
    def upload(self,*args,**kwargs):
        raise RuntimeError('Live OAuth and uploads are disabled pending official authorization and integration testing')
