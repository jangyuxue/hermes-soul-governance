<p align="center">
  <br>
  <b>SOUL.md Governance Framework</b><br>
  <i>Fix Hermes Agent's broken memory, unmanaged skills, and missing governance layer.</i>
</p>

<br>

---

## The Problem

### 1. Memory is Broken

Hermes stores memory in `MEMORY.md` and `USER.md` — each capped at **2200 and 1375 characters** respectively. That's ~3600 characters total for everything the agent should remember about you.

When the files fill up, Hermes **auto-compresses** existing content to make room. It merges facts, drops context, and keeps writing until it fills up again. Over time, these files become a garbage dump — preferences, environment details, workflows, and random auto-summaries all mashed together with no structure, no priority, no separation.

The result: the injected system prompt becomes incoherent, the agent's output drifts, and you end up with a system that costs more to maintain than it saves.

Worse, the native memory system has **no rules enforcement**. The agent writes to MEMORY.md and USER.md using the `memory()` tool, which bypasses any rules you write inside those files. Rules only apply when the file is **full** and needs compression — otherwise the agent writes blindly.

### 2. Skill System Creates but Never Maintains

Hermes encourages saving skills after complex tasks (5+ tool calls), but there's no:
- **Expiry policy** — skills live forever on disk
- **Quality gate** — malformed or empty skills are accepted
- **Deduplication** — overlapping skills accumulate
- **Auto-registration** — skills are created but never added to `user_capabilities.json`, so `capability_finder.py` can't find them

Result: skill directories fill up with duplicates, garbage, and orphaned files. No one knows what's useful and what's stale.

### 3. No Privacy Isolation in Gateway Mode

When Hermes runs behind a gateway (Telegram, Feishu, etc.), multiple users share one process, one database, and one OS user account. `session_search` has no `user_id` filter — anyone can search anyone else's conversations. `read_file` has no approval gate, so anyone can read config files, API keys, and other users' data.

Current mitigations (`allowed_chats`, `approvals.mode`, SOUL.md rules) are all agent-discipline-dependent. There's no real isolation.

---

## The Solution

### Architecture

```
SOUL.md (unconditional injection, no write path)
  ├── user-memory/          ← Structured persistence (unlimited, no auto-compression)
  │   ├── preferences.md
  │   ├── user-profile.md
  │   ├── environment-setup.md
  │   └── workflows/
  ├── user-registry/        ← Custom skill management
  │   ├── user_capabilities.json
  │   └── capability_finder.py
  └── skills/
      ├── auto-generated/   ← Agent's skills
      └── user-created/     ← User's skills
```

### Layer 1: SOUL.md — Read-Only Rule Anchor

SOUL.md is the only file that is both **unconditionally injected** (no toggle, always loaded) and **system-cannot-write** (no write function exists). Rules placed here cannot be overwritten by memory auto-compression.

Key rules enforced:
- No `memory(action='add')` — disabled via config
- Write protocol: read → merge → write → verify
- Trigger keyword mapping (preferences → `preferences.md`, identity → `user-profile.md`, etc.)
- Search-first retrieval (keyword match before full read)

### Layer 2: user-memory/ — Structured Persistence

Replaces `MEMORY.md` and `USER.md` with unlimited, categorized files:

| File | Stores | Read when |
|------|--------|-----------|
| `preferences.md` | Communication style, tone, habits | User asks about preferences |
| `user-profile.md` | Identity, role, domain | Task involves user context |
| `environment-setup.md` | System config, paths, tools | Action requires execution |
| `workflows/<name>.md` | Step-by-step processes | Workflow is triggered |

Files are **not auto-injected** — loaded on demand only. Most turns consume zero context window.

### Layer 3: user-registry/ — Skill Management

Custom skills need more than creation — they need registration, trigger matching, and maintenance:

