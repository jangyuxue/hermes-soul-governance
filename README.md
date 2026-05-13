<p align="center">
  <br>
  <b>SOUL.md Governance Framework</b><br>
  <i>Structured memory, skill lifecycle, and operational rules for Hermes Agent</i>
</p>

<br>

## Quick Start

```bash
# 1. Copy the framework (includes everything)
cp -r framework/* ~/.hermes/

# 2. Edit SOUL.md — replace placeholders in Section 1
vim ~/.hermes/SOUL.md

#    1.1 Role: <YOUR_ROLE>       → "Backend Engineer", "Data Scientist", etc.
#    1.2 Language: <YOUR_LANGUAGE> → "English", "Chinese", etc.

# 3. Disable Hermes default memory (this framework manages its own)
hermes config set memory.memory_enabled false
hermes config set memory.user_profile_enabled false

# 4. Run the maintenance script
~/.hermes/hermes-agent/venv/bin/python \
  ~/.hermes/skills/user-created/skill-maintenance/scripts/maintain.py
```

---

## Overview

**SOUL.md** is a single-source-of-truth configuration file injected into the agent's system prompt every turn. It governs:

| Section | Topic |
|---------|-------|
| 1 | Identity & Role |
| 2 | Response Standards |
| 3 | Persistence — Write Protocol |
| 4 | Retrieval Protocol |
| 5 | Operational Constraints |
| 6 | Skill Dispatch |
| 7 | Skill Creation & Storage |
| 8 | Compliance & Audit |

---

## How It Works

### Memory Flow

Agent writes user data to structured files based on trigger keywords:

| File | Triggered by |
|------|-------------|
| `user-memory/preferences.md` | "I like...", "I prefer...", "Your tone should be..." |
| `user-memory/user-profile.md` | "I am...", "My name is...", "I work as..." |
| `user-memory/environment-setup.md` | "My system is...", "I use...", "I installed..." |
| `user-memory/workflows/<name>.md` | "My steps are...", "First I do X, then Y..." |

### Skill Lifecycle

```
New skill on disk → maintain.py detects
  → Auto-fixes SKILL.md (adds frontmatter if missing)
  → Registers in user_capabilities.json
  → Agent fills in triggers
  → Skill is matchable

Skill deleted → maintain.py detects → unregisters from registry
```

Skill types:

| Type | Location | Created by | Managed by |
|------|----------|------------|------------|
| Auto-generated | `auto-generated/` | Agent (after complex tasks) | maintain.py + agent |
| User-created | `user-created/` | User | maintain.py + agent |

### Skill Matching

```
User speaks → capability_finder.py
  → Scores triggers: exact=100, contains=50, contained=10
  → Returns best match
    → type="skill" → execute script
    → type="direct_answer" → agent responds directly
```

---

## Directory Structure

```
~/.hermes/
├── SOUL.md                            ← Governance rules
├── skills/
│   ├── auto-generated/                ← Agent self-learned skills
│   │   ├── self_created_skills.json   ← Manifest
│   │   └── <skill-name>/
│   ├── user-created/                  ← User-defined skills
│   │   └── <skill-name>/
│   └── <category>/                    ← Bundled skills
├── user-memory/                       ← Auto-populated by agent
│   ├── preferences.md
│   ├── user-profile.md
│   ├── environment-setup.md
│   └── workflows/
└── user-registry/
    ├── user_capabilities.json         ← Skill registry
    └── capability_finder.py           ← Trigger matcher
```

---

## Scripts

### maintain.py

Scans `auto-generated/` and `user-created/` directories. Detects new and deleted skills, syncs the registry, auto-fixes SKILL.md formatting, and validates triggers and script paths.

```bash
~/.hermes/hermes-agent/venv/bin/python \
  ~/.hermes/skills/user-created/skill-maintenance/scripts/maintain.py
```

### capability_finder.py

Reads `user_capabilities.json` and matches user input to registered skills using a scoring algorithm (exact=100, contains=50, contained=10).

```bash
~/.hermes/hermes-agent/venv/bin/python \
  ~/.hermes/user-registry/capability_finder.py "generate image"
```

---

## Testing

```bash
python3 skills/skill-maintenance/test_maintain.py
```

Test coverage: empty directory, new skill detection, SKILL.md auto-fix, registry sync, deletion unregister, idempotency, manifest detection, mixed skills, validation warnings, clean state — **11 tests, all passing**.

---

## Design Principles

1. **Single source of truth** — SOUL.md is the only governance file
2. **Read-before-write** — prevents data corruption
3. **Separated concerns** — auto-generated, user-created, and bundled skills have distinct directories with different behaviors
4. **Non-destructive** — script never modifies user-created skill content
5. **Audit trail** — all changes logged with timestamps and snapshots

---

## License

MIT
