"""Fail-closed rights and approval control plane for Beyond Orbit.

This module intentionally does not download, render, connect accounts, or publish.
It answers the higher-risk question first: may this exact job proceed, and does the
exact output still have the approvals needed for release?
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence
from urllib.parse import urlsplit


TRACKS = {
    "campaign_clip",
    "creator_service",
    "owned_analysis",
    "owned_ai_explainer",
    "kids_animation",
}
RIGHTS_BASES = {"campaign_license", "written_creator_permission", "owned", "licensed"}
PLATFORMS = {"youtube", "instagram", "tiktok"}
HIGH_RISK_SOURCE_TYPES = {"movie", "television", "netflix", "leak", "pirated_copy"}
APPROVAL_KINDS = {"creative", "publish"}


@dataclass(frozen=True)
class GateDecision:
    allowed: bool
    state: str
    blockers: Sequence[str]
    warnings: Sequence[str]

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Approval:
    kind: str
    digest: str
    decision: str
    reviewer: str
    approved_at: str

    def as_dict(self) -> Dict[str, str]:
        return asdict(self)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _https_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlsplit(value)
    return parsed.scheme == "https" and bool(parsed.hostname) and not parsed.username and not parsed.password


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _valid_iso8601(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    return all(character in "0123456789abcdef" for character in value.lower())


def artifact_digest(video_path: Path, metadata: Mapping[str, Any]) -> str:
    """Bind approval to exact video bytes and exact metadata."""
    path = Path(video_path)
    h = hashlib.sha256()
    h.update(path.read_bytes())
    h.update(b"\0metadata\0")
    h.update(_canonical(metadata))
    return h.hexdigest()


def publication_digest(
    artifact_sha256: str,
    destinations: Iterable[str],
    campaign_fingerprint: Optional[str],
) -> str:
    payload = {
        "artifact_sha256": artifact_sha256,
        "destinations": sorted(set(destinations)),
        "campaign_fingerprint": campaign_fingerprint,
    }
    return hashlib.sha256(_canonical(payload)).hexdigest()


def approve(kind: str, digest: str, reviewer: str, at: Optional[str] = None) -> Approval:
    """Create a local audit record; this is not identity authentication."""
    if kind not in APPROVAL_KINDS:
        raise ValueError("approval kind must be creative or publish")
    if not _sha256(digest):
        raise ValueError("approval must bind a SHA-256 digest")
    if not _nonempty(reviewer):
        raise ValueError("reviewer is required")
    timestamp = at or datetime.now(timezone.utc).isoformat()
    if not _valid_iso8601(timestamp):
        raise ValueError("approval timestamp must include a timezone")
    return Approval(kind, digest, "approved", reviewer.strip(), timestamp)


def evaluate_intake(job: Mapping[str, Any]) -> GateDecision:
    """Evaluate whether a proposed source may enter editing.

    Unknown or missing rights block the job. A campaign or cloud file location is
    evidence only when the record also includes the grant and its scope.
    """
    blockers: List[str] = []
    warnings: List[str] = []

    track = job.get("track")
    if track not in TRACKS:
        blockers.append("unknown production track")

    source = job.get("source") if isinstance(job.get("source"), Mapping) else {}
    rights = job.get("rights") if isinstance(job.get("rights"), Mapping) else {}
    destinations = job.get("destinations")

    if not _https_url(source.get("url")):
        blockers.append("direct HTTPS source URL is required")
    if not _nonempty(source.get("owner")):
        blockers.append("source owner is required")
    source_type = source.get("type")
    if not _nonempty(source_type):
        blockers.append("source type is required")
    if source_type in HIGH_RISK_SOURCE_TYPES:
        if rights.get("basis") != "campaign_license" or rights.get("campaign_supplied") is not True:
            blockers.append("movie/TV/leaked material requires a campaign-supplied commercial license")

    if source.get("storage") == "google_drive":
        warnings.append("Google Drive possession is not evidence of copyright permission")

    if rights.get("basis") not in RIGHTS_BASES:
        blockers.append("recognized rights basis is required")
    if rights.get("commercial_use") is not True:
        blockers.append("commercial-use permission is required")
    if not _https_url(rights.get("evidence_url")):
        blockers.append("rights evidence must have a direct HTTPS URL")
    if not _nonempty(rights.get("scope")):
        blockers.append("rights scope is required")
    if not _valid_iso8601(rights.get("checked_at")):
        blockers.append("rights verification timestamp with timezone is required")
    if rights.get("expires_at") is not None:
        if not _valid_iso8601(rights.get("expires_at")):
            blockers.append("rights expiry must include a timezone")
        elif datetime.fromisoformat(rights["expires_at"].replace("Z", "+00:00")) <= datetime.now(timezone.utc):
            blockers.append("rights grant has expired")

    if not isinstance(destinations, list) or not destinations:
        blockers.append("at least one destination is required")
    elif any(p not in PLATFORMS for p in destinations):
        blockers.append("unsupported destination platform")

    audio = job.get("audio") if isinstance(job.get("audio"), Mapping) else {}
    if audio.get("basis") not in {"none", "owned", "licensed", "platform_library", "campaign_license"}:
        blockers.append("audio rights basis is required")
    if audio.get("basis") not in {"none", "platform_library"} and not _https_url(audio.get("evidence_url")):
        blockers.append("audio rights evidence URL is required")

    if track == "campaign_clip":
        campaign = job.get("campaign") if isinstance(job.get("campaign"), Mapping) else {}
        for field in ("id",):
            if not _nonempty(campaign.get(field)):
                blockers.append("campaign %s is required" % field)
        if not _sha256(campaign.get("brief_fingerprint")):
            blockers.append("campaign brief_fingerprint must be a SHA-256 digest")
        if not _valid_iso8601(campaign.get("submission_deadline")):
            blockers.append("campaign submission_deadline must include a timezone")
        elif datetime.fromisoformat(campaign["submission_deadline"].replace("Z", "+00:00")) <= datetime.now(timezone.utc):
            blockers.append("campaign submission deadline has passed")
        if not _https_url(campaign.get("brief_url")):
            blockers.append("direct campaign brief URL is required")
        if rights.get("basis") != "campaign_license":
            blockers.append("campaign clips must use campaign-license rights")
        if rights.get("campaign_supplied") is not True:
            blockers.append("campaign footage must be explicitly supplied or named by the campaign")

    if track == "creator_service" and rights.get("basis") != "written_creator_permission":
        blockers.append("creator service requires written creator permission")

    if track in {"owned_analysis", "owned_ai_explainer", "kids_animation"}:
        if rights.get("basis") not in {"owned", "licensed"}:
            blockers.append("owned-content tracks require owned or licensed assets")
        if job.get("reference_video_mode") not in {None, "analysis_only"}:
            blockers.append("reference videos may guide analysis only, not be copied")

    if track == "kids_animation":
        kids = job.get("kids") if isinstance(job.get("kids"), Mapping) else {}
        if kids.get("made_for_kids_review") is not True:
            blockers.append("kids content requires made-for-kids/COPPA review")
        if kids.get("separate_channel") is not True:
            blockers.append("kids content requires a separate channel strategy")
        warnings.append("kids animation is a later pilot, not tonight's launch track")

    disclosures = job.get("disclosures")
    if track == "campaign_clip" and (not isinstance(disclosures, list) or not disclosures):
        blockers.append("campaign disclosures are required")

    return GateDecision(not blockers, "EDIT_ALLOWED" if not blockers else "BLOCKED", tuple(blockers), tuple(warnings))


def _has_exact_approval(approvals: Sequence[Approval], kind: str, digest: str) -> bool:
    return any(a.kind == kind and a.digest == digest and a.decision == "approved" for a in approvals)


def publication_gate(
    intake: Mapping[str, Any],
    video_path: Path,
    metadata: Mapping[str, Any],
    approvals: Sequence[Approval],
) -> GateDecision:
    """Require rights plus two exact-version approvals before any live adapter."""
    intake_result = evaluate_intake(intake)
    blockers = list(intake_result.blockers)
    warnings = list(intake_result.warnings)
    if blockers:
        return GateDecision(False, "BLOCKED", tuple(blockers), tuple(warnings))

    artifact_sha = artifact_digest(Path(video_path), metadata)
    campaign = intake.get("campaign") if isinstance(intake.get("campaign"), Mapping) else {}
    release_sha = publication_digest(
        artifact_sha,
        intake.get("destinations", []),
        campaign.get("brief_fingerprint"),
    )
    if not _has_exact_approval(approvals, "creative", artifact_sha):
        blockers.append("exact video and metadata need creative approval")
    if not _has_exact_approval(approvals, "publish", release_sha):
        blockers.append("exact artifact, destinations and campaign terms need publish approval")
    return GateDecision(not blockers, "READY_FOR_LIVE_ADAPTER" if not blockers else "AWAITING_APPROVAL", tuple(blockers), tuple(warnings))


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Beyond Orbit fail-closed control plane")
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate-intake")
    validate.add_argument("job")
    args = parser.parse_args(argv)

    if args.command == "validate-intake":
        result = evaluate_intake(load_json(Path(args.job)))
        print(json.dumps(result.as_dict(), indent=2))
        return 0 if result.allowed else 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
