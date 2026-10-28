> Historical milestone-1 notes. Current implementation and limitations are in [architecture](architecture.md), [operating guide](operating-guide.md), and [status](../reports/status.json). Repository access through Git was later verified by a successful push; the API remains blocked.

# Runtime and integration decisions

Development works in Codex Cloud using Python 3.12 and system FFmpeg with libass. No pip packages or third-party skills were installed. Existing checkout is retained; no worktree is needed.

## Simplest next permanent runtime

Prefer GitHub Actions for short batch experiments after private repository access and billing limits are confirmed. Actions runs independently of a laptop, supports protected environments and encrypted secrets, but runners are temporary: durable manifests, jobs and an upload ledger must live outside a runner or in a persistent store before automated publishing. Do not cache tokens in artifacts. Uploaded video artifacts need short retention and controlled access.

n8n Cloud adds a subscription and is unnecessary for this first batch renderer. Managed serverless containers can support longer jobs and durable queues but add IAM, storage and operational complexity. Neither has been provisioned. No schedule, hosting resource or billing feature has been activated.

A future workflow should run tests → render → retain private review artifact. Publishing must be a separate authenticated job with exact-version approval and protected access. Durable unique upload claims and reconciliation are required before retries; YouTube upload requests are not assumed idempotent. Use bounded exponential backoff only for safe reads; reconcile uncertain upload outcomes rather than blindly retrying. Current renderer fails explicitly, preserves partial output for diagnosis and refuses to overwrite a run directory.

## Official APIs

YouTube discovery adapter uses official Data API v3 search, but no live API request has been authorized or tested. It needs API access and network permission for www.googleapis.com. Search quota costs apply, so do not schedule broad discovery until quota is reviewed.

Uploads require the official Google OAuth consent flow with youtube.upload scope and a private default. Analytics needs separate least-privilege authorization such as yt-analytics.readonly. No OAuth flow or upload implementation is enabled yet. Inspect official current documentation and complete consent configuration before requesting authorization; never request passwords or tokens in chat. Account-specific upload restrictions may apply to unverified API projects.

Higgsfield subscription entitlement, official API endpoints, supported authentication, pricing and commercial output rights remain unverified. A consumer subscription does not prove API access. Do not use browser automation or undocumented endpoints to bypass API restrictions. No Higgsfield request was made and no paid generation was started.

## GitHub repository verification

The user confirmed `rahul3sr/BeyondOrbit` as the intended repository. Retain the existing checkout at `/workspace/BeyondOrbit`; do not create a duplicate named `beyond-orbit`.

Origin fetch URL: `https://github.com/rahul3sr/BeyondOrbit.git`. A read-only `git ls-remote --symref origin HEAD` succeeded through the existing platform authentication. Remote default branch is `last-30-days`; remote HEAD was `54e2d142bff68230439ad1046afe46c2d9780328`, matching the checkout's initial commit. This proves repository identity and Git read access, not privacy or write access.

GH_TOKEN is present (value not inspected). The GitHub API request fails at the proxy CONNECT step with HTTP 403; the current restricted network preset includes github.com but does not include api.github.com. No conclusion about token validity or scope can be drawn before that network barrier is removed.

The environment draft now adds only `api.github.com` to custom allowed domains and preserves package-manager presets. Saving the draft did not apply it: an immediate retry still returned Forbidden. In Codex environment settings, review and save the allowed-domain change, then publish the environment as requested by the configuration tool. Reconnect/restart if needed for the policy to take effect. Afterwards retry:

```bash
cd /workspace/BeyondOrbit
gh api repos/rahul3sr/BeyondOrbit --jq '{full_name,private,default_branch,permissions}'
```

Require `private: true` before pushing project work. If the request then reaches GitHub but reports 401, 403, or an authenticated 404, review the Codex GitHub connection's repository access for `rahul3sr/BeyondOrbit`. GitHub's installed Codex/OpenAI application must include that repository. A PR also requires repository Contents write and Pull requests write permissions under the connection's supported authorization flow. Do not create or paste a personal token to work around a network denial.

No remote branch push or pull request has succeeded or been attempted during this verification milestone. Work is committed locally with review notes; this is not a GitHub save. The draft domain change is not a new GitHub account permission grant.
