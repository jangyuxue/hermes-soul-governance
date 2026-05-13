---
name: skill-maintenance
description: "Automated skill maintenance tool. Full scan: [Orphan] migrate misplaced skills from category dirs to auto-generated/ (register + manifest in one pass), [Sync] auto-generated/ vs manifest diff (new/deleted/revived + description auto-sync), [Reg] user-created/ registry consistency (add/remove, no content changes), [Check] validation warnings + multi-dimensional merge detection. Portability: auto-creates missing registry, manifest, and directories. SKILL.md auto-fix for auto-generated/ only."
version: 5.8.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [maintenance, skills, cleanup, audit, registry]
    related_skills: [multi-deliverable-project, user-memory-system]
---

# Skill Maintenance Tool v5

## Directory Structure

```
~/.hermes/
├── SOUL.md                      ← Governance rules (edit Section 1)
├── skills/
│   ├── auto-generated/          ← Agent self-generated skills
│   │   ├── self_created_skills.json
│   │   └── <skill-name>/
│   ├── user-created/            ← User-created skills
│   │   ├── skill-maintenance/   ← scripts/maintain.py lives here
│   │   └── <skill-name>/
│   └── <category>/              ← Bundled skills
├── user-memory/                 ← Auto-populated by agent
└── user-registry/
    ├── user_capabilities.json   ← Registry (routing table for capability_finder.py)
    └── capability_finder.py     ← Trigger matcher
```

Framework template (`framework/`) is a self-contained copyable package.
See main README for per-directory deployment commands.
skill-maintenance is INCLUDED inside `framework/skills/user-created/skill-maintenance/`.
No separate install step needed.

## Execution Flow ([Orphan] → [Sync] → [Reg] → [Check])

The script runs four parts in strict sequence. [Orphan] MUST run first so newly
relocated skills are present in `auto-generated/` before [Sync] scans it.

### Step 0: Bootstrap (Run Before Parts)

Before any scan step runs, the script ensures all required infrastructure exists:

1. **Load registry** (`user_capabilities.json`):
   - File missing → create with empty `capabilities: []`
   - Print "Created new registry: user_capabilities.json"
   - Backup existing file to `.backup/`

2. **Load manifest** (`self_created_skills.json`):
   - File missing → create with empty `self_created_skills: []`
   - Backup existing file to `.backup/`

3. **Create directories if missing**:
   - `auto-generated/` missing → `os.makedirs()`, print "Created directory: auto-generated/"
   - `user-created/` missing → `os.makedirs()`, print "Created directory: user-created/"

### [Orphan] Misplaced Skills Auto-Migration (SOUL.md Enforcement)

Scans category directories under `skills/` for skills that landed in the wrong place.
Moves non-bundled skills to `auto-generated/`, registers them in the capability registry,
and adds them to the manifest — all in one pass.

What to look for in output:
- `✓ X: <dir>/ → auto-generated/` — skill was relocated
- `→ Registered X → user_capabilities.json` — new registry entry created
- `→ Registry updated: X` — existing entry updated with new path
- `+ Manifest added: X` — new manifest entry created
- `! X: target auto-generated/X already exists` — conflict, needs manual merge
- `No misplaced skills found` — everything where it should be (idempotent)

**Verification:** Run the script again. If [Orphan] reports "No misplaced skills found",
the migration is complete and idempotent.

### [Sync] Auto-generated Manifest Diff

Compares `auto-generated/` directory against `self_created_skills.json` and syncs them:

- **New skill** — disk has a skill the manifest doesn't → auto-fix SKILL.md format, add to manifest, register in capability registry
- **Deleted skill** — manifest says active but disk removed → mark as deleted in manifest, unregister from registry
- **Revived skill** — manifest says deleted but disk reappears → restore to active, re-register
- **Description auto-sync** — reads each active skill's `description` from SKILL.md frontmatter and propagates changes to both manifest and registry. Edit a skill's SKILL.md description and it syncs everywhere on the next scan. No manual three-way sync needed.

