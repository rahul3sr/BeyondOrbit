# Implemented architecture

The existing first-party renderer remains the foundation. Python standard-library services and system FFmpeg/Flite run locally; no new paid services or pip dependencies were installed.

Campaign import → schema/evidence validation → SQLite deduplication and material revisions → account eligibility gate → explicit scenario assumptions and contribution ranking → authorized local source ingestion → supplied transcript segment ranking → vertical FFmpeg clipping/captions → QC and rights attestation → SHA-256 manifest → individual authenticated review → mock-only queued upload → ledger and operating dashboard.

Original content: authored original topic/script → scene plan → procedural geometry → optional Flite narration per scene → captions → metadata → QC → the same review system. Topic research and factual verification remain human/LLM-assisted; this milestone's script offers creative-process suggestions and contains no external factual claims. There is no unattended LLM orchestration service.

SQLite transactions protect campaign revisions, decisions and job claims. A unique video-plus-metadata upload key prevents duplicate mock uploads even when an artifact is registered twice. Workers recheck the latest decision, version and campaign fingerprint immediately before the mock side effect. Filesystem mutation by another local process cannot be made fully atomic with SQLite; this is one reason live publishing remains disabled. Running/uncertain jobs are never automatically reclaimed. Safe mock timeouts have bounded retry delays; permission, integrity and terms changes fail closed.

Manifest binding includes video, SRT, ASS, metadata, spec, QC report and optional context/transcript. Changing terms invalidates campaign approvals. Monetary estimates are separate from verified-evidence imports for accrued earnings and received cash. Metrics start unavailable; forecasts cannot enter the financial ledger. Verification labels on manual imports are the importer's attestations, not proof of external verification by this application.

Five roles are enforced server-side. Minors may participate under supervision; they cannot approve publication. There is no shared Google password. The review application is loopback-only with individual random credentials, HttpOnly SameSite cookies, session expiry, CSRF checks, Host/Origin checks and escaped display text. It is a development service, not an Internet-ready identity platform. No browser session has been created for the owner.

## Cloud decision

GitHub remains the code source of truth. Actions is the preferred first batch runtime, but free quota and spending limits are not known. A manual, disabled-by-default verification workflow is committed; no run was dispatched and no scheduler has been deployed. A single-host systemd timer template plus SQLite is provided for an approved always-on host. Neither systemd nor a paid host was installed. n8n Cloud and managed serverless/storage are deferred because they add cost and credentials before live source access is available.

Persistent state and large media must not be normal Git history. A production deployment needs approved persistent storage, authenticated HTTPS review, backups and an identity-backed approval service before live uploads. No cost or uptime guarantee is implied by local validation.
