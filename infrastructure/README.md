# Cloud execution status

No paid resources, hosted review server, notifications or continuously running scheduler have been deployed.

`.github/workflows/verify.yml` is manual-only and job-gated on `BEYOND_ORBIT_CI_AUTHORIZED == true`. The repository variable has NOT been set and no workflow has been dispatched. Enabling it requires owner confirmation of free allowance/spending limits. The workflow pins checkout, installs system media tools, then runs the same security and test commands verified locally. Hosted execution is unverified.

`templates/beyond-orbit-daily.service` and `.timer` are inactive deployment examples for a future approved Linux host with persistent `/var/lib/beyond-orbit`, a dedicated service user and an existing checkout at `/srv/beyond-orbit`. They run authorized imports daily at 14:00 UTC plus randomized delay; no timezone-sensitive business posting time is inferred. They have not been installed, enabled or tested on a permanent host.

SQLite and media must be backed up together to approved durable storage. The authenticated development review service is loopback-only. Do not expose it directly on the Internet. No autonomous publication is enabled by these files.

Current incremental external API spend: $0. Current compute cost: unmetered within the existing Codex environment. Monthly hosted costs are unknown because no plan or billing allowance has been authorized; $0 hosting is not promised. n8n, managed queues, storage and serverless resources are deferred.
