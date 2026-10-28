"""Pinned, local CLI utilities. No plugin installer or Claude runtime required."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]/'vendor/youtube-agent-skill'
TOOLS = {'hook': 'yt-script/hookscore.py', 'title': 'yt-package/title.py',
         'edit': 'yt-edit/deadair.py', 'chapters': 'yt-chapters/chapters.py',
         'retention': 'yt-retention/retention.py', 'outliers': 'yt-viral/swipe.py'}


def verify_vendor():
    data = json.loads((ROOT/'PROVENANCE.json').read_text())
    for name, expected in data['files'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != expected:
            raise ValueError('Vendored utility integrity mismatch')
    return data['commit']


def run(tool, *args):
    verify_vendor()
    result = subprocess.run([sys.executable, '-I', str(ROOT/'skills'/TOOLS[tool]),
                             *map(str, args), '--json'], check=True,
                            text=True, capture_output=True, timeout=30)
    return json.loads(result.stdout)


def hook(text):
    return run('hook', '--hook', text)


def package(title, thumbnail):
    return run('title', '--title', title, '--thumb', thumbnail)


def edit(transcript):
    if Path(transcript).suffix.lower() not in {'.srt', '.vtt'}:
        raise ValueError('Adapter accepts SRT/VTT; upstream JSON list parser is defective')
    result = run('edit', Path(transcript).resolve())
    # Merge overlapping edit ranges instead of trusting upstream summed cut durations.
    merged = []
    for c in sorted(result['cuts'], key=lambda c: c['start']):
        a, b = max(0, c['start']), min(result['duration'], c['end'])
        if b <= a:
            continue
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    result['removed'] = round(sum(b-a for a,b in merged),3)
    result['out'] = round(result['duration']-result['removed'],3)
    result['merged_ranges'] = merged
    return result
