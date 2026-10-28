from pathlib import Path
import subprocess
from beyond_orbit.engine import digest,write
from beyond_orbit.campaigns import now

def moving_source(root):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    source=root/'legal-test-source.mp4'
    subprocess.run(['ffmpeg','-v','error','-nostdin','-f','lavfi','-i','testsrc2=size=960x540:rate=24:duration=34',
        '-f','lavfi','-i','aevalsrc=0.08*sin(2*PI*(440*t+30*t*t)):s=48000:d=34',
        '-c:v','libx264','-preset','ultrafast','-threads','2','-pix_fmt','yuv420p','-c:a','aac',str(source)],check=True,capture_output=True,timeout=120)
    doc=root/'rights.txt';doc.write_text('Original FFmpeg testsrc2/chirp fixture. Development only. No human speech, campaign or commercial-source claim.')
    destination={'platform':'youtube','channel_id':'UC_TEST_ONLY','privacy':'private'}
    rights={'fixture':True,'owner':'Beyond Orbit test fixture','source_sha256':digest(source),'document_reference':str(doc),
        'document_sha256':digest(doc),'commercial_use':True,'editing_allowed':True,'audio_reuse':True,
        'verified_by':'TEST ONLY','verified_at':now().isoformat(),'destinations':[destination],'attribution':[],
        'disclosures':['Synthetic development media; no human speech or real campaign.']}
    return source,rights,destination
