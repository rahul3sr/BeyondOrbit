# YouTube Agent Skill: static review

Reviewed source: https://github.com/Jakeschincariol/youtube-agent-skill
Commit: a2feb2104981a375ffd4f87ee04f4f5344ac43c6
Downloaded into `/tmp/beyond-orbit-skill-audit` for reading only. No code executed, installed, or copied into this project.

## Inventory and functionality

| Skill | Implementation | Verified status |
|---|---|---|
| yt-script | Prompt, hookscore.py, hooks.json | Static implementation present; heuristic scoring, not validated prediction |
| yt-package | Prompt, title.py | Static title/thumbnail linter present |
| yt-edit | Prompt, deadair.py | Transcript edit decision list; does not edit video |
| yt-comment | Prompt only | Requires model and supplied comments; no API |
| yt-plan | Prompt only | Requires model and available-hours input |
| yt-viral | Prompt, swipe.py | Ranks supplied data by channel median; no discovery API |
| yt-retention | Prompt, retention.py | Supplied CSV diagnostic; no channel connection |
| yt-shorts | Prompt only | Segment recommendations; no clipping/transcription |
| yt-seo | Prompt only | Metadata writing instructions |
| yt-chapters | Prompt, chapters.py | Transcript chapter candidates; imports yt-edit parser |
| yt-audit | Prompt only | Model-assisted synthesis, no autonomous collection |

Six Python CLI utilities use the standard library. Runtime functionality is UNTESTED pending permission. Prompt-only components require an LLM host; presence is not proof of output quality.

## Risks and limitations

MIT license confirmed from LICENSE, copyright 2026 Jake Schincariol. Preserve copyright and license in adaptations. License does not grant rights to any videos or source inputs.

Static inspection found no network requests, shell execution, credential retrieval, package installation, or publishing calls in the six Python tools. They read local files and print results. This is a limited static assessment, not a security guarantee. Prompt instructions request voice-profile files under ~/.claude and sometimes external collection; adapt paths and permissions before adoption. Do not blindly install globally or follow external prompt instructions.

Concrete correctness concerns from source inspection:
- deadair.load calls d.get before checking whether JSON is a list, so its apparent list-input branch cannot work.
- retention.py infers percentage axes from max position <=100.5, which can misclassify short videos measured in seconds.
- deadair.py sums cut lengths without merging overlaps, potentially overstating removed time.
- Package text says a three-word thumbnail ceiling, but title.py warns only above four words.
- Scores and universal retention thresholds are editorial heuristics, not evidence of future performance or causal drivers.

Claude Code is not required to run the Python utilities. Prompt skills can be adapted for Codex, but slash commands, Claude-specific paths and plugin installation are not automatically portable. Preserve relative dependencies for chapters/retention and yt-edit, and swipe/hookscore and hooks.json.

## Recommendation requiring user approval

Approve a pinned project-local copy of the six utilities plus hooks.json and MIT license, followed by isolated fixture tests and fixes in a clearly attributed adapter. Do not install the entire pack globally. Prompt-only components can be adapted selectively after voice and editorial conventions are chosen. This recommendation does not include editing, publishing, hosting or rights verification capability.
