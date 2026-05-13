---
name: skill-maintenance
description: "Automated skill maintenance tool. Scans auto-generated/ to diff manifest, scans user-created/ to check registry sync."
version: 5.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [maintenance, skills, cleanup, audit, registry]
---

# Skill Maintenance Tool v5

## Directory Structure

```
~/.hermes/skills/
├── auto-generated/              ← Agent self-generated skills
│   ├── self_created_skills.json ← Manifest file
│   ├── .history/                ← Change history
│   └── <skill-name>/
├── user-created/                ← User-created skills
│   ├── skill-maintenance/
│   └── <skill-name>/
└── <category>/                  ← Bundled skills
```

## Two-Part Logic

### Part A: Auto-generated Manifest Diff

Script scans `auto-generated/` and compares against `self_created_skills.json`:
- Disk has skill but manifest does not → add to manifest + auto-register
- Manifest has skill but disk does not → mark as deleted
- Registry sync: active skills auto-registered, deleted skills auto-unregistered

### Part B: User-created Registry Check

Script scans `user-created/` and only checks registry:
- Disk has skill but registry does not → add to registry (category=user-created)
- Registry has skill but disk does not → remove from registry
- Does NOT modify any skill content

### Auto-created entry format

When script detects a new skill, it creates:
- `id`: from directory name
- `name`: auto-formatted
- `category`: `"user-created"` or `"auto-generated"`
- `triggers`: `[]` (EMPTY — agent fills in)
- `description`: from SKILL.md frontmatter
- `script`: `null` (agent sets if skill has script)
- `dependencies`: `[]`
- `examples`: `[]`

Agent MUST after auto-create:
1. Check if new entries were created (triggers empty)
2. Tell user: "New skill registered, triggers is empty, please add trigger words"
3. User adds triggers manually to `user_capabilities.json`
4. If skill has a script, agent MUST set the `script` field path

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

## Framework Architecture (Closed Loop)

```
User speaks → SOUL.md rules → capability_finder.py matches triggers → Skill executes
                                          ↓ (no match)
                                   direct_answer (agent responds)

New skill on disk → maintain.py detects → writes to user_capabilities.json
Skill deleted → maintain.py detects → removes from user_capabilities.json
```

## Testing

```bash
~/.hermes/hermes-agent/venv/bin/python \
  ~/.hermes/skills/user-created/skill-maintenance/test_maintain.py
```

Test coverage: empty directory, new skill detection, registry sync, deletion unregister, idempotency, manifest deleted detection, mixed skills, clean after removal.
