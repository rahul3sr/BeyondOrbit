"""Authorized local source clipping with supplied, timed transcript captions."""
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import textwrap
import time
from .engine import digest, manifest, probe, qc, read, timestamp, write
from .skills import hook


def transcript(path):
    data=read(path)
    segments=data['segments']
    last=0
    for s in segments:
        a,b=s['start'],s['end']
        if not all(isinstance(x,(int,float)) and math.isfinite(x) for x in (a,b)) or not last<=a<b:
            raise ValueError('Transcript times must be finite, increasing, non-overlapping')
        if not isinstance(s['text'],str) or not s['text'].strip():raise ValueError('Missing transcript text')
        last=b
    if not segments:raise ValueError('Empty transcript')
    return segments


def candidates(segments):
    result=[]
    for i,s in enumerate(segments):
        for e in segments[i:]:
            duration=e['end']-s['start']
            if duration>60:break
            if 30<=duration<=60:
                result.append({'start':s['start'],'end':e['end'],'hook':s['text'],
                               'editorial_score':hook(s['text'])[0]['verdict'],
                               'note':'Heuristic only; review completeness and framing'})
                break
    return sorted(result,key=lambda c:-c['editorial_score'])


def clip(source,transcript_path,out, *,start,duration,evidence,metadata,campaign_context,campaign,account,allow_fixture=False):
    from .campaigns import number,eligibility,fingerprint
    decision=eligibility(campaign,account,allow_fixture=allow_fixture)
    if not decision['eligible']:raise ValueError('Campaign ineligible: '+'; '.join(decision['reasons']))
    if fingerprint(campaign)!=campaign_context.get('fingerprint'):
        raise ValueError('Campaign context does not bind current terms')
    if metadata['destination']['platform']!=account['platform']:
        raise ValueError('Account and destination platform differ')
    for disclosure in campaign['fields']['required_disclosures']['value']:
        if disclosure not in metadata['description']:raise ValueError('Missing required disclosure')
    number(start);number(duration,30,60)
    source=Path(source).resolve()
    if not source.is_file() or source.suffix.lower() not in {'.mp4','.mov','.mkv'}:
        raise ValueError('Ingest an authorized local media file')
    if evidence.get('source_sha256')!=digest(source) or evidence.get('commercial_clipping') is not True:
        raise ValueError('Exact-source commercial rights attestation required')
    for key in ('owner','evidence','audio_evidence','usage_scope'):
        if not evidence.get(key):raise ValueError('Missing rights evidence: '+key)
    if evidence['usage_scope']!=metadata['destination']:
        raise ValueError('Rights destination differs from metadata')
    p=probe(source)
    if start+duration>float(p['format']['duration'])+.05:raise ValueError('Clip exceeds source duration')
    cues=transcript(transcript_path)
    selected=[{'start':max(0,s['start']-start),'end':min(duration,s['end']-start),'text':s['text']}
              for s in cues if s['start']<start+duration and s['end']>start]
    if not selected:raise ValueError('No timed transcript covers selected clip')
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False)
    write(out/'spec.json',{'source_sha256':digest(source),'source_name':source.name,
          'start':start,'duration':duration,'rights':evidence,'campaign':campaign_context,
          'transcription':'supplied timed transcript; not automatic speech recognition'})
    write(out/'metadata.json',metadata)
    write(out/'context.json',campaign_context)
    write(out/'transcript.json',{'segments':selected})
    # User text is stripped of subtitle markup and stays in a data file.
    srt='\n\n'.join(f"{i+1}\n{timestamp(s['start'])} --> {timestamp(s['end'])}\n"+
        '\n'.join(textwrap.wrap(re.sub(r'[{}<>\\]',' ',s['text']),26)) for i,s in enumerate(selected))+'\n'
    (out/'captions.srt').write_text(srt)
    from .captions import ass
    (out/'captions.ass').write_text(ass(selected))
    began=time.monotonic()
    # Decoding is limited to file/pipe protocols; local media cannot trigger HTTP fetches.
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-protocol_whitelist','file,pipe',
                    '-ss',str(start),'-i',str(source),'-t',str(duration),'-map','0:v:0','-map','0:a?',
                    '-vf','scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,ass=captions.ass',
                    '-c:v','libx264','-preset','veryfast','-threads','2','-pix_fmt','yuv420p','-c:a','aac',
                    '-movflags','+faststart','video.mp4'],cwd=out,check=True,capture_output=True)
    report={'qc':qc(out/'video.mp4'),'rights':{'status':'attested_pending_human_review','evidence':evidence},
            'campaign':campaign_context,'elapsed_seconds':round(time.monotonic()-began,2),
            'external_api_cost_usd':0,'infrastructure_cost_usd':None,'state':'awaiting_human_approval',
            'compliance':{'automated_checks':'local-source hash and destination binding',
                          'human_checks':['terms','disclosures','framing','caption accuracy','commercial rights']}}
    report['qc']['audio']='source audio retained if present; verify audio rights'
    write(out/'report.json',report);write(out/'manifest.json',manifest(out))
    return report
