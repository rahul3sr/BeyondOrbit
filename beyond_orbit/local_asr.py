"""Reproducible, offline English ASR. Drafts always require audio-checked editing."""
from pathlib import Path
import importlib.metadata
import os
import re
import subprocess
from .engine import digest,write


def transcribe(source,out):
    try:from pocketsphinx import Decoder
    except ImportError:raise RuntimeError('Use .venv/bin/python after installing requirements-asr.lock') from None
    source=Path(source).resolve()
    pcm=subprocess.run(['ffmpeg','-v','error','-nostdin','-protocol_whitelist','file,pipe','-i',str(source),
        '-vn','-ac','1','-ar','16000','-f','s16le','-'],check=True,capture_output=True,timeout=180).stdout
    if not pcm:raise ValueError('No source audio available')
    decoder=Decoder(logfn=os.devnull);decoder.start_utt();decoder.process_raw(pcm,False,True);decoder.end_utt()
    words=[]
    for s in decoder.seg() or []:
        if s.word.startswith(('<','[')):continue
        text=re.sub(r'\(\d+\)$','',s.word)
        words.append({'start':round(s.start_frame/100,3),'end':round((s.end_frame+1)/100,3),'text':text})
    if not words:raise ValueError('No speech recognized; supply an audio-verified transcript or a higher-quality approved ASR model')
    segments=[]
    for i in range(0,len(words),7):
        group=words[i:i+7]
        segments.append({'start':group[0]['start'],'end':group[-1]['end'],'text':' '.join(w['text'] for w in group)})
    result={'source_sha256':digest(source),'engine':'pocketsphinx','version':importlib.metadata.version('pocketsphinx'),
        'model':'bundled English model','words':words,'segments':segments,'human_reviewed':False,'reviewed_by':None,
        'limitations':['Offline English baseline; accuracy must be measured on the actual source','Not neural ASR; no automatic accuracy guarantee'],
        'external_api_usd':0}
    write(out,result);return result


def word_error_rate(reference,hypothesis):
    a=re.findall(r"[a-z0-9']+",reference.lower());b=re.findall(r"[a-z0-9']+",hypothesis.lower())
    previous=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        current=[i]
        for j,y in enumerate(b,1):current.append(min(previous[j]+1,current[j-1]+1,previous[j-1]+(x!=y)))
        previous=current
    return previous[-1]/max(1,len(a))