| File | Purpose |
|------|---------|
| `user_capabilities.json` | Skill registry with triggers, script paths, config |
| `capability_finder.py` | Trigger word matcher (exact=100, contains=50, contained=10) |
| `maintain.py` | Auto-detect new/deleted skills, sync registry, fix SKILL.md |

---

## Features

- **Disable broken memory** — `memory_enabled: false`, replace with structured files
- **Unlimited storage** — no 2200/1375 char limits, write to disk
- **No auto-compression** — facts stay as written, never merged or dropped
- **Skill auto-registration** — drop a directory, `maintain.py` registers it
- **SKILL.md auto-fix** — missing frontmatter, name, description auto-added
- **Validation** — empty triggers, broken script paths, unregistered orphans warned
- **Closed loop** — create → register → match → execute → cleanup
- **No manual JSON editing** — `user_capabilities.json` managed by script
- **Privacy mitigation** — `allowed_chats` whitelist, read-only SOUL.md

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

User speaks → SOUL.md Section 3.5 matches trigger keywords:

| Keyword pattern | File |
|----------------|------|
| "I like...", "I prefer...", "Your tone should be..." | `user-memory/preferences.md` |
| "I am...", "My name is...", "I work as..." | `user-memory/user-profile.md` |
| "My system is...", "I use...", "I installed..." | `user-memory/environment-setup.md` |
| "My steps are...", "First I do X, then Y..." | `user-memory/workflows/<name>.md` |

Write protocol: `read_file → merge → write_file → read_file verify`

### Skill Lifecycle

```
New skill on disk → maintain.py detects
  → Auto-fixes SKILL.md (adds frontmatter if missing)
  → Registers in user_capabilities.json
  → Agent fills in triggers
  → Skill is matchable

Skill deleted → maintain.py detects → unregisters from registry
```

### Trigger Matching

```
User speaks → capability_finder.py
  → Scores: exact=100, contains=50, contained=10
  → Returns best match
    → "skill" → execute script
    → "direct_answer" → agent responds
```

---

## Directory Structure

```
~/.hermes/
├── SOUL.md                            ← Governance rules (read-only anchor)
├── skills/
│   ├── auto-generated/                ← Agent self-learned skills
│   │   ├── self_created_skills.json   ← Manifest
│   │   └── <skill-name>/
│   ├── user-created/                  ← User-defined skills
│   │   └── <skill-name>/
│   └── <category>/                    ← Bundled skills
├── user-memory/                       ← Structured persistence
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

Scans `auto-generated/` and `user-created/`. Detects new/deleted skills, syncs registry, auto-fixes SKILL.md, validates triggers and script paths.

```bash
~/.hermes/hermes-agent/venv/bin/python \
  ~/.hermes/skills/user-created/skill-maintenance/scripts/maintain.py
```

### capability_finder.py

Matches user input to registered skills using scoring algorithm.

```bash
~/.hermes/hermes-agent/venv/bin/python \
  ~/.hermes/user-registry/capability_finder.py "generate image"
```

---

## Testing

```bash
python3 framework/skills/user-created/skill-maintenance/test_maintain.py
```

11 tests: empty directory, new skill detection, SKILL.md auto-fix, registry sync, deletion, idempotency, manifest detection, mixed skills, validation — **all passing**.

---

## Design Principles

1. **Single source of truth** — SOUL.md is the only governance file
2. **Read-before-write** — prevents data corruption
3. **Separated concerns** — auto-generated, user-created, bundled skills
4. **Non-destructive** — script never modifies user-created skills
5. **Audit trail** — all changes logged with snapshots

---

## Known Limitations

- **Agent discipline** — SOUL.md ensures rules are read, not guaranteed to be followed. Works today; may vary with different models.
- **Gateway privacy** — no `user_id` isolation in `session_search`. Mitigate with `allowed_chats` whitelist.
- **Skill classification** — heuristic-based (session references, file size). Works for current patterns; may need adjustment.

---

## License

MIT
