---
name: skill-maintenance
description: "Automated skill maintenance tool (v6 — Unified Registry + Snapshots). Full scan: [Orphan] migrate misplaced skills from category dirs OR standalone skills/&lt;name&gt;/ to auto-generated/, [Sync] auto-generated/ vs registry lifecycle diff (new/deleted/revived + description auto-sync via lifecycle field), [Reg] user-created/ registry consistency (add/remove, no content changes), [Check] validation warnings + multi-dimensional merge detection, [Snapshot] timestamped registry archive to .history/. All lifecycle tracking merged into user_capabilities.json — single source of truth."
version: 6.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [maintenance, skills, cleanup, audit, registry]
    related_skills: [multi-deliverable-project, user-memory-system]
---

# Skill Maintenance Tool v6 — Unified Registry

## Directory Structure

```
~/.hermes/
├── SOUL.md                      ← Governance rules (edit Section 1)
├── skills/
│   ├── auto-generated/          ← Agent self-generated skills
│   │   └── <skill-name>/
│   ├── user-created/            ← User-created skills
│   │   ├── skill-maintenance/   ← scripts/maintain.py lives here
│   │   └── <skill-name>/
│   └── <category>/              ← Bundled skills
├── user-memory/                 ← Auto-populated by agent
└── user-registry/
    ├── user_capabilities.json   ← SINGLE registry (routing + lifecycle tracking via lifecycle field)
    └── capability_finder.py     ← Trigger matcher
```

Framework template (`framework/`) is a self-contained copyable package.
See main README for per-directory deployment commands.
skill-maintenance is INCLUDED inside `framework/skills/user-created/skill-maintenance/`.
No separate install step needed.

## Execution Flow ([Orphan] → [Sync] → [Reg] → [Check] → [Snapshot])

The script runs four parts in strict sequence. [Orphan] MUST run first so newly
relocated skills are present in `auto-generated/` before [Sync] scans it.

### Step 0: Bootstrap (Run Before Parts)

Before any scan step runs, the script ensures all required infrastructure exists:

1. **Load registry** (`user_capabilities.json`):
   - File missing → create with empty `capabilities: []`
   - Print "Created new registry: user_capabilities.json"
   - Backup existing file to `.backup/`

2. **Create directories if missing**:
   - `auto-generated/` missing → `os.makedirs()`, print "Created directory: auto-generated/"
   - `user-created/` missing → `os.makedirs()`, print "Created directory: user-created/"

### [Orphan] Misplaced Skills Auto-Migration (SOUL.md Enforcement)

Scans category directories under `skills/` for skills that landed in the wrong place.
Detects two types:
1. **Sub-skills** inside a category dir (e.g. `creative/my-skill/`)
2. **Standalone skills** directly at `skills/<name>/` with their own SKILL.md (e.g.
   agent-created skills that bypassed auto-generated/ or user-created/)

Moves non-bundled skills to `auto-generated/` and registers them in the capability registry
with lifecycle fields — all in one pass.

What to look for in output:
- `✓ X: <dir>/ → auto-generated/` — skill was relocated
- `→ Registered X → user_capabilities.json` — new registry entry created
- `→ Registry updated: X` — existing entry updated with new path
- `! X: target auto-generated/X already exists` — conflict, needs manual merge
- `No misplaced skills found` — everything where it should be (idempotent)

**Verification:** Run the script again. If [Orphan] reports "No misplaced skills found",
the migration is complete and idempotent.

### [Sync] Auto-generated Lifecycle Sync (Registry-based)

Compares `auto-generated/` directory against registry's `lifecycle` fields and syncs them:

- **New skill** — disk has auto-generated skill that's not in registry → auto-fix SKILL.md format, add entry with lifecycle: {type: auto-generated, status: active}
- **Deleted skill** — registry lifecycle says active but disk removed → set lifecycle.status=deleted
- **Revived skill** — lifecycle says deleted but disk reappears → restore lifecycle.status=active
- **Description auto-sync** — reads each active skill's `description` from SKILL.md frontmatter and propagates to registry. Edit a skill's SKILL.md description and it syncs on the next scan.

