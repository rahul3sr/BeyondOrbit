# Beyond Orbit

An offline-first, approval-gated media production prototype. This milestone produces an original silent 36-second vertical text video. It never uploads content.

## Run

Requires Python 3.12+, FFmpeg/ffprobe with libx264 and libass, and DejaVu Sans (available in the prepared cloud machine). No pip dependencies.

```bash
python3 -m unittest discover -s tests -v
python3 -m beyond_orbit demo --out artifacts/my-review
# Or supply your own original script specification:
python3 -m beyond_orbit render examples/original.json --out artifacts/another-review
```

Use a fresh output directory each time. Review video.mp4, captions.srt, captions.ass, metadata.json, spec.json, report.json and manifest.json. Artifacts are intentionally ignored by Git. Captions are generated from script timing, not speech transcription. Do not claim this text-only demo is finished production quality.

The manifest binds exact media, captions, script, metadata, rights and QC report. A future human approval record must include decision `approved`, reviewer, approved_at, manifest_sha256 and the exact destination from metadata.json. `python3 -m beyond_orbit verify-approval ARTIFACT_DIR RECORD.json` checks binding only; it does not authenticate the reviewer or upload. A trusted approval service is required before production publishing. No real approval record has been created.

See [module status](agents/README.md), [third-party audit](docs/third-party-audit.md), and [cloud/integration decisions](docs/cloud-and-integrations.md). All live integrations are unverified. Clipping, narration, transcription, official OAuth publishing, channel analytics and scheduled execution remain incomplete.
