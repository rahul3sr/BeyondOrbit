"""Measured media checks. Creative acceptance remains a human decision."""
from array import array
import math
from pathlib import Path
import re
import subprocess
from .engine import probe


def run(args):
    return subprocess.run(['ffmpeg','-hide_banner','-nostdin',*args],check=True,capture_output=True,timeout=180)


def audio(path,start=0,duration=None):
    a=['-v','error','-protocol_whitelist','file,pipe','-ss',str(start),'-i',str(path)]
    if duration is not None:a+=['-t',str(duration)]
    a+=['-vn','-ac','1','-ar','8000','-f','s16le','-']
    samples=array('h');samples.frombytes(run(a).stdout)
    return samples


def audio_alignment(source,output,start,duration):
    # Compare preserved source waveform with encoded output, tolerating codec delay.
    ref=audio(source,start,min(duration,10));out=audio(output,0,min(duration,10))
    ref=ref[::8];out=out[::8];best=(-1,0)
    for lag in range(-200,201,10):
        a=ref[max(0,lag):min(len(ref),len(out)+lag)]
        b=out[max(0,-lag):max(0,-lag)+len(a)]
        if not a or len(a)!=len(b):continue
        dot=sum(x*y for x,y in zip(a,b));norm=math.sqrt(sum(x*x for x in a)*sum(y*y for y in b))
        correlation=dot/norm if norm else 0
        if correlation>best[0]:best=(correlation,lag/1000)
    return {'correlation':round(best[0],4),'offset_seconds':best[1],
            'passed':best[0]>=.80 and abs(best[1])<=.12,'scope':'first 10 seconds, waveform alignment; not semantic speech verification'}


def inspect(path,cues,*,source=None,source_start=0,caption_size=42):
    info=probe(path);v=next(s for s in info['streams'] if s['codec_type']=='video')
    a=next((s for s in info['streams'] if s['codec_type']=='audio'),None)
    duration=float(info['format']['duration'])
    result=run(['-v','info','-protocol_whitelist','file,pipe','-i',str(path),'-vf',
                'blackdetect=d=0.25:pix_th=0.1,freezedetect=n=0.003:d=0.75',
                '-af','silencedetect=noise=-40dB:d=0.6','-f','null','-'])
    log=result.stderr.decode(errors='replace')
    blacks=[float(x) for x in re.findall(r'black_duration:([\d.]+)',log)]
    freezes=[float(x) for x in re.findall(r'freeze_duration: ([\d.]+)',log)]
    starts=[float(x) for x in re.findall(r'freeze_start: ([\d.]+)',log)]
    ends=[float(x) for x in re.findall(r'freeze_end: ([\d.]+)',log)]
    if len(starts)>len(ends):freezes.append(duration-starts[-1])
    silences=[float(x) for x in re.findall(r'silence_duration: ([\d.]+)',log)]
    samples=audio(path);clipped=sum(abs(x)>=32760 for x in samples)/max(1,len(samples))
    valid=bool(cues);last=0
    for c in cues:
        valid=valid and 0<=c['start']<c['end']<=duration+.05 and c['start']>=last and bool(c['text'].strip())
        last=c['end']
    align=audio_alignment(source,path,source_start,duration) if source else {'passed':False,'scope':'source comparison required'}
    checks={'aspect_ratio':v['width']*16==v['height']*9,'resolution':v['width']>=720 and v['height']>=1280,
        'duration':24.95<=duration<=45.1,'h264_aac':v['codec_name']=='h264' and a is not None and a['codec_name']=='aac',
        'fully_decodable':True,'actual_motion':sum(freezes)/duration<=.20,'black_frames':sum(blacks)/duration<=.05,
        'unintended_silence':sum(silences)/duration<=.35 and max(silences,default=0)<=3,
        'audio_clipping':clipped<.002,'subtitle_timing':bool(valid),
        'caption_layout_bounds':28<=caption_size<=60 and all(len(c['text'])<=90 for c in cues),
        'source_audio_alignment':align['passed']}
    return {'passed':all(checks.values()),'checks':checks,'duration':duration,'resolution':[v['width'],v['height']],
        'freeze_seconds':round(sum(freezes),3),'black_seconds':round(sum(blacks),3),'silence_seconds':round(sum(silences),3),
        'audio_clipped_fraction':clipped,'audio_alignment':align,
        'human_required':['caption accuracy against audible words','visual framing and relevance','rights authenticity','creative acceptance'],
        'limitations':['Motion is a freeze heuristic, not proof of genuine source rights','Caption readability and entertainment are not objectively certified']}
