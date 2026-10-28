# Beyond Orbit

A working local campaign-to-video and original-video engine with version-bound human review and mock-only publishing. This extends the preserved offline prototype; it is not a live monetized or continuously running service.

## Verified workflow

```bash
python3 -m unittest discover -s tests -v
python3 scripts/security_check.py
python3 -m beyond_orbit.operations demo --out artifacts/NEW_RUN_NAME
```

The demo imports an explicitly synthetic campaign, checks a zero-follower test account, computes three illustrative profitability scenarios, renders a 48-second narrated original video, creates authorized source footage, ranks transcript segments, extracts a 32-second vertical clip, generates captions/metadata, checks technical quality, records costs and stops awaiting human approval. No public upload, campaign submission or real approval is made. Use a fresh output directory.

Python 3.12+, FFmpeg/ffprobe with libx264/libass/Flite and DejaVu Sans are required. No pip packages are required. All six audited YouTube utilities are pinned with MIT attribution and checksums; no plugin installer or permanent Claude process is needed.

## Working capabilities and boundaries

Campaign imports, evidence labels, deduplication, revisions, eligibility, contribution ranking, local video production, captions, narration, quality reports, individual authenticated review, local job queue, mock platform adapters and operating reports work in tests. Both original baseline videos and recovery files remain preserved.

Live marketplace discovery, automatic speech transcription, factual topic research, Higgsfield generation, Google authorization, real uploads, hosted review, permanent scheduling and channel revenue data are NOT connected. There are no verified current paid campaign opportunities or actual earnings. Mock protocol tests are not live integration validation.

See [operating guide](docs/operating-guide.md), [architecture](docs/architecture.md), [third-party audit](docs/third-party-audit.md), [cloud status](infrastructure/README.md), and [machine-readable status](reports/status.json).
