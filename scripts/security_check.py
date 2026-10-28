"""Focused source scan and vendored checksum verification; not a full security audit."""
from pathlib import Path
import re
import subprocess
import sys

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
from beyond_orbit.skills import verify_vendor
verify_vendor()
patterns=[re.compile(x) for x in (r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
                                 r'gh[pousr]_[A-Za-z0-9]{20,}',r'AIza[0-9A-Za-z_-]{35}')]
files=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard'],cwd=root,text=True).splitlines()
failures=[]
for name in files:
    p=root/name
    if not p.is_file():continue
    if p.suffix.lower() in {'.mp4','.wav','.sqlite','.bundle'} or p.name=='.env':failures.append(name+': disallowed source artifact')
    text=p.read_text(errors='replace')
    if any(pattern.search(text) for pattern in patterns):failures.append(name+': possible credential (value withheld)')
if failures:
    print('\n'.join(failures));sys.exit(1)
print(f'PASS: focused credential-pattern scan of {len(files)} source files; vendored integrity verified. No pip dependencies to audit.')
