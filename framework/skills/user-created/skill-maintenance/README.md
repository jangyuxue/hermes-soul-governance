# skill-maintenance

Automated skill lifecycle management for Hermes Agent.

## What it does

Runs five maintenance phases in strict sequence:

| Phase | Description |
|-------|-------------|
| [Orphan] | Scans category dirs for sub-skills AND standalone skills at `skills/<name>/`, migrates non-bundled to `auto-generated/`, registers with lifecycle fields |
| [Sync] | Compares `auto-generated/` disk against registry lifecycle fields: detects new/deleted/revived skills, auto-syncs SKILL.md `description` changes to registry |
| [Reg] | Checks `user-created/` registry consistency — adds missing entries, removes deleted ones. Never touches skill content |
| [Check] | Validates registry entries (empty triggers, broken paths), auto-fixes malformed SKILL.md (auto-generated only), detects merge candidates via 5-axis scoring with anti-false-positive gates |
| [Snapshot] | Saves a timestamped copy of `user_capabilities.json` to `.history/` for change audit and rollback reference |

## Files

| File | Purpose |
|------|---------|
| `scripts/maintain.py` | The maintenance script (v6 — unified registry) |
| `scripts/test_maintain.py` | 9 test cases (local-only, not in framework template) |
| `SKILL.md` | Skill documentation |
