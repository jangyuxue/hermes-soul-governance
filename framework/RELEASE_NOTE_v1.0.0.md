## v1.0.0 — 2026-05-13

### What's Changed

The native Hermes Agent memory system has two architectural defects:

**Memory Compression Loop**
`MEMORY.md` and `USER.md` enforce 2200/1375 character limits. When exceeded, the system auto-compresses by merging entries and discarding context. This cycle repeats on every overflow, leading to progressive data loss and rule dilution.

**Skill System Maintenance Gap**
The framework provides a creation path for skills but no corresponding maintenance — no auto-registration, no validation, no cleanup, no expiry.

SOUL.md addresses both through an **immutable governance anchor** (a read-only SOUL.md with no write path in the codebase) + **structured file persistence**.

### New Features

- **SOUL.md v2.1** — 8-section immutable governance layer injected at prompt_parts[0]
- **Framework Template** (`framework/`) — drop-in deployable structure for `~/.hermes/`
- **Categorized Memory** (`user-memory/`) — preferences.md, user-profile.md, environment-setup.md, workflows/
- **Capability Discovery** (`user-registry/`) — capability_finder.py + user_capabilities.json with trigger scoring
- **Skill Maintenance Script** (`maintain.py`) — auto-registration, validation, cleanup, manifest sync
- **11 Test Cases** — empty directory, new skill detection, SKILL.md auto-fix, registry sync, idempotency, mixed types

### Quick Start

```bash
cp -r framework/* ~/.hermes/
vim ~/.hermes/SOUL.md          # Edit Section 1: Role & Language
hermes config set memory.memory_enabled false
hermes config set memory.user_profile_enabled false
~/.hermes/hermes-agent/venv/bin/python \
  ~/.hermes/skills/user-created/skill-maintenance/scripts/maintain.py
```

### Known Limitations

- Rule enforcement depends on model instruction-following capability (inherent to LLM-based systems)
- Skill classification heuristics may need adjustment as agent behavior evolves

### License

MIT
