# Add campaign-to-video workflow and authenticated review

Beyond Orbit's initial renderer could only produce a silent text video. This change reuses it to deliver a narrated original-content pipeline and a campaign clip pipeline with evidence-labelled imports, account eligibility, scenario contribution ranking, supplied-transcript segment selection, 9:16 clipping and caption generation. The end-to-end fixture demonstration stops awaiting real human review.

Adds a SQLite operating database, terms revisions, a loopback review interface with individual credentials/roles/CSRF, exact-version decisions, duplicate-protected mock jobs and verified-evidence financial/metric imports. Official YouTube OAuth PKCE, resumable private-upload and analytics protocols are exercised through mock transports only. Instagram/TikTok and Higgsfield remain mocks; no account is connected. All six audited YouTube utilities are pinned, attributed and fixture-tested without running installation scripts.

Validation: 49 tests passed, including narrated rendering and full decode, synthetic campaign clipping, eligibility/finance calculations, role and CSRF checks, exact-version/changed-terms invalidation, duplicate prevention, retry gating and mocked official protocols. Focused credential-pattern scanning, vendor hashes and Git whitespace checks passed. No live integration or hosted runtime is claimed.

Manual-only Actions verification remains gated off pending billing authorization. Daily timer templates are inactive; no schedule, paid service, external notification or public upload was activated. Marketplace sources and api.github.com remain proxy-denied. Generated videos/SQLite state stay outside Git. See reports/status.json, reports/test-results.txt and docs/operating-guide.md for details.