What to look for in output:
- `+ Added to registry: X` — new skill registered with lifecycle
- `- Marked deleted: X` — lifecycle.status set to deleted
- `↺ Revived: X` — lifecycle.status restored to active
- `~ Registry description sync: X` — description propagated to registry
- `No changes` — disk is consistent with registry

### [Reg] User-created Registry Check

Scans `user-created/` and checks registry consistency only:
- Disk has skill but registry does not → add to registry (category=user-created)
- Registry has skill but disk does not → remove from registry
- **Does NOT modify any skill content or SKILL.md format**

### [Check] Validation Warnings + Merge Detection

After all operations, runs checks in order:

1. **Registry entry validation** (all skills) — checks for empty triggers (skill unreachable by capability_finder) and broken script paths
2. **SKILL.md format validation** (auto-generated/ only) — fixes missing frontmatter, name, description, or H1 heading. Auto-fixed skills need another run to register.
3. **Merge candidate detection** (auto-generated/ only):
   - Compare every active auto-generated skill pairwise
   - Multi-dimensional scoring across name, content, structure, cross-refs, and file layout
   - Report pairs with score >= 0.30 and evidence from at least 2 dimensions:
     → `! skill-A <-> skill-B (score=0.8, axes=[...], evidence details)`
   - Higher score + more evidence axes = more reliable recommendation
   - Deleted skills are excluded from merge detection
   - **Always review candidates manually before merging** — the scoring is heuristic

### [Snapshot] Registry Snapshot (Post-Run Archive)

After all four phases complete, saves a timestamped copy of `user_capabilities.json` to `.history/`:

- **Snapshot file**: `.history/snapshot_{YYYYMMDD_HHMMSS}.json`
- **Purpose**: provides a timeline of registry state changes across runs, useful for rollback reference and change auditing
- **Created by**: `save_json(snapshot_path, registry)` after the registry write

Output:
- `Snapshot: ~/.hermes/skills/user-created/skill-maintenance/.history/snapshot_20260515_091410.json`

## Portability (Self-Bootstrapping)

The script is designed to run on a fresh `~/.hermes/` with zero pre-configuration.

| Missing item | What happens |
|---|---|
| `user_capabilities.json` | Created with empty `capabilities: []` (version 2.0) |
| `user-registry/` directory | Created via `os.makedirs` (by save_json) |
| `auto-generated/` directory | Created, prints "Created directory: auto-generated/" |
| `user-created/` directory | Created, prints "Created directory: user-created/" |
| `.history/` directory | Created on first snapshot write |
| `.backup/` directory | Created on first backup |

The script NEVER exits with an error for missing files — it creates what it needs and proceeds.

## Usage

```bash
# Full scan
~/.hermes/hermes-agent/venv/bin/python \
  ~/.hermes/skills/user-created/skill-maintenance/scripts/maintain.py

# Check specific skill
~/.hermes/hermes-agent/venv/bin/python \
  ~/.hermes/skills/user-created/skill-maintenance/scripts/maintain.py \
  --target <skill-name>
```

### Testing (local only)

Test file `scripts/test_maintain.py` is kept locally but NOT included in the framework distribution.
Users deploy the script and verify by running `maintain.py` directly and checking its output.

```bash
~/.hermes/hermes-agent/venv/bin/python \
  ~/.hermes/skills/user-created/skill-maintenance/scripts/test_maintain.py
```

9 test cases: empty directory, auto-generated new, user-created register, user-created delete/unregister, idempotency, lifecycle status tracking, mixed scenarios, merge detection, post-clear.

## Pitfalls

### [Orphan] is destructive without .bundled_manifest

The [Orphan] phase scans ALL category directories under `~/.hermes/skills/` and moves
non-bundled skills to `auto-generated/`. It identifies bundled skills by checking
`~/.hermes/skills/.bundled_manifest` via `is_bundled_skill()`.

**If `.bundled_manifest` is missing**, `load_bundled_manifest()` returns an empty set,
meaning EVERY skill found in a category directory is treated as a non-bundled orphan.
This includes all Hermes built-in skills (e.g. `creative/architecture-diagram`,
`devops/kanban-orchestrator`, `autonomous-ai-agents/claude-code`) — they would all
be moved to `auto-generated/`, breaking the skill organization.

