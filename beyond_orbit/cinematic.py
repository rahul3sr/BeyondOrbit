"""A visual proof renderer using original storyboard art, camera motion and sound design.
This is not generative video or natural voiceover. It never uploads.
"""
import argparse
from array import array
import json
import math
from pathlib import Path
import random
import shutil
import subprocess
import wave
from .captions import ass
from .engine import digest, manifest, probe, qc, write

DURATIONS=[4,5,5,5,6,7]
LINES=['Too many ideas?','Pick one.','Make it small.','Finish the first version.','Learn by making.','One idea. Into orbit.']


def soundbed(path,duration=32):
    """Original quiet ambient chord with soft edit accents; no voice or samples."""
    rate=44100
    samples=array('h')
    boundaries=[0,4,9,14,19,25]
    rng=random.Random(47)
    for n in range(rate*duration):
        t=n/rate
        fade=min(1,t/2,(duration-t)/3)
        chord=sum(math.sin(2*math.pi*f*t+0.12*math.sin(t*.7+i))*.018
                  for i,f in enumerate([130.8128,196,261.6256,329.6276]))
        pulse=sum(math.exp(-(t-b)*18)*math.sin(2*math.pi*880*(t-b))*.05
                  for b in boundaries if 0<=t-b<.3)
        air=(rng.random()*2-1)*.002
        samples.append(round(max(-1,min(1,(chord+pulse+air)*max(0,fade)))*32767))
    with wave.open(str(path),'wb') as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(rate);f.writeframes(samples.tobytes())


def build(sheet,out):
    sheet=Path(sheet).resolve();out=Path(out).resolve()
    out.mkdir(parents=True,exist_ok=False)
    shutil.copy2(sheet,out/'storyboard.png')
    info=probe(sheet)['streams'][0]
    width,height=info['width']//3,info['height']//2
    # Crop source panels as part of the media assembly, then animate each shot.
    for i,seconds in enumerate(DURATIONS):
        x=(i%3)*width;y=(i//3)*height
        frames=seconds*30
        zoom="1.04+0.00045*on" if i%2==0 else "1.14-0.00045*on"
        horizontal="iw/2-iw/zoom/2+sin(on/80)*8"
        vf=(f'crop={width}:{height}:{x}:{y},scale=1080:1920:force_original_aspect_ratio=increase,'
            'crop=1080:1920,'
            f"zoompan=z='{zoom}':x='{horizontal}':y='ih/2-ih/zoom/2':d={frames}:s=720x1280:fps=30,"
            'setsar=1,fade=t=in:st=0:d=0.12,'
            f'fade=t=out:st={seconds-.12}:d=0.12')
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-i',str(sheet),
                        '-vf',vf,'-t',str(seconds),'-c:v','libx264','-preset','veryfast','-threads','2',
                        '-pix_fmt','yuv420p',f'shot{i}.mp4'],cwd=out,check=True,capture_output=True)
    (out/'shots.txt').write_text(''.join(f"file shot{i}.mp4\n" for i in range(6)))
    cues=[];at=0
    for text,seconds in zip(LINES,DURATIONS):
        cues.append({'start':at+.3,'end':at+seconds-.25,'text':text});at+=seconds
    subtitles=ass(cues).replace('DejaVu Sans,42,','DejaVu Sans,46,').replace(',0,5,70,70,100,1',',0,2,60,60,235,1')
    (out/'captions.ass').write_text(subtitles)
    from .engine import timestamp
    (out/'captions.srt').write_text('\n\n'.join(f"{i+1}\n{timestamp(c['start'])} --> {timestamp(c['end'])}\n{c['text']}" for i,c in enumerate(cues))+'\n')
    soundbed(out/'soundbed.wav')
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-f','concat','-safe','1','-i','shots.txt',
                    '-i','soundbed.wav','-vf','ass=captions.ass','-af','loudnorm=I=-20:TP=-2:LRA=8',
                    '-c:v','libx264','-preset','veryfast','-threads','2','-pix_fmt','yuv420p','-c:a','aac',
                    '-b:a','160k','-movflags','+faststart','-t','32','video.mp4'],cwd=out,check=True,capture_output=True)
    write(out/'spec.json',{'type':'cinematic_visual_proof','scene_durations':DURATIONS,'scene_text':LINES,
        'visuals':'Original AI-generated contact-sheet artwork, cropped and animated with camera motion',
        'storyboard_sha256':digest(sheet),'narration':False,
        'audio':'Original procedural ambient soundbed; no third-party samples',
        'limits':['Still-image motion, not generative video','No natural voiceover yet','Requires human creative review']})
    write(out/'metadata.json',{'title':'One idea. Into orbit.','description':'Beyond Orbit visual proof. Original AI artwork and sound design. No narration.',
        'destination':{'platform':'youtube','channel':'@BeyondOrbitVentures','privacy':'private'}})
    technical=qc(out/'video.mp4')
    technical['audio']='Original ambient sound design; no narration'
    write(out/'report.json',{'qc':technical,'state':'awaiting_human_review',
        'rights':{'status':'original AI artwork and first-party sound design; human review required'},
        'creative_review':'NOT asserted by automated QC','narration':'none',
        'changes':['Six visual scenes','Continuous camera movement','Short editorial text','Original sound design','Robotic speech removed']})
    write(out/'manifest.json',manifest(out))
    return out/'video.mp4'

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('sheet');p.add_argument('--out',required=True)
    a=p.parse_args();print(build(a.sheet,a.out))
