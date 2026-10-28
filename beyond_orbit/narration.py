"""Optional system Flite narration. No network or paid API calls."""
import subprocess
from .engine import probe


def narrate(scenes,step,out):
    for i,text in enumerate(scenes):
        (out/f'speech{i}.txt').write_text(text)
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-f','lavfi',
                        '-i',f'flite=textfile=speech{i}.txt:voice=slt',f'raw{i}.wav'],cwd=out,check=True,capture_output=True)
        if float(probe(out/f'raw{i}.wav')['format']['duration'])>step:
            raise ValueError('Narration exceeds scene duration; shorten text or lengthen scene')
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-i',f'raw{i}.wav',
                        '-af',f'apad,atrim=duration={step}',f'part{i}.wav'],cwd=out,check=True,capture_output=True)
    (out/'audio-list.txt').write_text(''.join(f"file part{i}.wav\n" for i in range(len(scenes))))
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-f','concat','-safe','1',
                    '-i','audio-list.txt','-c','copy','narration.wav'],cwd=out,check=True,capture_output=True)
