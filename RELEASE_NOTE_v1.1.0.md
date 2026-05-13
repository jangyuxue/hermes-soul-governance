## v1.1.0 — Skill Maintenance Overhaul (2026-05-13)

The `maintain.py` skill maintenance tool has been significantly upgraded with new automation capabilities, dead code removal, and numerous fixes.

### New Features

| Feature | Description |
|---------|-------------|
| [Orphan] auto-migration | Scans all category directories, moves non-bundled skills to `auto-generated/` in one pass |
| [Orphan] one-pass registry | Registers to `user_capabilities.json` during migration, no deferral |
| [Orphan] manifest field sync | Updates stale `description/status/registered` fields in manifest |
| [Orphan] dual bundled check | Dir name + SKILL.md frontmatter `name:` against `.bundled_manifest` (fixes `creative-ideation` false positive) |
| [Sync] description auto-sync | SKILL.md description change → manifest + registry auto-update |
| [Check] merge detection | Pairwise name + topic overlap scoring (threshold >= 0.3) |
| Self-bootstrapping | Creates missing registry, manifest, directories on first run — zero pre-configuration |
| Output notifications | Prints "Created directory: ..." on each auto-created path |

### Removed Dead Code (~112 lines)

- `classify_unknown_skill` + 5 helper functions (replaced by `.bundled_manifest`)
- `detect_merge_candidates` (defined but never called)
- `get_skill_author` (return value unused)
- `ROLLBACK_LOG` (path defined but never written)

### Fixes

- **Execution order**: [Orphan] → [Sync] → [Reg] → [Check] (was A→B→E→C with skipped letters)
- **Tag labels**: Standardized to [Orphan]/[Sync]/[Reg]/[Check] (was jumping across letters)
- **Snapshot completeness**: Added missing `misplaced_changes` field
- **SKILL.md auto-fix scope**: Now only applies to `auto-generated/` (was incorrectly touching `user-created/`)
- **Code comments**: All-English (was mixed CN/EN)
- **Line count**: 725 → 717, readability improved

### Still Manual

1. Merge detection reports only — script cannot understand semantic content
2. Triggers remain empty by design — user decides trigger phrases
3. Script path must be set by user per skill
4. `skill_manage` delete → next [Sync] cycle clears registry (intentional batch delay)
5. `~/.hermes/skills/` root must exist before first run

### Quick Start

```bash
git clone https://github.com/jangyuxue/hermes-soul-governance.git
cd hermes-soul-governance
cp framework/SOUL.md ~/.hermes/SOUL.md
cp -r framework/user-memory ~/.hermes/
cp -r framework/user-registry ~/.hermes/
cp -r framework/skills/user-created ~/.hermes/skills/
# Then configure SOUL.md and disable native memory
~/.hermes/hermes-agent/venv/bin/python \
  ~/.hermes/skills/user-created/skill-maintenance/scripts/maintain.py
```

### Full Changelog

[See README](https://github.com/jangyuxue/hermes-soul-governance#changelog)
