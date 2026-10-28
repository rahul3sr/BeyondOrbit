# Beyond Orbit — Apollo 15 review draft

Status: NOT PUBLISHED. This is a real-footage review draft, not an accepted professional Short.

## Completed
- Recovered rahul3sr/BeyondOrbit at bb3802290392257d6ac68a91806a0c6d094f4412; inspected default and research branches. Repository is PUBLIC.
- Downloaded and decoded original NASA Apollo 15 M4V (640x480, 82.816 seconds). Original MOV alternative downloaded but failed decoding. The separate 19-minute NASA Megan McArthur interview also downloaded successfully; it was not selected.
- Produced 29.83-second 720x1280 H.264/AAC review draft from 00:39.500–01:09.300. Full 4:3 source frame, original radio speech; no synthetic voice or added music.
- Reused existing caption generator and technical QA. All 12 mechanical checks pass. Zero detected frozen/black/silent seconds; clipped audio fraction zero; source audio correlation 0.9995, estimated offset zero (first ten seconds only).
- Existing test suite: 89/89 passed after installing the already reviewed hash-pinned dependencies. Initial run had one missing-dependency error. Security check passed.

## Rights evidence and limits
NASA identifies the individual asset's credit as NASA:
https://science.nasa.gov/resource/the-apollo-15-hammer-feather-drop/

Media guidelines:
https://www.nasa.gov/nasa-brand-center/images-and-media/

The editorial-use basis is original government mission footage used factually, with NASA attribution and no implied endorsement. This does not grant blanket advertising, merchandise or personality rights; NASA specifically identifies restrictions for recognizable people. Do not use the astronaut to endorse Beyond Orbit, sponsors or products. No third-party music was added. Complete audiovisual rights review and final owner acceptance remain pending; do not assert unrestricted commercial clearance.

Historical transcript reference:
https://www.apollojournals.org/alsj/a15/a15.clsout3.html
Only original mission speech is used for proposed captions, not the later copyrighted commentary. Cue timing is provisional, based on mission speech and rough ASR landmarks, and has NOT been verified by listening. PocketSphinx's unconstrained recognition was poor; forced alignment failed twice. Mechanical cue bounds passing is NOT proof of synchronization or caption accuracy. No human-reviewed flag was fabricated.

## Creative assessment
The real lunar experiment has a clear visual payoff. Full-frame presentation avoids cropping the falling objects. Archival 640x480 footage and radio audio limit perceived quality; upscaling is not new detail. Caption timing, wording, sentence boundaries and opening effectiveness need review. Current status is unapproved draft, not publication-ready.

## Publishing and cloud status
Studio required sign-in; no channel identity or upload permission was verified. Existing uploader remains mock-only. Metricool was discovered and suggested, but no installation/connection was confirmed. No public upload, paid campaign submission or paid infrastructure was created. Existing PublicationGate and human-review requirements were not altered. Source acquisition and rendering ran in the remote workspace without the user's MacBook; persistent deployment remains unconfigured.

## Costs and blockers
No paid AI credits or new paid infrastructure used. Runtime compute cost unavailable. A proposed faster-whisper installation was rejected by automatic approval review as an unreviewed dependency; no bypass was attempted. The existing hash-pinned PocketSphinx dependencies were then used successfully. No neural ASR benchmark completed.

## Reproduce
From the existing Phase 2 checkout, install requirements-asr.lock with --require-hashes --only-binary=:all: into Python 3.12 venv. Download source URL in source-manifest.json; verify hash. Run:
`.venv/bin/python scripts/apollo15_draft.py /absolute/path/apollo15.m4v /absolute/path/review`
Then `.venv/bin/python scripts/run_checks.py` and `.venv/bin/python scripts/security_check.py`.
The separate draft script does not register an asset, manufacture approval or publish. Do not treat its output as approved input to a publishing integration.

## Campaign readiness
ContentRewards and Vyro live integration was not validated in this run. Existing manual brief import remains available; it does not prove campaign availability or permission. No earnings claimed.

Next prerequisites: verify/correct captions against audio and authenticate the intended channel through a supported connection. End-to-end public publishing is incomplete.
