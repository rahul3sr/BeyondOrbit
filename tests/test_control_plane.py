import json
from pathlib import Path
import tempfile
import unittest

from beyond_orbit.control_plane import (
    approve,
    artifact_digest,
    evaluate_intake,
    publication_digest,
    publication_gate,
)


def owned_job():
    return {
        "job_id": "bo-original-001",
        "track": "owned_ai_explainer",
        "source": {
            "url": "https://beyond-orbit.example/assets/original-script-001",
            "owner": "Beyond Orbit",
            "type": "original_script",
            "storage": "local",
        },
        "rights": {
            "basis": "owned",
            "commercial_use": True,
            "campaign_supplied": False,
            "evidence_url": "https://beyond-orbit.example/rights/original-001",
            "scope": "All Beyond Orbit social accounts",
            "checked_at": "2026-11-17T19:00:00-06:00",
        },
        "audio": {"basis": "none"},
        "destinations": ["youtube", "instagram", "tiktok"],
        "reference_video_mode": "analysis_only",
        "disclosures": [],
    }


class IntakeTests(unittest.TestCase):
    def test_owned_original_allowed_to_edit(self):
        result = evaluate_intake(owned_job())
        self.assertTrue(result.allowed, result.blockers)
        self.assertEqual(result.state, "EDIT_ALLOWED")

    def test_google_drive_is_not_rights(self):
        job = owned_job()
        job["source"]["storage"] = "google_drive"
        job["rights"] = {}
        result = evaluate_intake(job)
        self.assertFalse(result.allowed)
        self.assertIn("Google Drive possession is not evidence of copyright permission", result.warnings)

    def test_netflix_copy_blocked_without_campaign_license(self):
        job = owned_job()
        job["track"] = "campaign_clip"
        job["source"]["type"] = "netflix"
        job["rights"]["basis"] = "owned"
        result = evaluate_intake(job)
        self.assertFalse(result.allowed)
        self.assertTrue(any("movie/TV/leaked" in x for x in result.blockers))

    def test_creator_service_needs_written_permission(self):
        job = owned_job()
        job["track"] = "creator_service"
        self.assertFalse(evaluate_intake(job).allowed)
        job["rights"]["basis"] = "written_creator_permission"
        self.assertTrue(evaluate_intake(job).allowed)

    def test_campaign_needs_exact_brief_and_disclosure(self):
        job = owned_job()
        job["track"] = "campaign_clip"
        job["rights"].update(basis="campaign_license", campaign_supplied=True)
        result = evaluate_intake(job)
        self.assertFalse(result.allowed)
        job["campaign"] = {
            "id": "campaign-123",
            "brief_url": "https://contentrewards.example/campaign-123",
            "brief_fingerprint": "a" * 64,
            "submission_deadline": "2026-11-20T23:59:00-06:00",
        }
        job["disclosures"] = ["#ad"]
        self.assertTrue(evaluate_intake(job).allowed)

    def test_expired_rights_are_blocked(self):
        job = owned_job()
        job["rights"]["expires_at"] = "2025-01-01T00:00:00+00:00"
        self.assertIn("rights grant has expired", evaluate_intake(job).blockers)

    def test_campaign_fingerprint_is_exact_hash(self):
        job = owned_job()
        job["track"] = "campaign_clip"
        job["rights"].update(basis="campaign_license", campaign_supplied=True)
        job["campaign"] = {
            "id": "campaign-123",
            "brief_url": "https://contentrewards.example/campaign-123",
            "brief_fingerprint": "not-a-hash",
            "submission_deadline": "2026-11-20T23:59:00-06:00",
        }
        job["disclosures"] = ["#ad"]
        self.assertFalse(evaluate_intake(job).allowed)

    def test_kids_track_is_separate_and_reviewed(self):
        job = owned_job()
        job["track"] = "kids_animation"
        self.assertFalse(evaluate_intake(job).allowed)
        job["kids"] = {"made_for_kids_review": True, "separate_channel": True}
        result = evaluate_intake(job)
        self.assertTrue(result.allowed)
        self.assertIn("kids animation is a later pilot, not tonight's launch track", result.warnings)


class ApprovalTests(unittest.TestCase):
    def test_two_exact_approvals_required(self):
        job = owned_job()
        metadata = {"title": "Original explainer", "destinations": job["destinations"]}
        with tempfile.TemporaryDirectory() as temp:
            video = Path(temp) / "video.mp4"
            video.write_bytes(b"test-video-v1")
            artifact_sha = artifact_digest(video, metadata)
            release_sha = publication_digest(artifact_sha, job["destinations"], None)

            self.assertEqual(publication_gate(job, video, metadata, []).state, "AWAITING_APPROVAL")
            creative = approve("creative", artifact_sha, "Master", "2026-11-17T19:30:00-06:00")
            self.assertFalse(publication_gate(job, video, metadata, [creative]).allowed)
            publish = approve("publish", release_sha, "Master", "2026-11-17T19:31:00-06:00")
            self.assertTrue(publication_gate(job, video, metadata, [creative, publish]).allowed)

            metadata["title"] = "Changed after approval"
            self.assertFalse(publication_gate(job, video, metadata, [creative, publish]).allowed)

    def test_changed_video_invalidates_approval(self):
        job = owned_job()
        metadata = {"title": "Original explainer"}
        with tempfile.TemporaryDirectory() as temp:
            video = Path(temp) / "video.mp4"
            video.write_bytes(b"v1")
            creative = approve("creative", artifact_digest(video, metadata), "Master")
            video.write_bytes(b"v2")
            self.assertFalse(publication_gate(job, video, metadata, [creative]).allowed)


if __name__ == "__main__":
    unittest.main()
