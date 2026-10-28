"""Local real-media execution using explicitly labelled legal development assets."""
from pathlib import Path
from tempfile import TemporaryDirectory
import copy
import json
import unittest
import wave
from beyond_orbit.engine import read,write,manifest,digest
from beyond_orbit.production import ingest,render_clip,validate_transcript,propose_segments
from beyond_orbit.quality import inspect
from media_support import moving_source

class MediaPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t=TemporaryDirectory();cls.root=Path(cls.t.name)
        cls.source,cls.rights,cls.destination=moving_source(cls.root/'inputs')
        cls.asset=cls.root/'ingested';cls.source_record=ingest(cls.source,cls.rights,cls.asset,fixture=True)
        cls.transcript=cls.root/'transcript.json'
        write(cls.transcript,{'source_sha256':digest(cls.source),'human_reviewed':True,'reviewed_by':'UNIT synthetic timeline only',
              'segments':[{'start':i*5,'end':i*5+4,'text':'Synthetic motion test. No human speech.'} for i in range(6)]})
        cls.selection={'start':0,'end':30,'editor':'UNIT TEST','confirmed':True,'framing':{'x':.3,'y':.5,'width':720,'height':1280},
            'creative_checks':{k:True for k in ('clear_beginning','coherent_story','meaningful_ending','speaker_continuity','audible_clarity','visual_relevance','natural_pacing')}}
        cls.metadata={'title':'Synthetic development test','description':cls.rights['disclosures'][0],'destination':cls.destination}
        cls.out=render_clip(cls.asset,cls.transcript,cls.selection,cls.metadata,cls.root/'output',fixture=True)
    @classmethod
    def tearDownClass(cls):cls.t.cleanup()
    def test_full_source_first_pipeline(self):
        report=read(self.out/'report.json')
        self.assertTrue(report['fixture']);self.assertTrue(report['qc']['passed'])
        self.assertEqual(report['creative_approval'],'pending')
        self.assertEqual(manifest(self.out),read(self.out/'manifest.json'))
        for name in ('source.json','rights.json','transcript.json','selection.json','captions.srt','preview.jpg','costs.json'):
            self.assertTrue((self.out/name).is_file())
    def test_frame_crop_config_preserved(self):
        self.assertEqual(read(self.out/'selection.json')['framing']['x'],.3)
    def test_unreviewed_transcript_blocked(self):
        data=read(self.transcript);data['human_reviewed']=False
        with self.assertRaises(ValueError):validate_transcript(data,digest(self.source))
    def test_transcript_wrong_source_blocked(self):
        with self.assertRaises(ValueError):validate_transcript(read(self.transcript),'WRONG')
    def test_fixture_cannot_enter_production(self):
        with self.assertRaises(ValueError):render_clip(self.asset,self.transcript,self.selection,self.metadata,self.root/'not-created')
        self.assertFalse((self.root/'not-created').exists())
    def test_rejected_slideshow_detected(self):
        import subprocess
        p=self.root/'static.mp4'
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=navy:size=720x1280:rate=24:duration=30',
            '-f','lavfi','-i','aevalsrc=0.08*sin(2*PI*(440*t+30*t*t)):s=48000:d=30',
            '-c:v','libx264','-preset','ultrafast','-threads','2','-c:a','aac',str(p)],check=True,capture_output=True)
        result=inspect(p,[{'start':0,'end':29,'text':'Static development fixture'}],source=p)
        self.assertFalse(result['checks']['actual_motion']);self.assertFalse(result['passed'])
    def test_black_silence_and_subtitle_checks(self):
        import subprocess
        p=self.root/'black.mp4'
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=black:size=720x1280:rate=24:duration=30',
            '-f','lavfi','-i','anullsrc=r=48000:cl=mono','-t','30','-c:v','libx264','-preset','ultrafast','-threads','2','-c:a','aac',str(p)],check=True,capture_output=True)
        result=inspect(p,[{'start':0,'end':99,'text':'bad timing'}],source=p)
        self.assertFalse(result['checks']['black_frames']);self.assertFalse(result['checks']['unintended_silence']);self.assertFalse(result['checks']['subtitle_timing'])

    def test_audio_sync_mismatch_rejected(self):
        result=inspect(self.out/'video.mp4',read(self.out/'transcript.json')['segments'],source=self.source,source_start=5)
        self.assertFalse(result['checks']['source_audio_alignment'])
    def test_full_scale_clipped_audio_rejected(self):
        import subprocess
        p=self.root/'clipped-audio.mkv'
        subprocess.run(['ffmpeg','-v','error','-i',str(self.out/'video.mp4'),'-f','lavfi','-i','aevalsrc=1:s=8000:d=30',
            '-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','pcm_s16le','-t','30',str(p)],check=True,capture_output=True)
        result=inspect(p,read(self.out/'transcript.json')['segments'],source=p)
        self.assertFalse(result['checks']['audio_clipping'])
    def test_corrupt_media_rejected(self):
        import subprocess
        p=self.root/'corrupt.mp4';p.write_bytes(b'not decodable media')
        with self.assertRaises(subprocess.CalledProcessError):inspect(p,[],source=p)

class RecordedSpeechASR(unittest.TestCase):
    def test_recorded_natural_speech_accuracy_and_timestamps(self):
        from beyond_orbit.local_asr import transcribe,word_error_rate
        data=Path(__file__).parent/'data/goforward.raw';provenance=read(data.parent/'PROVENANCE.json')
        self.assertEqual(digest(data),provenance['sha256'])
        with TemporaryDirectory() as t:
            wav=Path(t)/'recording.wav'
            with wave.open(str(wav),'wb') as f:
                f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000);f.writeframes(data.read_bytes())
            result=transcribe(wav,Path(t)/'transcript.json')
            error=word_error_rate(provenance['reference'],' '.join(w['text'] for w in result['words']))
            self.assertLessEqual(error,.25)
            self.assertTrue(all(0<=w['start']<w['end']<=3 for w in result['words']))
            self.assertFalse(result['human_reviewed'])

class CropPreview(unittest.TestCase):
    def test_explicit_crop_preview(self):
        from beyond_orbit.production import preview_crop
        from beyond_orbit.engine import probe
        with TemporaryDirectory() as t:
            root=Path(t);source,rights,destination=moving_source(root/'inputs');ingest(source,rights,root/'asset',fixture=True)
            preview=preview_crop(root/'asset',{'start':1,'framing':{'x':0,'y':.5,'width':720,'height':1280}},root/'preview.jpg')
            self.assertEqual(probe(preview)['streams'][0]['width'],720)
