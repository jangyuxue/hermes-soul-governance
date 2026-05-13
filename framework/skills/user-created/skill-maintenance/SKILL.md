---
name: skill-maintenance
description: "Automated skill maintenance tool. Full scan: [Orphan] migrate misplaced skills from category dirs to auto-generated/ (registers to user_capabilities.json and manifest in one pass), [Sync] auto-generated/ vs manifest diff (new/deleted/revived + description auto-sync to registry), [Reg] user-created/ registry consistency (add/remove, never modifies content), [Check] validation warnings + merge candidate detection. Portability: auto-creates missing registry, manifest, and directories. SKILL.md auto-fix for auto-generated/ only. Merge detection: active auto-generated skills compared pairwise (name + topic overlap score >= 0.3)."
version: 5.7.0
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

Scans EVERY category directory under `skills/` that is NOT `auto-generated/`, `user-created/`,
`.hub`, `.backup`, or `.history`. For each skill found:

1. **Check if bundled** — `is_bundled_skill()` does TWO checks against `.bundled_manifest`:
   - Directory name matches manifest key? → system skill, skip
   - SKILL.md frontmatter `name:` field matches manifest key? → system skill, skip
   - Neither matches → non-bundled skill, proceed to migrate

2. **Check target conflict** — if `auto-generated/<name>/` already exists on disk:
   - Flag: "! X: target auto-generated/X already exists (manual merge needed)"
   - Do NOT overwrite

3. **Move directory** — `shutil.move(source_path, target_path)`
   - Print: "✓ X: devops/ → auto-generated/"

4. **Register or update in user_capabilities.json** (one step, not deferred):
   - Skill IS already registered → update `category` to `auto-generated`, rewrite `script` path
   - Skill is NOT registered → create entry: `{id, name, category:"auto-generated", triggers:[], ...}`
   - Print: "→ Registry updated: X" or "→ Registered X → user_capabilities.json"

5. **Add or update manifest entry** (`self_created_skills.json`):
   - Skill NOT in manifest → add: `{name, status:"active", registered:true, note:"Migrated from...", ...}`
   - Skill IS in manifest → compare `description`, `status`, `registered` fields; update if stale
   - Print: "+ Manifest added: X" or "~ Manifest updated: X description"

This closes the SOUL.md enforcement loop: SOUL.md rule 7.2 says agent-created skills
MUST go to `auto-generated/` or `user-created/`. [Orphan] ensures any skill that lands
in a bundled category directory gets relocated, registered, and tracked in one pass.

**Verification:** Run maintain.py again. If [Orphan] reports "No misplaced skills found",
the migration is complete and idempotent.

### [Sync] Auto-generated Manifest Diff

Scans `auto-generated/` directory and compares against `self_created_skills.json`:

**New skill detection:** Disk has but manifest does not
- Auto-fix SKILL.md format (`ensure_skill_md_standard()`)
- Add to manifest with `status: active`
- Register in `user_capabilities.json` if not already there

**Deletion detection:** Manifest has active but disk does not
- Mark `status: deleted` in manifest
- Unregister from `user_capabilities.json`

**Revival detection:** Manifest has deleted but disk reappears
- Mark `status: active` in manifest
- Re-register in `user_capabilities.json`

**Description auto-sync** — After all sync operations, [Sync] reads each
active skill's `description` from SKILL.md frontmatter and compares it
against both `self_created_skills.json` and `user_capabilities.json`:
- SKILL.md description differs from manifest → update manifest entry
- SKILL.md description differs from registry → update registry entry
- Print: "~ Manifest description sync: X" / "~ Registry description sync: X"
- This ensures editing a skill's SKILL.md description propagates everywhere
  in one scan. No manual three-way sync needed.

### [Reg] User-created Registry Check

Scans `user-created/` and checks registry consistency only:
- Disk has skill but registry does not → add to registry (category=user-created)
- Registry has skill but disk does not → remove from registry
- **Does NOT modify any skill content or SKILL.md format**

### [Check] Validation Warnings + Merge Detection

After all operations, runs checks in order:

1. **Registry entry validation** (all skills, including user-created):
   - Empty triggers → "! X: triggers is empty — skill unreachable by capability_finder.py"
   - Broken script paths → "! X: script not found — {path}"

2. **SKILL.md format validation** (auto-generated/ only):
   - Missing frontmatter → prepend name/description/version/author
   - Missing `name:` → add from directory name
   - Missing `description:` → auto-generate
   - Missing H1 heading → add
   - Print: "! X: SKILL.md auto-fixed ({changes})"

3. **Merge candidate detection** (auto-generated/ only):
   - Compare every active auto-generated skill pairwise
   - Score = name token overlap (+0.3) + topic keyword overlap (+0.1/keyword, max 0.4)
   - Report pairs with score >= 0.3 → "! X <-> Y (score=0.4, topic overlap: {...})"
   - Deleted skills are excluded from merge detection

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

## Testing

```bash
~/.hermes/hermes-agent/venv/bin/python \
  ~/.hermes/skills/user-created/skill-maintenance/scripts/test_maintain.py
```

8 test cases: empty directory, auto-generated new, user-created register, user-created delete/unregister, idempotency, manifest deletion, mixed scenarios, post-clear.

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

`detect_merge_candidates()` only scans active manifest entries (auto-generated/).
User-created/ skills are never included in merge suggestions.

### Triggers empty for auto-generated is BY DESIGN, not a bug

Auto-generated skills are registered with `triggers: []`. This is a deliberate human-in-the-loop:
user decides whether to route the skill and what natural phrases trigger it.

### Dead code removal is required, not optional

After any major refactor, `grep` all function definitions and verify each is called. Remove unused constants like `ROLLBACK_LOG`. Run all tests after cleanup.

### Code comments must be all-English

No Chinese characters in `maintain.py` — all comments, docstrings, and section headers in English.
Output labels: `[Orphan]`, `[Sync]`, `[Reg]`, `[Check]`.

### Directory creation must notify the user

When creating missing directories, print "Created directory: auto-generated/" so the user knows what happened. Silent creation is confusing.

## Three Data Files

| File | Path | Read by | Purpose |
|---|---|---|---|
| `user_capabilities.json` | `user-registry/` | `capability_finder.py` | Routing table — user speaks → triggers match → execute skill |
| `self_created_skills.json` | `auto-generated/` | maintain.py (internal) | Auto-generated skill lifecycle tracking |
| `.bundled_manifest` | `skills/` | maintain.py + hermes system | System built-in skill whitelist |

## References

- `scripts/maintain.py` — The script itself
- `scripts/test_maintain.py` — 8 test cases
- `references/session-2026-05-13-soulmd-enforcement-gap.md` — [Orphan] auto-migration origin
- `references/session-2026-05-13-migration-run.md` — Live migration (4 skills relocated)
- `references/session-2026-05-13-code-cleanup.md` — Dead code removal + output labels
- `references/session-2026-05-13-portability.md` — Self-bootstrapping
- `references/session-2026-05-13-merge-and-desc-sync.md` — Merge hermes-agent-setup ↔ hermes-wsl-tool-setup + description auto-sync added
- `references/session-2026-05-13-merge-restore-cleanup.md` — Merge detection restore