Conditions where `.bundled_manifest` may be missing:
- Fresh Hermes installation that never installed hub skills
- Non-standard install method (git clone without post-install)
- Corrupted or accidentally deleted manifest

**Safeguard:** Before running maintain.py on an unfamiliar system, verify the manifest exists:
```bash
ls ~/.hermes/skills/.bundled_manifest
```
If missing, either skip [Orphan] (comment out the call in `run_global_scan()`) or
reinstall Hermes skills to regenerate it. Do NOT run [Orphan] blindly on a bare system.

### Don't rewrite user's existing skills without permission

When restructuring or migrating skills, the user's original content is theirs. Moving directories and updating paths is fine. Rewriting the script logic, SKILL.md content, or behavior without explicit permission is NOT fine.

### Keep old files when changing data paths — don't delete

When you consolidate multiple data files into one (e.g. merging a manifest into a registry), redirect the code paths only — do not delete the old files. Deleting old files is seen as destructive even when their data has been merged.

Correct approach:
1. Merge data from old file into new file
2. Update all code to read/write the new file only
3. Keep the old file on disk as a static reference/backup
4. Only delete old files if the user explicitly asks for cleanup

### SOUL.md format conventions

Section numbers: `## N. TITLE` (sequential, no 6A/6B). Sub-rules: `N.M` or `N.M.P`. Governance keywords: `MUST`, `PROHIBITED`, `ENFORCED`.

When writing or editing SOUL.md rules:

- **One sentence per rule.** Don't write three sub-rules that say the same thing. If multiple clauses are needed, use N.M.P sub-numbering.
- **Pure English.** Section titles and body text are English. Chinese examples use Chinese only inside quotes or as example values. Do not mix languages within a single sentence.
- **Follow existing section patterns.** Read the surrounding 3-4 rules before writing a new one. Match the existing tone, indentation, and keyword style.
- **Read the full file before writing.** SOUL.md 3.3.2 requires reading full content before any write_file or patch. Partial reads (offset/limit) miss context.

### Bundled skill name mismatch (creative-ideation case)

`is_bundled_skill()` checks TWO sources against `.bundled_manifest`:
1. Directory name (fast path)
2. SKILL.md frontmatter `name:` field (fallback)

This prevents false positives when a bundled skill's directory name differs from its manifest key (e.g. `creative-ideation` directory with `name: ideation` in frontmatter).

### SKILL.md auto-fix only applies to auto-generated/

`ensure_skill_md_standard()` is called for `auto-generated/` skills only. [Reg] never modifies user-created/ skill content.

### Merge detection scope: auto-generated/ only

Only entries with lifecycle.type=auto-generated and lifecycle.status=active are scanned for merge candidates.
User-created/ skills are never included — they are hand-crafted by the user, not agent-generated.

### Triggers empty for auto-generated is BY DESIGN, not a bug

Auto-generated skills are registered with empty triggers. The user decides
whether to enable them and what natural phrases trigger the skill.

### Read full file before editing the skill's own files

When patching `maintain.py` or editing this `SKILL.md`, use `skill_view()` (no offset/limit)
to read the full file before calling `skill_manage(action='patch')`. Partial reads miss context.
SOUL.md 3.3.2 requires reading full content before writing.

### README describes the current project, not version history

The project README should describe what the project IS now — its architecture, structure, and
how to use the latest version. Do NOT add version banners ("> vX.X.X — Feature Name") or
changelog sections to README. Version announcements and change logs belong in `RELEASE_NOTE_*.md`.

When updating README after a release:
- Update descriptions of capabilities to match the current version's behavior
- Update hard data (test counts, file paths, directory structures)
- Do NOT add "New in vX.X.X" commentary — that belongs in the release note

### Test assertions must handle unordered output

When a test checks output that contains skill names (e.g. merge detection output
`hermes-setup <-> hermes-debug`), the order may be alphabetical by name. Do NOT
hardcode a specific order. Either:

```python
assert ("X <-> Y" in out or "Y <-> X" in out)
# or check both names individually:
assert "X" in out and "Y" in out
```

This applies to any tool output where the sequence depends on iteration order,
alphabetical sorting, or parallel execution.

### Verify from a fresh clone, not just the working tree

After updating any deployable files (framework/ templates, maintain.py, SKILL.md),
validate the full user workflow from a fresh state:

