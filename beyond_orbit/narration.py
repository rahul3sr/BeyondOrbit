"""Optional system Flite narration. No network or paid API calls."""
import subprocess
from .engine import probe


def narrate(scenes,step,out,*,fixture=False):
    if not fixture:raise ValueError("Flite is forbidden in production; retain source speech or configure an approved natural narration provider")
    for i,text in enumerate(scenes):
        (out/f'speech{i}.txt').write_text(text)
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-f','lavfi',
                        '-i',f'flite=textfile=speech{i}.txt:voice=slt',f'raw{i}.wav'],cwd=out,check=True,capture_output=True)
    (out/'audio-list.txt').write_text(''.join(f"file raw{i}.wav\n" for i in range(len(scenes))))
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-f','concat','-safe','1',
                    '-i','audio-list.txt','-c','copy','narration.wav'],cwd=out,check=True,capture_output=True)
