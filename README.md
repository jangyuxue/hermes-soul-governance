<p align="center">
  <br>
  <b>SOUL.md Governance Framework</b><br>
  <i>Stop repeating yourself. Let the agent remember, organize, and improve.</i>
</p>

<br>

---

## The Problem

Hermes Agent is powerful, but out of the box:

- **No persistent memory** — every session starts from scratch. You tell the agent your preferences, environment, and workflows over and over.
- **Skills are disposable** — after a complex debugging session or a tricky workflow, the knowledge disappears. Next time, the agent starts from zero.
- **No quality control** — auto-generated skills pile up with no way to track what's useful and what's stale.
- **Triggers are manual** — skills exist on disk but the agent can't find them because triggers are empty or missing.

The result: you keep repeating yourself, and the agent never gets smarter over time.

---

## The Solution

**SOUL.md** is a governance layer for Hermes Agent that turns it from a session-scoped assistant into a learning system.

Three core capabilities:

| Capability | What it does | Without it | With it |
|------------|-------------|-----------|---------|
| **Structured Memory** | User preferences, identity, environment, workflows are stored in persistent files | Agent forgets everything next session | Agent remembers your habits, tools, and processes |
| **Skill Lifecycle** | Skills are auto-registered, validated, and cleaned up | Skills pile up unmanaged; triggers stay empty | Skills are tracked, reachable, and quality-checked |
| **Trigger Matching** | User input is scored against all registered skill triggers | Agent can't find the right skill | Agent routes to the correct skill automatically |

---

## Features

- **File-based memory** — preferences, profile, environment, and workflows persist across sessions
- **Auto-registration** — drop a skill into a directory, `maintain.py` registers it automatically
- **Self-healing** — malformed `SKILL.md` files are auto-fixed (missing frontmatter, name, description)
- **Validation** — warns about empty triggers, broken script paths, unregistered orphans
- **Closed loop** — create → register → match → execute → cleanup, all automated
- **No manual JSON editing** — `user_capabilities.json` is managed entirely by the maintenance script
- **Dual-language support** — triggers work in any language

---

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

| Type | Location | Created by | Managed by |
|------|----------|------------|------------|
| Auto-generated | `auto-generated/` | Agent (after complex tasks) | maintain.py + agent |
| User-created | `user-created/` | User | maintain.py + agent |

### Trigger Matching

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
python3 framework/skills/user-created/skill-maintenance/test_maintain.py
```

11 tests: empty directory, new skill detection, SKILL.md auto-fix, registry sync, deletion unregister, idempotency, manifest detection, mixed skills, validation warnings, clean state — **all passing**.

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