```bash
cd /tmp && git clone <repo-url> test-verify
cp -r framework/SOUL.md test-verify/.hermes/
# ... follow the Quick Start deploy steps
python test-verify/.hermes/.../scripts/test_maintain.py
```

This catches issues that don't appear when testing from the working tree:
stale file references, missing template files, path mismatches in deployment instructions.

### SKILL.md is a usage guide, not code documentation

When editing this `SKILL.md`, remember it exists to tell the agent how to USE the tool, not
to document implementation internals. Implementation details (scoring formulas, function names,
calibration data, historical bugs) belong in `references/`, not in `SKILL.md` body.

Test: after writing a section, check if it answers all three of:
1. "What does this do?" (concept, not code)
2. "What should I look for in the output?" (concrete signals)
3. "What should I do about it?" (next actions)

If a section only answers #1, it belongs in `references/`.

### Deploy path awareness in framework/ documentation

When writing deploy commands in `framework/README.md` or `framework/skills/*/README.md`,
remember the reader is reading from WITHIN the `framework/` directory. Commands like
`cp SOUL.md ~/.hermes/SOUL.md` are correct from within `framework/`. Do NOT prefix
with `framework/` — that creates a non-existent `framework/framework/` path.

When writing deploy commands for the repository root README, the correct prefix is
`framework/` (e.g. `cp framework/SOUL.md ~/.hermes/SOUL.md`). Know which directory
the reader is in before writing paths.

## Single Data Source — Unified Registry

All skill data lives in one file. The `lifecycle` field on each capability entry tracks auto-generated skill lifecycle:

| File | Path | Read by | Purpose |
|---|---|---|---|
| `user_capabilities.json` | `user-registry/` | `capability_finder.py` + maintain.py | Routing table (triggers → skills) + lifecycle tracking (status/note/type) via each entry's `lifecycle` field |
| `.bundled_manifest` | `skills/` | maintain.py + hermes system | System built-in skill whitelist |

## References

- `scripts/maintain.py` — The script itself (v6 — unified registry, single registry file)
- `scripts/test_maintain.py` — 9 test cases (local-only, not in framework)
- `references/session-2026-05-15-unified-registry.md` — v5→v6 migration: two JSONs merged into one, lifecycle field design, removed files
- `references/session-2026-05-15-unified-registry.md` — v5→v6 migration: two JSONs merged into one, lifecycle field design, removed files
- `references/session-2026-05-13-soulmd-enforcement-gap.md` — [Orphan] auto-migration origin
- `references/session-2026-05-13-migration-run.md` — Live migration (4 skills relocated)
- `references/session-2026-05-13-code-cleanup.md` — Dead code removal + output labels
- `references/session-2026-05-13-portability.md` — Self-bootstrapping
- `references/session-2026-05-13-merge-and-desc-sync.md` — Merge hermes-agent-setup ↔ hermes-wsl-tool-setup + description auto-sync added
- `references/session-2026-05-13-merge-restore-cleanup.md` — Merge detection restore
- `references/session-2026-05-13-merge-rigor-enhancement.md` — Jaccard gate + `.split()` fix + false positive calibration
- `references/session-2026-05-13-skills-as-usage-guides.md` — SKILL.md 写作原则（格式一致、简洁优先、操作纪律）
- `references/session-2026-05-13-v2.0.0-release.md` — v2.0.0 release session notes
- `references/test-coverage-bundled-manifest-gap.md` — [Orphan] test coverage gap (BUNDLED_MANIFEST_PATH not mocked)
- `references/portability-bundled-manifest-gap.md` — [Orphan] portability risk on systems without .bundled_manifest
- `references/github-release-notes-format.md` — GitHub Release 正文格式（纯 Markdown，禁用 HTML/Mermaid）
- `references/standalone-project-extraction.md` — Pattern for extracting a focused tool from a larger framework into its own repository. Covers repo-as-skill-directory structure, user_skills/ single-directory model, bootstrap-at-startup, and single self-registration. Derived from the skill-auto-maintain project.
- `references/open-source-readme-design.md` — README and Release Notes design patterns: Mermaid flowcharts, before/after comparisons, feature cards, language switcher, Release renderer limitations, and common pitfalls.
