## v3.0.0 — Unified Registry + SOUL.md v2.2 + Snapshot Archive (2026-05-15)

### Overview

v3.0.0 is a structural consolidation release. Three major changes: unified the skill
registry (eliminating dual-file management), refactored SOUL.md into a tighter
governance document, and added automatic registry snapshot archiving for change audit.

---

### 1. Unified Registry (Single Source of Truth)

Before v3.0.0, skill lifecycle tracking lived in `self_created_skills.json` (manifest)
while routing went through `user_capabilities.json` (registry) — two files that could
drift out of sync.

| Before | After |
|--------|-------|
| `self_created_skills.json` (lifecycle) | **Removed** — merged into registry |
| `user_capabilities.json` (routing only) | `user_capabilities.json` v2.0 — **routing + lifecycle** in one file |
| `maintain.py` v5 — writes to manifest + registry | `maintain.py` v6 — all writes to unified JSON |
| Syncing two files = drift risk | Single write target = atomic updates |

Each skill entry now carries a `lifecycle` field:
```json
{
  "lifecycle": {
    "type": "auto-generated",
    "status": "active",
    "registered": true,
    "note": ""
  }
}
```

**Files affected:**
- `user_capabilities.json` (live system + framework/ + examples/) → v2.0 with lifecycle
- `self_created_skills.json` (live system + framework/ + examples/) → **deleted**
- `maintain.py` → v6, all operations use registry singleton
- `.history/` → removed (old snapshot mechanism), replaced with proper snapshot below

---

### 2. Snapshot Archive (`.history/`)

After each maintenance run, a timestamped copy of the registry is saved to:

```
~/.hermes/skills/user-created/skill-maintenance/.history/snapshot_{YYYYMMDD_HHMMSS}.json
```

This provides a recoverable timeline of registry state changes.

---

### 3. SOUL.md v2.2 — Structural Refactoring

| Change | Before | After |
|--------|--------|-------|
| Version | v2.1 | v2.2 |
| §3.5.1 mapping | Included `add a skill/register function → user_capabilities.json` | **Removed** — skills created via `skill_manage()`, not direct write |
| §5.3 deletion rules | Protected `skills/`, `output/`, `memories/` | Added `skills/*/.history/` |
| §8 Compliance | Separate section | **Merged** into §5 as §5.6-5.8 |
| §7.3 | No snapshot documentation | Added §7.3.6 Registry snapshot path |

---

### 4. Orphan Detection — Standalone Skill Fix

`maintain.py` [Orphan] phase now detects two types of misplaced skills:

1. **Sub-skills** inside a category directory (e.g. `creative/my-skill/`) — existed before
2. **Standalone skills** directly at `skills/<name>/` with their own SKILL.md
   (e.g. `skills/soul-governance/SKILL.md`) — **new in v3.0.0**

Also fixed a latent bug: `make_lifecycle_entry()` was called with a `note=` keyword
parameter it didn't accept, causing a `TypeError` on first orphan migration attempt.

---

### Files Changed (13 files, +406 / -308)

```
README.md                                          |  21 +-
README_CN.md                                       |  20 +-
SOUL.md                                            |  29 +-
framework/SOUL.md                                  |  29 +-
framework/README.md                                |   5 +-
framework/skills/auto-generated/README.md          |   2 +-
.../user-created/skill-maintenance/README.md       |  19 +-
.../user-created/skill-maintenance/SKILL.md        | 202 +++++++---
.../skill-maintenance/scripts/maintain.py          | 325 +++++++----------
framework/user-registry/user_capabilities.json     |  27 +-
examples/user_capabilities.json                    |  11 +-
examples/auto-generated/self_created_skills.json   |  17 --  (deleted)
framework/.../auto-generated/self_created_skills.json | 7 --  (deleted)
```

### Upgrade Notes

Re-deploy the framework to get all v3.0.0 changes:

```bash
cd hermes-soul-governance
git pull
cp framework/SOUL.md ~/.hermes/SOUL.md                    # v2.2 governance rules
cp -r framework/user-registry ~/.hermes/                   # v2.0 registry template
cp -r framework/skills/user-created ~/.hermes/skills/      # v6 maintain.py + updated docs
~/.hermes/hermes-agent/venv/bin/python \
  ~/.hermes/skills/user-created/skill-maintenance/scripts/maintain.py  # first run creates registry snapshot
```

Run the script twice to verify idempotency — the second run should report
`No changes`.

### License

MIT
