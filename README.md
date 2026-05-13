<p align="center">
  <br>
  <b>SOUL.md Governance Framework</b><br>
  <i>A structured governance layer for Hermes Agent — replacing default memory with file-based persistence and automated skill lifecycle management.</i>
</p>

<br>

---

## Background

Hermes Agent stores persistent data through two mechanisms:

1. **`MEMORY.md` / `USER.md`** — each capped at 2200 and 1375 characters respectively. When capacity is exhausted, the system automatically compresses existing content by merging facts, discarding context, and rewriting entries. Over successive cycles, these files accumulate mixed-priority, unstructured data — preferences, environment configurations, workflow notes, and system auto-summaries — without separation by category or retention policy. The resulting content, when injected into the system prompt, degrades response coherence and increases maintenance overhead.

2. **Auto-generated skills** — after completing tasks involving multiple tool calls, the agent is instructed to preserve the approach as a skill. However, the system provides no expiration policy, quality validation, duplicate detection, or auto-registration mechanism. Skills accumulate on disk without entering `user_capabilities.json`, rendering them unreachable by the trigger matching system.

These issues stem from a common root cause: rules written inside writable files (`MEMORY.md`, `USER.md`) cannot be enforced at write time. The agent writes through tool calls that bypass file content entirely — it never reads the file before writing. Rules only take effect when the file is full and the system reads it to compress, which is not a reliable enforcement point.

SOUL.md (`~/.hermes/SOUL.md`) provides a different injection path — unconditional loading at session start, with no corresponding write function in the codebase. This makes it a read-only anchor that cannot be overwritten by the memory system.

---

## Solution Architecture

### Layer 1: SOUL.md — Read-Only Rule Anchor

SOUL.md is loaded automatically every turn via `load_soul_md()`, placed at `prompt_parts[0]` (highest priority). The system has no write path for this file. Rules defined here cannot be modified by memory operations.

The file defines:
- Write protocol: read → merge → write → verify (Section 3)
- Keyword-to-file mapping for structured persistence (Section 3.5.1)
- Search-first retrieval, on-demand loading (Section 4)
- Skill creation triggers and storage paths (Section 7)

Native memory is disabled via configuration:

```yaml
memory:
  memory_enabled: false
  user_profile_enabled: false
```

This prevents `MEMORY.md` and `USER.md` from being injected or written to.

### Layer 2: user-memory/ — File-Based Persistence

Replaces `MEMORY.md` / `USER.md` with categorized, unlimited-capacity files:

| Path | Content | Read Trigger |
|------|---------|-------------|
| `user-memory/preferences.md` | Communication style, tone, habits | User references preferences |
| `user-memory/user-profile.md` | Identity, role, domain, skills | Task requires user context |
| `user-memory/environment-setup.md` | Toolchain, paths, installed packages | Execution requires environment |
| `user-memory/workflows/<name>.md` | Step-by-step procedures | Specific workflow triggered |

These files are not auto-injected into the system prompt. They are loaded on demand via `read_file` / `search_files`. Most turns consume zero context window for memory. File size is bounded only by disk capacity, not by the 2200/1375 character limit.

Write protocol (Section 3.3-3.4):
1. Before writing: verify file existence via `search_files` or `read_file`
2. If file exists: read full content → merge new content → write merged result
3. If file does not exist: write directly
4. After writing: `read_file` to confirm content integrity

### Layer 3: user-registry/ — Skill Registry

Custom skills require explicit registration to be reachable by the trigger matching system. Three components:

| Component | Function |
|-----------|----------|
| `user_capabilities.json` | Registry: skill ID, trigger words, script path, dependencies, examples, configuration |
| `capability_finder.py` | Matches user input against registered triggers using scoring (exact=100, substring=50, contained=10) |
| `workflow-commands.json` | Maps skill ID to machine-readable execution steps |

### Skill Maintenance (maintain.py)

Two directories, two behaviors:

**auto-generated/** — Agent-created skills after complex tasks.
- New on disk → add to `self_created_skills.json` manifest + register in `user_capabilities.json`
- Removed from disk → mark deleted in manifest + unregister from registry
- Malformed `SKILL.md` → auto-fix (add frontmatter, name, description)

**user-created/** — User-defined skills.
- New on disk → register in `user_capabilities.json`
- Removed from disk → unregister from registry
- Does not modify skill content

Validation checks (Section C):
- Empty triggers (skill registered but unreachable)
- Script path does not exist
- Malformed `SKILL.md` (auto-fixed with report)

---

## Quick Start

```bash
# 1. Deploy framework template
cp -r framework/* ~/.hermes/

# 2. Configure identity — edit ~/.hermes/SOUL.md Section 1
#    - Replace <YOUR_ROLE> with your role (e.g. "Backend Engineer")
#    - Replace <YOUR_LANGUAGE> with your language (e.g. "English", "中文")

# 3. Disable native memory
hermes config set memory.memory_enabled false
hermes config set memory.user_profile_enabled false

# 4. Run maintenance script to register existing skills
~/.hermes/hermes-agent/venv/bin/python \
  ~/.hermes/skills/user-created/skill-maintenance/scripts/maintain.py
```

---

## Repository Contents

```
hermes-soul-governance/
├── README.md                    # This file
├── README_CN.md                 # Chinese version
├── SOUL.md                      # Governance rules (single source of truth)
├── .gitignore                   # Excludes user data
├── framework/                   # Deployable template
│   ├── SOUL.md                  # Customizable rules (edit Section 1)
│   ├── user-memory/             # Structured persistence (agent auto-fills)
│   │   ├── preferences.md
│   │   ├── user-profile.md
│   │   ├── environment-setup.md
│   │   └── workflows/
│   ├── user-registry/
│   │   ├── user_capabilities.json
│   │   └── capability_finder.py
│   └── skills/
│       ├── auto-generated/      # Agent skills
│       │   └── self_created_skills.json
│       └── user-created/
│           └── skill-maintenance/
│               ├── scripts/maintain.py
│               ├── test_maintain.py
│               └── SKILL.md
├── examples/
│   ├── auto-generated/self_created_skills.json
│   └── user_capabilities.json
└── framework/skills/user-created/skill-maintenance/
    ├── scripts/maintain.py      # Maintenance script
    ├── test_maintain.py         # 11 test cases
    └── SKILL.md                 # Agent-facing documentation
```

---

## Testing

```bash
python3 framework/skills/user-created/skill-maintenance/test_maintain.py
```

Test suite: empty directory, new skill detection, SKILL.md auto-fix, registry synchronization, deletion unregistration, idempotency, manifest consistency, mixed skill types, validation warnings, clean state upon removal. **11 tests, all passing.**

---

## Known Limitations

1. **Rule enforcement** — SOUL.md ensures rules are loaded into the system prompt, but compliance depends on the model's ability to follow instructions. This is inherent to LLM-based systems and not unique to this framework.

2. **Skill classification** — The maintenance script identifies auto-generated skills using heuristic criteria (session reference files, reference count, file size, section count, presence of executable scripts). These heuristics match current generation patterns but may require adjustment if the agent's behavior changes.

3. **Gateway privacy** — When running behind a messaging gateway (Telegram, Feishu, etc.), `session_search` operates on the entire `state.db` without per-user isolation. This is an architectural limitation of Hermes Agent's single-user data model. Current mitigation: use `allowed_chats` to restrict access to trusted users. Not a substitute for proper multi-tenant isolation.

---

## License

MIT
