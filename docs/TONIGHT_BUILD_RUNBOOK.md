# Tonight’s Build and Launch Runbook

## Goal

Finish a controlled first system tonight and prepare one private/unlisted original test across YouTube, Instagram, and TikTok. Do not treat account creation, OAuth, API-key creation, or posting as already completed.

## Build 1 — completed

- [x] Create fail-closed rights intake.
- [x] Separate campaign, creator-service, owned analysis, owned explainer, and kids tracks.
- [x] Block Google-Drive/Netflix scenario without explicit commercial campaign rights.
- [x] Bind creative approval to video bytes + metadata.
- [x] Bind publish approval to artifact + destinations + campaign fingerprint.
- [x] Add eight automated tests.
- [x] Keep live publishing disabled.

Verification:

```bash
python3 -m unittest discover -s tests -v
python3 -m beyond_orbit.control_plane validate-intake examples/intake_owned_original.json
python3 -m beyond_orbit.control_plane validate-intake examples/intake_blocked_tv.json
```

## Live setup sequence

### 1. Campaign due diligence

Open Content Rewards and Vyro. For each live GTA campaign, record the joined brief in the intake schema. Rank by expected contribution and operational fit. Approve at most two campaigns tonight.

Stop if the brief does not explicitly identify footage or provide a commercial-use basis.

### 2. Account architecture

Reserve consistent handles for:

- GTA/campaign clipping;
- original Beyond Orbit explainers.

Use separate identities. Configure 2FA and recovery ownership. Account creation final submits and authentication codes remain human steps.

### 3. Scheduling layer

Create one Metricool brand for the campaign identity. Connect Instagram, TikTok, and YouTube through official OAuth and the minimum scopes. Do not grant posting access until the account and scope screen is reviewed.

### 4. AI credentials

Create only a Gemini development key first. Use a dedicated Google project, the narrow Gemini service, a small quota/budget, and an ignored local secret.

Create OpenAI/Anthropic development keys later only when the benchmark defines a separate job they will perform. Three keys are not a success metric.

### 5. Production engines

1. Install PeakCut in an isolated persistent folder after pinning the reviewed commit.
2. Test with NASA or owned footage.
3. Connect Gemini through local environment configuration.
4. Produce 3–5 candidates.
5. Connect OpusClip via OAuth only for a same-source benchmark.
6. Score quality, human rework minutes, render time, and cost.

### 6. Owned explainer

Connect Everygen through the verified `everygen.ai` OAuth connector. Create one original 60–90 second explainer from an independently researched idea. Do not ask it to recreate a competitor’s exact video.

### 7. Private/unlisted distribution test

Use the original/NASA benchmark, not GTA streamer footage. Create platform-specific metadata and verify crop, captions, audio, and disclosure. Obtain creative approval, then publish approval. Use private/unlisted/draft modes where supported; where a platform lacks private test posting, stop at the final publish screen.

### 8. Launch-day gate

On November 19, ingest only the campaign-named VODs after release. Generate candidates, approve a small batch, publish, submit within the brief deadline, and record links/IDs immediately.

## What success tonight means

- one tested control plane;
- one or two approved campaign briefs captured;
- account identities reserved and secured;
- one AI provider configured safely;
- one owned test asset staged across three platforms;
- no credentials in Git;
- no unlicensed GTA/Netflix/TV post;
- no claim that platform monetization is guaranteed.
