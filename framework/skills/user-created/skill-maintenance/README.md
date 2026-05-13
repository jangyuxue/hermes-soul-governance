# skill-maintenance

Automated skill lifecycle management for Hermes Agent.

## What it does

Scans `auto-generated/` and `user-created/` skill directories to keep the registry in sync:

| Event | Action |
|-------|--------|
| New skill on disk | Creates entry in `user_capabilities.json` |
| Skill deleted | Removes from registry |
| SKILL.md malformed | Auto-fixes (adds frontmatter, name, description) |
| Empty triggers | Warns user |
| Broken script path | Warns user |

## Files

| File | Purpose |
|------|---------|
| `scripts/maintain.py` | The maintenance script |
| `test_maintain.py` | 8 test cases |
| `SKILL.md` | Skill documentation for the agent |

## Usage

```bash
# Full scan
~/.hermes/hermes-agent/venv/bin/python \
  ~/.hermes/skills/user-created/skill-maintenance/scripts/maintain.py
```

## What it checks

1. **auto-generated/** — Compare against `self_created_skills.json` manifest
   - New on disk → add to manifest + register
   - In manifest but not on disk → mark deleted + unregister
2. **user-created/** — Sync with `user_capabilities.json`
   - New on disk → register
   - Not on disk → unregister
3. **Validation** — Warns about
   - Empty triggers (unreachable skills)
   - Missing script paths
   - Malformed SKILL.md (auto-fixed)

## Test

**After deploying to `~/.hermes/`:**

```bash
~/.hermes/hermes-agent/venv/bin/python \
  ~/.hermes/skills/user-created/skill-maintenance/test_maintain.py
```

**Before deployment (from the repository root):**

```bash
python3 framework/skills/user-created/skill-maintenance/test_maintain.py
```
