# Phase 2: source-first clipping and repaired safeguards

This milestone repairs the audited code at 7920e77. It does not provide a real campaign source, connect Google credentials, activate paid hosting, or publish content. The existing recovery archives and rejected artifacts remain preserved.

## Exact source-ingestion interface

Use `.venv/bin/python`; dependencies are pinned for Python 3.12 Linux x86_64 in `requirements-asr.lock`, including bundled offline English ASR models. The checked-in PocketSphinx test sample has upstream provenance and license under tests/data. No ASR API is called.

1. Supply an authorized MP4/MOV/MKV with natural speech and its actual rights document. Populate `examples/production/rights.template.json` with the exact source/document SHA-256, owner, commercial edit/audio permissions, specific destination, current verification, attribution and disclosures. False or missing permissions fail.
2. `.venv/bin/python -m beyond_orbit.pipeline ingest SOURCE --rights RIGHTS.json --out artifacts/ASSET`
3. `.venv/bin/python -m beyond_orbit.pipeline transcribe artifacts/ASSET/source.mp4 --out artifacts/transcript-draft.json` (use the source's actual extension).
4. Listen to the source, correct words and timing, then set `human_reviewed: true` and identify `reviewed_by`. The draft is deliberately blocked from production. PocketSphinx is an offline baseline, not neural ASR. A separately measured existing synthetic-speech test had 22.41% WER; this cannot be treated as publication-ready transcription. The pinned short natural-speech test is much narrower than arbitrary real-world speech.
5. Generate candidate intervals with `.venv/bin/python -m beyond_orbit.pipeline candidates TRANSCRIPT.json --out CANDIDATES.json`. Candidate editorial criteria remain explicitly unverified until an editor selects them; no viral prediction is made.
6. Fill `selection.template.json`: 25–45 seconds, editor identity, confirmed selection, seven editorial checks, normalized crop x/y, resolution (720x1280 or 1080x1920), optional caption font size. The source speech is retained without padding or voice replacement.
7. Preview the crop before rendering: `.venv/bin/python -m beyond_orbit.pipeline preview --asset ASSET --selection SELECTION.json --out crop-preview.jpg`.
8. Render: `.venv/bin/python -m beyond_orbit.pipeline render --asset ASSET --transcript TRANSCRIPT.json --selection SELECTION.json --metadata METADATA.json --out artifacts/CLIP`. Optional --campaign and --account enforce campaign eligibility and exact footage association. Metadata must contain all required attribution/disclosures.
9. The production render CLI registers passing output in `state/operations.sqlite` (override with --db) as pending creative review. It never authorizes publication. Review video.mp4, source.json, rights.json, rights-document.txt, transcript.json, selection.json, captions.srt, captions.ass, report.json, costs.json, preview.jpg and manifest.json. A failed QA leaves diagnostic output but returns an error and never approves/uploads it.

No source was supplied that qualifies for the requested professional demonstration. The saved Phase 2 output is only a procedural moving-pattern/chirp development fixture. It contains no human speech or real campaign and is explicitly rejected by the publication authority. It must not be presented as the requested Short.

## Approval authority

`PublicationGate` authenticates individual adult reviewer identities, verifies exact media/metadata and destination evidence, and snapshots artifact files into read-only copies. Its HMAC seal binds media version, source/campaign/account context, destination evidence, reviewer decision, and explicit publication authorization. Dispatch revalidates evidence freshness, expiry, registry terms, metadata and final payload bytes. Duplicate dispatch claims are blocked. A snapshot hash cannot authenticate legal claims; an authorized owner still must verify the original rights documents and official channel/account evidence.

An owner can record signed `attest_destination(...)` evidence only after checking the official channel/account response. No real channel evidence was verified in Phase 2. Missing, stale or tampered evidence blocks registration. There is no automatic assertion that a supplied channel string is authenticated.

The review service optionally receives the authority when individual users and a stable `BEYOND_ORBIT_APPROVAL_KEY` are securely configured. Production reviews use a separate endpoint and an unchecked-by-default explicit private-publication authorization box. A creative approval alone does not authorize upload. No real review credentials/signing key were provisioned. Legacy Store review and JSON approval checks are for local technical/simulation workflows; they are not consumed by the publication authority.

Direct YouTubeProtocol.private_upload is denied. The only permitted protocol transport is the exact in-memory RecordingTransport type, via PublicationGate or explicitly named simulation methods. No real upload transport or Google credentials are connected. Simulations are not live upload validation.

## Campaign import and freshness

Campaign JSON now validates collection/boolean types. Real campaigns require structured account/participant age restrictions and current manual review of uninterpreted terms. Financial evidence expires after 24 hours. Synthetic records are labelled inactive. Registration checks campaign context identity/fingerprint, and dispatch checks current terms and eligibility. The production renderer and publication authority require the campaign source_footage value to equal the actual source SHA-256.

`beyond_orbit.briefs.import_brief` preserves the original official document, its hash, the URL, structured record and original verification timestamps. It never converts unparsed prose into verified terms. Importing the URL/document does not prove availability or rights. ContentRewards/Vyro remain proxy-denied; supported interfaces/authentication requirements are unverified. No campaign applications or submissions are implemented.

Higgsfield remains an isolated explicit mock. Official site/docs access was proxy-denied again. No supported API contract, commercial terms, subscription entitlement or pricing was verified, so no speculative provider adapter was added and no credits were used.

## Queue recovery

Invalid first jobs enter blocked state and the worker proceeds to valid work. States include queued, running, blocked, retryable, failed, uncertain_upload and completed. Only safe simulation timeouts receive automatic retries. Uncertain/running work requires operator reconciliation; retry requires affirmative confirmation that no upload occurred and renewed validation. Structured job_events contain phase, error type, reviewer/outcome and timestamp without raw credential-bearing exception text. Live publication remains disabled.

## Technical QA and limits

Measures: aspect/resolution/codec/duration, full decode, freeze and black intervals, silence, clipped sample ratio, caption time/layout bounds, and source/output audio waveform alignment over the first ten seconds. Actual source-document/hash/destination matching is checked separately. Freeze detection is a heuristic, not a proof that footage is genuine. Waveform alignment is not semantic transcript accuracy. An editor must verify speech, captions, source framing and creative quality. No software check claims entertainment quality.

The text renderer now requires explicit `fixture=True`; its command is `technical-fixture`. Normal production requires source footage and has no navy-background or Flite fallback. Flite itself refuses production calls and no longer pads speech into eight-second WAV segments. Historical artifacts are unchanged.

## Cloud and costs

A single-host container definition is supplied but not built/deployed. The review remains bound to loopback; an approved HTTPS/identity edge is required. Persistent state/media volumes, backups, ownership and secrets need configuration. No public insecure service, paid resource or scheduler was activated. The container definition and runner remain deployment preparation, not verified restart recovery. There is no production publication worker until official authorization and live/private testing are explicitly approved.

Incremental API/hosting charges activated in this task: none. Development compute is unmetered, not claimed free. Per-render wall time is recorded, while compute cost is null without an authorized rate. Future hosting/provider costs need approval and current quotes. Clipping does not depend on Higgsfield or paid narration.

## Validation

`.venv/bin/python scripts/run_checks.py --save-report` runs all preserved tests with explicit fixture opt-ins plus adversarial regressions and local media/ASR tests. The result separates unit/local utility, local media, simulated transport/identity evidence, actual mock dependence, and live integration counts. See reports/phase2-tests.json. No test publishes externally.
