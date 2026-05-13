# skill-maintenance

Automated skill lifecycle management for Hermes Agent.

## What it does

Runs four maintenance phases in strict sequence:

| Phase | Description |
|-------|-------------|
| [Orphan] | Scans all category dirs, migrates misplaced non-bundled skills to `auto-generated/`, registers and tracks in one pass |
| [Sync] | Compares `auto-generated/` dir against manifest: detects new/deleted/revived skills, syncs SKILL.md `description` changes to manifest and registry |
| [Reg] | Checks `user-created/` registry consistency — adds missing entries, removes deleted ones. Never touches skill content |
| [Check] | Validates registry entries (empty triggers, broken paths), auto-fixes malformed SKILL.md (auto-generated only), detects merge candidates via 5-axis scoring with anti-false-positive gates |

## Files

| File | Purpose |
|------|---------|
| `scripts/maintain.py` | The maintenance script (v5.8.0) |
| `SKILL.md` | Skill documentation for the agent |

## Usage

```bash
# Full scan
~/.hermes/hermes-agent/venv/bin/python \
  ~/.hermes/skills/user-created/skill-maintenance/scripts/maintain.py
```
