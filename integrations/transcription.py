"""Optional local ASR adapter. Not installed or live-validated in this milestone.
Only an explicitly supplied local model directory is accepted; no model downloads.
"""
from pathlib import Path
from beyond_orbit.engine import write


def transcribe(source,model_dir,out):
    source=Path(source).resolve();model_dir=Path(model_dir).resolve()
    if not source.is_file() or not model_dir.is_dir():raise ValueError('Local source and approved local ASR model required')
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise RuntimeError('Optional faster-whisper package is not installed; supply a timed transcript meanwhile') from None
    model=WhisperModel(str(model_dir),device='cpu',compute_type='int8',local_files_only=True)
    segments,info=model.transcribe(str(source),beam_size=5)
    data={'language':info.language,'segments':[{'start':s.start,'end':s.end,'text':s.text.strip()} for s in segments],
          'source':'local ASR; human caption accuracy review required'}
    write(out,data)
    return data
