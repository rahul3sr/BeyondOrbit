"""Source-first editing. Missing media, rights or reviewed speech fails explicitly."""
from pathlib import Path
import json
import math
import shutil
import subprocess
import textwrap
import time
from .engine import digest,manifest,probe,read,write,timestamp
from .campaigns import now,when
from .captions import ass


def validate_rights(rights,source_sha,destination):
    required=('owner','document_sha256','document_reference','verified_by','verified_at','source_sha256')
    if any(not isinstance(rights.get(k),str) or not rights[k].strip() for k in required):raise ValueError('Structured source-rights documentation required')
    if rights['source_sha256']!=source_sha:raise ValueError('Rights bind a different source hash')
    for k in ('commercial_use','editing_allowed','audio_reuse'):
        if rights.get(k) is not True:raise ValueError('Unverified or incompatible rights: '+k)
    age=(now()-when(rights['verified_at'])).total_seconds()
    if not 0<=age<=86400:raise ValueError('Source rights verification is stale or in the future')
    if destination not in rights.get('destinations',[]):raise ValueError('Destination not within verified rights scope')
    for key in ('attribution','disclosures'):
        if not isinstance(rights.get(key),list) or any(not isinstance(s,str) for s in rights[key]):raise ValueError('Structured attribution/disclosures required')


def ingest(source,rights,out,*,fixture=False):
    source=Path(source).resolve();out=Path(out).resolve()
    if not source.is_file() or source.suffix.lower() not in {'.mp4','.mov','.mkv'}:raise ValueError('Supply an authorized MP4, MOV or MKV source')
    info=probe(source)
    if not any(s['codec_type']=='audio' for s in info['streams']):raise ValueError('Production requires source audio; no synthetic voice fallback')
    if not any(s['codec_type']=='video' for s in info['streams']):raise ValueError('Source has no video stream')
    if not fixture and rights.get('fixture'):raise ValueError('Test-media rights cannot authorize real production')
    sha=digest(source)
    destinations=rights.get('destinations',[])
    if not destinations:raise ValueError('Explicit rights destinations required')
    for d in destinations:validate_rights(rights,sha,d)
    # Keep the actual document: a hash/URL alone is not independent legal verification.
    doc=Path(rights['document_reference']).resolve()
    if not doc.is_file() or digest(doc)!=rights['document_sha256']:raise ValueError('Provide the rights document matching its hash')
    out.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(source,out/('source'+source.suffix.lower()))
    shutil.copyfile(doc,out/'rights-document.txt')
    write(out/'rights.json',rights)
    data={'version':1,'fixture':bool(fixture),'sha256':sha,'local_reference':str(source),
          'source_url':rights.get('source_url'),'filename':'source'+source.suffix.lower(),
          'rights':rights,'duration':float(info['format']['duration']),'media':info,'ingested_at':now().isoformat()}
    write(out/'source.json',data)
    return data


def validate_transcript(data,source_sha):
    if data.get('source_sha256')!=source_sha:raise ValueError('Transcript does not match source audio/video')
    if data.get('human_reviewed') is not True or not data.get('reviewed_by'):raise ValueError('Review/correct ASR against source audio before production rendering')
    last=0
    for s in data.get('segments',[]):
        if not all(isinstance(s.get(k),(int,float)) and math.isfinite(s[k]) for k in ('start','end')):raise ValueError('Finite transcript timestamps required')
        if not last<=s['start']<s['end'] or not isinstance(s.get('text'),str) or not s['text'].strip():raise ValueError('Invalid transcript timing/text')
        last=s['end']
    if last==0:raise ValueError('Empty transcript')


def propose_segments(data,min_seconds=25,max_seconds=45):
    segments=data['segments'];candidates=[]
    for i,s in enumerate(segments):
        for e in segments[i:]:
            duration=e['end']-s['start']
            if duration>max_seconds:break
            if duration>=min_seconds:
                candidates.append({'start':s['start'],'end':e['end'],'opening':s['text'],
                  'ending':e['text'],'checks':{k:'editor_review_required' for k in (
                  'clear_beginning','coherent_story','meaningful_ending','speaker_continuity',
                  'audible_clarity','visual_relevance','natural_pacing')},'predicts_virality':False})
                break
    return candidates


