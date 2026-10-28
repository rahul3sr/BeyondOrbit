"""Offline first-party video production. No publication capability is enabled."""
import hashlib
import json
import subprocess
import textwrap
import time
from pathlib import Path


def read(path):
    return json.loads(Path(path).read_text())


def write(path, data):
    Path(path).write_text(json.dumps(data, indent=2) + "\n")


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rights_check(spec):
    # Evidence is a reviewable attestation, never automated legal verification.
    rights = spec.get("rights", {})
    required = {"script", "visuals", "audio"}
    if set(rights) != required:
        raise ValueError("Rights evidence required for script, visuals, and audio")
    for kind, evidence in rights.items():
        if evidence.get("basis") not in {"original", "licensed", "none"}:
            raise ValueError(f"Unsupported rights: {kind}")
        if not evidence.get("evidence", "").strip():
            raise ValueError(f"Missing evidence: {kind}")
        if evidence["basis"] == "none" and kind != "audio":
            raise ValueError("Only audio may be absent")
    if rights["visuals"]["basis"] != "original" or (rights["audio"]["basis"] != "none" and not (rights["audio"]["basis"] == "original" and spec.get("narration") is True)):
        raise ValueError("This renderer supports original graphics and no audio only")
    return {"status": "documented_pending_human_review", "evidence": rights,
            "legal_verification": False}


def score(text):
    # Transparent editorial checklist, not a viral performance prediction.
    words = text.split()
    parts = {"concise": 25 if 4 <= len(words) <= 18 else 0,
             "question": 25 if "?" in text else 0,
             "direct_address": 25 if "you" in text.lower() else 0,
             "concrete_number": 25 if any(c.isdigit() for c in text) else 0}
    return {"score": sum(parts.values()), "components": parts,
            "predicts_virality": False}


def probe(path):
    result = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format",
                             "-of", "json", str(path)], check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def qc(path):
    p = probe(path)
    v = next(s for s in p["streams"] if s["codec_type"] == "video")
    duration = float(p["format"]["duration"])
    checks = {"duration_30_to_60": 30 <= duration <= 60,
              "vertical_9_16": v["width"] * 16 == v["height"] * 9,
              "h264": v["codec_name"] == "h264", "nonempty": Path(path).stat().st_size > 1000}
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"],
                   check=True, capture_output=True)
    checks["fully_decodable"] = True
    return {"passed": all(checks.values()), "checks": checks, "duration": duration,
            "resolution": [v["width"], v["height"]],
            "human_review_required": ["readability", "factual accuracy", "rights", "pacing"],
            "audio": "intentionally silent; no narration or music"}


def timestamp(seconds):
    ms = round(seconds * 1000)
    return f"{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}"


def render(spec, out):
    started = time.monotonic()
    rights = rights_check(spec)
    scenes = spec["scenes"]
    if not scenes or any(not isinstance(s, str) or not s.strip() or len(s) > 200 for s in scenes):
        raise ValueError("Use nonempty scene text, at most 200 characters per scene")
    duration = spec.get("duration", 36)
    if not 30 <= duration <= 60:
        raise ValueError("Duration must be 30–60 seconds")
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    write(out / "spec.json", spec)
    step = duration / len(scenes)
    srt = "\n\n".join(f"{i+1}\n{timestamp(i*step)} --> {timestamp((i+1)*step)}\n" +
                         "\n".join(textwrap.wrap(text, 27)) for i, text in enumerate(scenes)) + "\n"
    (out / "captions.srt").write_text(srt)
    def ass_time(t):
        cs = round(t * 100)
        return f"{cs//360000}:{cs//6000%60:02}:{cs//100%60:02}.{cs%100:02}"
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,DejaVu Sans,42,&H00FFFFFF,&H00FFFFFF,&H00101B35,&H00101B35,0,0,0,0,100,100,0,0,1,2,0,5,70,70,100,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for i, text in enumerate(scenes):
        # Strip subtitle markup controls before inserting display text.
        safe = text.replace("\\", " ").replace("{", "(").replace("}", ")")
        safe = "\\N".join(textwrap.wrap(safe, 23))
        events.append(f"Dialogue: 0,{ass_time(i*step)},{ass_time((i+1)*step)},Default,,0,0,0,,{safe}")
    (out / "captions.ass").write_text(header + "\n".join(events) + "\n")
    # Fixed local filenames and argv: user text never becomes a shell or filter expression.
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-f", "lavfi", "-i",
           f"color=c=0x101b35:s=720x1280:r=24:d={duration}", "-vf",
           "drawbox=x=40:y=360:w=640:h=560:color=0x203352:t=fill,"
           "ass=captions.ass",
           "-an", "-c:v", "libx264", "-preset", "veryfast", "-threads", "2", "-pix_fmt", "yuv420p",
           "-movflags", "+faststart", "video.mp4"]
    if spec.get('narration'):
        from .narration import narrate
        narrate(scenes, step, out)
        cmd = cmd[:cmd.index('-vf')] + ['-i', 'narration.wav'] + cmd[cmd.index('-vf'):]
        cmd.remove('-an')
        cmd[-1:-1] = ['-map', '0:v:0', '-map', '1:a:0', '-c:a', 'aac']
    subprocess.run(cmd, cwd=out, check=True, capture_output=True)
    metadata = {"title": spec["title"], "description": spec["description"],
                "destination": {"platform": "youtube", "channel": "@BeyondOrbitVentures", "privacy": "private"}}
    if not 1 <= len(metadata["title"]) <= 100 or len(metadata["description"]) > 5000:
        raise ValueError("Invalid YouTube metadata length")
    write(out / "metadata.json", metadata)
    report = {"rights": rights, "qc": qc(out / "video.mp4"), "hook": score(scenes[0]),
              "elapsed_seconds": round(time.monotonic()-started, 2), "external_api_cost_usd": 0,
              "infrastructure_cost_usd": None, "state": "awaiting_human_approval"}
    if spec.get("narration"):
        report["qc"]["audio"] = "Synthetic Flite narration, timed per original scene; human pronunciation review required"
    write(out / "report.json", report)
    write(out / "manifest.json", manifest(out))
    return report


BOUND_FILES = ("video.mp4", "captions.srt", "captions.ass", "metadata.json", "spec.json", "report.json")

def manifest(out):
    out = Path(out)
    names = BOUND_FILES + tuple(n for n in ("context.json", "transcript.json") if (out/n).exists())
    hashes = {name: digest(out / name) for name in names}
    encoded = json.dumps(hashes, sort_keys=True).encode()
    return {"sha256": hashlib.sha256(encoded).hexdigest(), "files": hashes}


def check_approval(out, record):
    current = manifest(out)
    if read(Path(out) / "manifest.json") != current:
        raise ValueError("Artifact changed: regenerate manifest and obtain reapproval")
    approval = read(record)
    if approval.get("manifest_sha256") != current["sha256"] or approval.get("decision") != "approved":
        raise ValueError("Missing exact-version approval")
    if not approval.get("reviewer") or not approval.get("approved_at"):
        raise ValueError("Reviewer and approval time are required")
    if approval.get("destination") != read(Path(out)/"metadata.json")["destination"]:
        raise ValueError("Destination differs from approval")
    if not read(Path(out)/"report.json")["qc"]["passed"]:
        raise ValueError("QC failed")
    return True