What to look for in output:
- `+ Manifest added: X` or `~ Manifest updated: X` — manifest sync
- `+ Registered X → user_capabilities.json` — new skill registered
- `~ Manifest description sync: X` / `~ Registry description sync: X` — description propagated
- `No changes` — manifest is consistent with disk

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

## Portability (Self-Bootstrapping)

The script is designed to run on a fresh `~/.hermes/` with zero pre-configuration.

| Missing item | What happens |
|---|---|
| `user_capabilities.json` | Created with empty `capabilities: []` |
| `user-registry/` directory | Created via `os.makedirs` (by save_json) |
| `auto-generated/` directory | Created, prints "Created directory: auto-generated/" |
| `user-created/` directory | Created, prints "Created directory: user-created/" |
| `self_created_skills.json` | Created with empty manifest |
| `.backup/` directory | Created on first backup |
| `.history/` directory | Created on first snapshot write |

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

## Pitfalls

### Don't rewrite user's existing skills without permission

When restructuring or migrating skills, the user's original content is theirs. Moving directories and updating paths is fine. Rewriting the script logic, SKILL.md content, or behavior without explicit permission is NOT fine.

### SOUL.md format conventions

Section numbers: `## N. TITLE` (sequential, no 6A/6B). Sub-rules: `N.M` or `N.M.P`. Governance keywords: `MUST`, `PROHIBITED`, `ENFORCED`.

### Bundled skill name mismatch (creative-ideation case)

`is_bundled_skill()` checks TWO sources against `.bundled_manifest`:
1. Directory name (fast path)
2. SKILL.md frontmatter `name:` field (fallback)

This prevents false positives when a bundled skill's directory name differs from its manifest key (e.g. `creative-ideation` directory with `name: ideation` in frontmatter).

### SKILL.md auto-fix only applies to auto-generated/

`ensure_skill_md_standard()` is called for `auto-generated/` skills only. [Reg] never modifies user-created/ skill content.

### Merge detection scope: auto-generated/ only

Only active manifest entries (auto-generated/) are scanned for merge candidates.
User-created/ skills are never included — they are hand-crafted by the user, not agent-generated.

### Triggers empty for auto-generated is BY DESIGN, not a bug

Auto-generated skills are registered with empty triggers. The user decides
whether to enable them and what natural phrases trigger the skill.

### Read full file before editing the skill's own files

When patching `maintain.py` or editing this `SKILL.md`, use `skill_view()` (no offset/limit)
to read the full file before calling `skill_manage(action='patch')`. Partial reads miss context.
SOUL.md 3.3.2 requires reading full content before writing.

## Three Data Files

| File | Path | Read by | Purpose |
|---|---|---|---|
| `user_capabilities.json` | `user-registry/` | `capability_finder.py` | Routing table — user speaks → triggers match → execute skill |
| `self_created_skills.json` | `auto-generated/` | maintain.py (internal) | Auto-generated skill lifecycle tracking |
| `.bundled_manifest` | `skills/` | maintain.py + hermes system | System built-in skill whitelist |

## References

- `scripts/maintain.py` — The script itself
- `references/session-2026-05-13-soulmd-enforcement-gap.md` — [Orphan] auto-migration origin
- `references/session-2026-05-13-migration-run.md` — Live migration (4 skills relocated)
- `references/session-2026-05-13-code-cleanup.md` — Dead code removal + output labels
- `references/session-2026-05-13-portability.md` — Self-bootstrapping
- `references/session-2026-05-13-merge-and-desc-sync.md` — Merge hermes-agent-setup ↔ hermes-wsl-tool-setup + description auto-sync added
- `references/session-2026-05-13-merge-restore-cleanup.md` — Merge detection restore
- `references/session-2026-05-13-merge-rigor-enhancement.md` — Jaccard gate + `.split()` fix + false positive calibration
- `references/session-2026-05-13-skills-as-usage-guides.md` — SKILL.md 写作原则（格式一致、简洁优先、操作纪律）
