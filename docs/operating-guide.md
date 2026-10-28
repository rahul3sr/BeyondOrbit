# Development operations

From the existing `/workspace/BeyondOrbit` checkout:

```bash
python3 -m unittest discover -s tests -v
python3 scripts/security_check.py
python3 -m beyond_orbit.operations demo --out artifacts/NEW_RUN_NAME
python3 -m beyond_orbit.operations status --db artifacts/NEW_RUN_NAME/operations.sqlite
python3 -m beyond_orbit.operations health --db artifacts/NEW_RUN_NAME/operations.sqlite
```

The full demo produces both narrated original content and an authorized synthetic campaign clip, then stops pending real human review. It never invents an approval. Tests use synthetic reviewer identities in temporary databases only.

## Authorized campaign import and scheduled discovery

`python3 -m beyond_orbit.operations import --db state/operations.sqlite path/to/campaign.json`

Every field is listed in `beyond_orbit.campaigns.FIELDS`; each contains `value`, `status` (verified/unconfirmed/unavailable), `source_url`, and `checked_at` with timezone. Missing fields must be explicitly unavailable with null. The generated `campaign-fixture.json` illustrates the schema; it is NOT a real opportunity. Use direct campaign-owner terms and a recent checked timestamp. Freshness expires after 24 hours for eligibility. Do not upgrade directory listings or unsupported claims to verified. Shared budgets may change between checks.

Import an inbox once per day with `python3 -m beyond_orbit.operations daily --db state/operations.sqlite --inbox state/inbox`. It deduplicates and records material changes without notifications. A failed import releases the daily claim for idempotent retry; a crashed running daily claim needs operator reconciliation. The daily command works, but no cloud scheduler is active. Keep the existing ChatGPT campaign-finding agent unchanged.

Rank real, eligible imports with `python3 -m beyond_orbit.operations rank --db state/operations.sqlite --account account.json --assumptions assumptions.json`. Account contains followers/country/platform. Assumptions map campaign IDs to downside/base/best inputs: views, qualifying_fraction, audience_relevance, approval_probability, production_cost, minutes, hourly_cost. Financial terms must be verified USD per-1000 qualifying views. Fees, payout caps and remaining budgets constrain gross forecasts; payout thresholds affect collectible estimates. Importer eligibility attestation and human review of all terms remain necessary.

## Review and family access

The tested local interface uses `python3 -m beyond_orbit.operations serve --db PATH --port 8765`. Configure `BEYOND_ORBIT_USERS` through secure runtime configuration: an array of individual objects with id, role, credential and optional minor boolean. Each credential must be a unique random string of at least 24 characters. Do not put this value in Git, logs or chat. Roles: OWNER, CREATOR, EDITOR, APPROVER, ANALYST. Minors cannot approve. No credentials are provisioned automatically and no shared account is needed.

The UI previews media, metadata, rights, terms context, costs and target destinations. APPROVE/REJECT/REQUEST CHANGES are version-bound decisions; APPROVE records a decision but never uploads. User-controlled HTML is displayed as text. The service is loopback-only and has no user-facing cloud URL. Remote review requires an approved authenticated HTTPS deployment; do not expose this development server directly.

## Reporting

Use `operations evidence --db PATH FILE.json` for verified actual entries. Each record requires a unique evidence_id, status verified, fixture false, checked_at and direct HTTPS source. Financial types distinguish accrued_revenue, cash_received, platform_fee, production_expense, external_api_expense and infrastructure_expense in USD. Metric imports name platform, video, metric and value. Fixtures cannot be imported as actual financial or performance data. Manual attestations must be reviewed against their sources.

## Integration and security limits

Official Google OAuth PKCE/state and YouTube resumable-private-upload/analytics protocols are mock-tested. No default network transport or OAuth login is wired. Instagram/TikTok and Higgsfield are mocks. The optional local faster-whisper adapter requires a separately reviewed installed package and approved local model; neither is installed. Timed transcripts are the working fallback. Do not call it tested automatic transcription.

The focused scanner checks selected credential signatures and vendored hashes; it is not an exhaustive secret scanner or vulnerability audit. System FFmpeg, Flite and Python are platform-provided. Check their supported security updates before a production deployment.

The previous environment snapshot publication stalled. No new publication attempt is part of this milestone. Git over github.com works independently. ContentRewards, Vyro and api.github.com are proxy-denied. Do not disable TLS, bypass authentication or scrape around access controls. Apply approved destination access via supported network controls or use authorized imports. Never recreate the repository to fix network access.
