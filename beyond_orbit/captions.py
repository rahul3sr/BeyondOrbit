"""Deterministic captions; no subtitle markup from user content."""
import re
import textwrap

HEADER='''[Script Info]
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,DejaVu Sans,42,&H00FFFFFF,&H00FFFFFF,&H00101B35,&H00101B35,0,0,0,0,100,100,0,0,1,2,0,5,70,70,100,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''

def ass(cues):
    def at(t):
        cs=round(t*100)
        return f'{cs//360000}:{cs//6000%60:02}:{cs//100%60:02}.{cs%100:02}'
    events=[]
    for s in cues:
        safe=re.sub(r'[{}\\\r\n]',' ',s['text'])
        safe='\\N'.join(textwrap.wrap(safe,23))
        events.append(f"Dialogue: 0,{at(s['start'])},{at(s['end'])},Default,,0,0,0,,{safe}")
    return HEADER+'\n'.join(events)+'\n'
