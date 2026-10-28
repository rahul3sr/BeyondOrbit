"""Render an explicitly unapproved review draft; never registers or publishes it.

Uses existing captions and technical QA. Full 4:3 source frame is preserved.
Transcript text is historical mission speech; cue timing is provisional.
"""
import sys, json, subprocess, hashlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from beyond_orbit.captions import ass
from beyond_orbit.engine import timestamp
from beyond_orbit.quality import inspect

source, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
out.mkdir(parents=True, exist_ok=True)
start, end = 39.5, 69.3
# Provisional cue timing from mission transcript and ASR landmarks.
# Do not label these timestamps verified or register this draft for publication.
cues = [
 {'start':0.2,'end':6.0,'text':'And we thought, where would be a better place to confirm his findings than on the Moon?'},
 {'start':6.6,'end':9.0,'text':"And so we thought we'd try it here for you."},
 {'start':9.7,'end':14.5,'text':'The feather happens to be, appropriately, a falcon feather for our Falcon.'},
 {'start':15.0,'end':19.5,'text':"And I'll drop the two of them here and hopefully they'll hit the ground at the same time."},
 {'start':21.7,'end':23.0,'text':'How about that!'},
 {'start':24.0,'end':28.0,'text':'Which proves that Mr. Galileo was correct in his findings.'},
]
(out/'captions.ass').write_text(ass(cues).replace(',0,5,70,70,100,1',',0,2,60,60,230,1'))
(out/'captions.srt').write_text('\n\n'.join(f"{i+1}\n{timestamp(c['start'])} --> {timestamp(c['end'])}\n{c['text']}" for i,c in enumerate(cues))+'\n')
meta={'human_reviewed':False,'reviewed_by':None,'status':'UNAPPROVED_REVIEW_DRAFT','source_start':start,'source_end':end,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'transcript_method':'Historical mission transcript with provisional timing; forced alignment failed; audible accuracy requires human verification','segments':cues}
(out/'transcript.json').write_text(json.dumps(meta,indent=2))
font='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
vf="scale=720:540,pad=720:1280:0:330:color=0x101B29,setsar=1"
for label,y,size,color in [('HAMMER vs FEATHER',115,44,'white'),('ON THE MOON',185,38,'0x79E0C0'),('APOLLO 15  /  1971',278,23,'0xBCC9D8'),('Original NASA footage',1120,23,'0xBCC9D8')]:
    vf+=f",drawtext=fontfile={font}:text='{label}':fontcolor={color}:fontsize={size}:x=(w-tw)/2:y={y}"
vf+=',ass=captions.ass'
subprocess.run(['ffmpeg','-y','-v','error','-ss',str(start),'-i',str(source),'-t',str(end-start),'-vf',vf,'-c:v','libx264','-crf','19','-preset','veryfast','-threads','2','-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-ar','48000','-movflags','+faststart','apollo15-review-draft.mp4'],cwd=out,check=True)
qa=inspect(out/'apollo15-review-draft.mp4',cues,source=source,source_start=start)
qa['publication_ready']=False
qa['caption_accuracy_verified']=False
qa['caption_synchronization_verified']=False
qa['creative_review']='pending; archival resolution and radio audio; transcript not human reviewed'
(out/'qa.json').write_text(json.dumps(qa,indent=2))
print(json.dumps({'start':start,'end':end,'qa':qa},indent=2))
