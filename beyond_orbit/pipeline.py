"""Production CLI: ingest -> transcribe -> inspect candidates -> editor selection -> render."""
import argparse
import json
from pathlib import Path
from .engine import read,write
from .production import ingest,render_clip,propose_segments,preview_crop


def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='cmd',required=True)
    a=s.add_parser('ingest');a.add_argument('source');a.add_argument('--rights',required=True);a.add_argument('--out',required=True)
    a=s.add_parser('transcribe');a.add_argument('source');a.add_argument('--out',required=True)
    a=s.add_parser('candidates');a.add_argument('transcript');a.add_argument('--out',required=True)
    a=s.add_parser('preview');a.add_argument('--asset',required=True);a.add_argument('--selection',required=True);a.add_argument('--out',required=True)
    a=s.add_parser('render');a.add_argument('--asset',required=True);a.add_argument('--transcript',required=True);a.add_argument('--selection',required=True);a.add_argument('--metadata',required=True);a.add_argument('--out',required=True);a.add_argument('--campaign');a.add_argument('--account');a.add_argument('--db',default='state/operations.sqlite')
    a=p.parse_args()
    if a.cmd=='ingest':result=ingest(a.source,read(a.rights),a.out)
    elif a.cmd=='transcribe':
        from .local_asr import transcribe
        result=transcribe(a.source,a.out)
    elif a.cmd=='candidates':result=propose_segments(read(a.transcript));write(a.out,result)
    elif a.cmd=='preview':result={'preview':str(preview_crop(a.asset,read(a.selection),a.out))}
    else:
        campaign=read(a.campaign) if a.campaign else None
        account=read(a.account) if a.account else None
        output=render_clip(a.asset,a.transcript,read(a.selection),read(a.metadata),a.out,campaign=campaign,account=account)
        from .store import Store
        store=Store(a.db)
        campaign_id=store.import_campaign(campaign)['id'] if campaign else None
        review=store.register(output,campaign_id,account)
        result={'artifact':str(output),'creative_review_id':review,'review_database':a.db,
                'state':'pending_creative_review','publication_authorized':False}

    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
