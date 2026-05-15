# skill-maintenance

Automated skill lifecycle management for Hermes Agent.

## What it does

Runs four maintenance phases in strict sequence:

| Phase | Description |
|-------|-------------|
| [Orphan] | Scans all category dirs, migrates misplaced non-bundled skills to `auto-generated/`, registers with lifecycle fields |
| [Sync] | Compares `auto-generated/` disk against registry lifecycle fields: detects new/deleted/revived skills, auto-syncs SKILL.md `description` changes to registry |
| [Reg] | Checks `user-created/` registry consistency — adds missing entries, removes deleted ones. Never touches skill content |
| [Check] | Validates registry entries (empty triggers, broken paths), auto-fixes malformed SKILL.md (auto-generated only), detects merge candidates via 5-axis scoring with anti-false-positive gates |

## Files

| File | Purpose |
|------|---------|
| `scripts/maintain.py` | The maintenance script (v6 — unified registry) |
| `SKILL.md` | Skill documentation |