def render_clip(asset,transcript,selection,metadata,out,*,campaign=None,account=None,fixture=False):
    began=time.monotonic();asset=Path(asset).resolve();out=Path(out).resolve()
    source=read(asset/'source.json');rights=source['rights'];destination=metadata['destination']
    if source['fixture'] and not fixture:raise ValueError('Synthetic test footage cannot be represented as production footage')
    original=asset/source['filename']
    if digest(original)!=source['sha256']:raise ValueError('Source file changed')
    validate_rights(rights,source['sha256'],destination)
    data=read(transcript);validate_transcript(data,source['sha256'])
    if not selection.get('editor') or selection.get('confirmed') is not True:raise ValueError('Explicit editor selection required')
    for k in ('clear_beginning','coherent_story','meaningful_ending','speaker_continuity','audible_clarity','visual_relevance','natural_pacing'):
        if selection.get('creative_checks',{}).get(k) is not True:raise ValueError('Editor must verify: '+k)
    from .campaigns import number,eligibility,identity,fingerprint
    start=number(selection['start']);end=number(selection['end'])
    if not 25<=end-start<=45 or end>source['duration']+.02:raise ValueError('Select a 25–45 second interval within source')
    framing=selection['framing'];x=number(framing['x'],0,1);y=number(framing['y'],0,1)
    width=framing.get('width',1080);height=framing.get('height',1920)
    if (width,height) not in {(720,1280),(1080,1920)}:raise ValueError('Choose 720x1280 or 1080x1920')
    caption_size=number(selection.get('caption_size',42),28,60)
    duration=end-start
    needed=rights['attribution']+rights['disclosures']
    context=None
    if campaign:
        result=eligibility(campaign,account or {})
        if not result['eligible']:raise ValueError('Campaign ineligible: '+'; '.join(result['reasons']))
        needed+=campaign['fields']['required_disclosures']['value']
        if campaign['fields']['source_footage']['value']!=source['sha256']:raise ValueError('Campaign permits a different source asset')
        context={'campaign_id':identity(campaign),'fingerprint':fingerprint(campaign),'fixture':False}
    if any(text not in metadata['description'] for text in needed):raise ValueError('Required attribution/disclosures missing')
    if not 1<=len(metadata['title'])<=100 or len(metadata['description'])>5000:raise ValueError('Invalid platform metadata length')
    selected=[{'start':max(0,s['start']-start),'end':min(duration,s['end']-start),'text':s['text']} for s in data['segments'] if s['start']<end and s['end']>start]
    if not selected:raise ValueError('No speech captions in selection')
    out.mkdir(parents=True,exist_ok=False)
    write(out/'source.json',source);write(out/'rights.json',rights);write(out/'selection.json',selection)
    shutil.copyfile(asset/'rights-document.txt',out/'rights-document.txt')
    write(out/'metadata.json',metadata);write(out/'transcript.json',{'source_sha256':source['sha256'],'segments':selected,'human_reviewed':True,'reviewed_by':data['reviewed_by']})
    write(out/'spec.json',{'type':'source_clip','fixture':bool(fixture),'source_sha256':source['sha256'],'source_name':Path(source['local_reference']).name,
        'source_start':start,'duration':duration,'preserves_source_audio':True})
    if context:write(out/'context.json',context)
    style=ass(selected).replace('DejaVu Sans,42,',f'DejaVu Sans,{caption_size},').replace(',0,5,70,70,100,1',',0,2,60,60,235,1')
    (out/'captions.ass').write_text(style)
    (out/'captions.srt').write_text('\n\n'.join(f"{i+1}\n{timestamp(s['start'])} --> {timestamp(s['end'])}\n"+'\n'.join(textwrap.wrap(s['text'],28)) for i,s in enumerate(selected))+'\n')
    vf=f'scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}:(iw-ow)*{x}:(ih-oh)*{y},ass=captions.ass'
    subprocess.run(['ffmpeg','-v','error','-nostdin','-protocol_whitelist','file,pipe','-ss',str(start),'-i',str(original),'-t',str(duration),
        '-map','0:v:0','-map','0:a:0','-vf',vf,'-c:v','libx264','-preset','veryfast','-crf','20','-threads','2','-pix_fmt','yuv420p',
        '-c:a','aac','-ar','48000','-b:a','160k','-movflags','+faststart','video.mp4'],cwd=out,check=True,capture_output=True,timeout=300)
    from .quality import inspect
    qa=inspect(out/'video.mp4',selected,source=original,source_start=start,caption_size=caption_size)
    write(out/'report.json',{'qc':qa,'rights':{'status':'documented_attestation_requires_human_approval','source_sha256':source['sha256']},
        'creative_approval':'pending','state':'awaiting_human_review','fixture':bool(fixture)})
    write(out/'costs.json',{'external_api_usd':0,'render_wall_seconds':round(time.monotonic()-began,3),'compute_usd':None,'note':'CPU cost unmetered; no paid APIs used'})
    write(out/'manifest.json',manifest(out))
    # A source-frame crop preview, not a substitute for reviewing the actual output.
    subprocess.run(['ffmpeg','-v','error','-ss','2','-i',str(out/'video.mp4'),'-frames:v','1',str(out/'preview.jpg')],check=True,capture_output=True,timeout=30)
    if not qa['passed']:raise ValueError('Production technical QA failed; inspect report.json. Nothing was approved or uploaded.')
    return out


def preview_crop(asset,selection,out):
    asset=Path(asset);source=read(asset/'source.json')
    from .campaigns import number
    f=selection['framing'];x=number(f['x'],0,1);y=number(f['y'],0,1)
    width=f.get('width',1080);height=f.get('height',1920)
    if (width,height) not in {(720,1280),(1080,1920)}:raise ValueError('Invalid framing resolution')
    if digest(asset/source['filename'])!=source['sha256']:raise ValueError('Source changed')
    subprocess.run(['ffmpeg','-v','error','-nostdin','-protocol_whitelist','file,pipe','-ss',str(number(selection['start'])),
        '-i',str((asset/source['filename']).resolve()),'-vf',f'scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}:(iw-ow)*{x}:(ih-oh)*{y}',
        '-frames:v','1',str(Path(out).resolve())],check=True,capture_output=True,timeout=30)
    return Path(out)
