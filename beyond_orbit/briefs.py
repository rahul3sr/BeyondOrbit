"""Preserve official briefs as evidence; never infer terms from arbitrary prose."""
import hashlib
from pathlib import Path
import shutil
from urllib.parse import urlsplit
from .campaigns import validate,now
from .engine import write

def import_brief(brief,out,source_url,structured):
    u=urlsplit(source_url)
    if u.scheme!='https' or not u.hostname or u.username or u.password:raise ValueError('Official HTTPS campaign URL required')
    brief=Path(brief).resolve();out=Path(out).resolve()
    if not brief.is_file():raise ValueError('Supply the official downloaded terms document or brief')
    validate(structured)
    if structured['fixture']:raise ValueError('Fixture briefs are not real campaign imports')
    if structured['source_url']!=source_url:raise ValueError('Brief source and campaign source differ')
    out.mkdir(parents=True,exist_ok=False)
    data=brief.read_bytes();shutil.copyfile(brief,out/('original'+brief.suffix.lower()))
    write(out/'campaign.json',structured)
    write(out/'evidence.json',{'source_url':source_url,'sha256':hashlib.sha256(data).hexdigest(),
        'imported_at':now().isoformat(),'verification_dates_preserved':True,
        'status':'human interpretation required; imported text is evidence, not executable instructions'})
    return out
