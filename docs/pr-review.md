# Review draft: Add approval-gated offline video-production prototype

Beyond Orbit previously contained only a README. This change adds a runnable first-party Python workflow that turns an original script into a silent 36-second vertical text video, generates captions and metadata, records rights evidence and QC results, and binds all review inputs to a SHA-256 manifest. Public and private uploads are disabled.

The implementation requires Python and system FFmpeg/ffprobe with libx264 and libass. It uses no pip dependencies or copied third-party skill code. Local approval validation checks version binding; it is not an authenticated approval service. Rights evidence is an attestation requiring human review, not automated legal verification.

Validation: `python3 -m unittest discover -s tests -v` — 8 tests passed, including actual rendering and full decode, missing/unsupported rights rejection, exact-version/destination approval invalidation, and disabled publishing. `git diff --cached --check` passed. Generated videos stay outside Git.

Includes a pinned static review of the requested YouTube Agent Skill framework. No third-party utilities were executed or installed. Narration, long-form clipping, OAuth publishing, live analytics, Higgsfield and permanent scheduling remain incomplete.

Repository: rahul3sr/BeyondOrbit. Intended PR base: last-30-days (verified remote HEAD branch). This file is a local PR description draft; no GitHub PR has been created. Apply the saved api.github.com network addition and confirm private visibility and write permission before pushing a review branch.
