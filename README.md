<p align="center">
  <br>
  <b>SOUL.md Governance Framework</b><br>
  <i>Replacing Hermes Agent's fragile memory compression cycle with an immutable governance layer.</i>
</p>

<p align="center">
  <a href="https://github.com/jangyuxue/hermes-soul-governance/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="MIT License"></a>
  <a href="#"><img src="https://img.shields.io/badge/python-3.8%2B-blue" alt="Python 3.8+"></a>
  <a href="#"><img src="https://img.shields.io/badge/tests-9%20passing-brightgreen" alt="Tests Passing"></a>
  <a href="https://github.com/jangyuxue/hermes-soul-governance/stargazers"><img src="https://img.shields.io/github/stars/jangyuxue/hermes-soul-governance?style=social" alt="Stars"></a>
</p>

<p align="center">
  <img src="docs/assets/architecture.svg" width="900" alt="SOUL.md Architecture Comparison: Native Memory vs SOUL.md Governance">
</p>

> **Hermes Agent's native `MEMORY.md` has a 2200-character limit and auto-compression loop that silently discards context.**
> SOUL.md replaces it with a **read-only governance anchor** + **structured file persistence** — no compression, no data loss.

## 30-Second Quick Start

```bash
# 0. Get the framework files
git clone https://github.com/jangyuxue/hermes-soul-governance.git
cd hermes-soul-governance

# 1. Deploy core components to ~/.hermes/
cp framework/SOUL.md ~/.hermes/SOUL.md
cp -r framework/user-memory ~/.hermes/
cp -r framework/user-registry ~/.hermes/
cp -r framework/skills/user-created ~/.hermes/skills/

# 2. Configure your role and language
vim ~/.hermes/SOUL.md
#    → Section 1: Replace <YOUR_ROLE> and <YOUR_LANGUAGE>

# 3. Disable Hermes native memory system
hermes config set memory.memory_enabled false
hermes config set memory.user_profile_enabled false

# 4. Run maintenance script to sync skill registry
~/.hermes/hermes-agent/venv/bin/python \
  ~/.hermes/skills/user-created/skill-maintenance/scripts/maintain.py
```

⚠️ **Read the per-directory READMEs to understand what goes where:**
- `~/.hermes/user-memory/` → structured memory files (preferences, profile, etc.)
- `~/.hermes/user-registry/` → skill capability discovery
- `~/.hermes/skills/` → skill scripts and maintenance (auto-generated kept intact)
- `~/.hermes/output/` → agent file output directories

[Full deployment guide →](#quick-start)

---

## Prerequisites

This framework is designed for **Hermes Agent**. You must have Hermes Agent installed and working before using this framework.

Files referenced throughout the framework assume the default Hermes installation path:

```
~/.hermes/
├── hermes-agent/           ← Source code
│   └── venv/bin/python     ← Python interpreter used by scripts
├── config.yaml             ← Configuration
└── SOUL.md                 ← This framework (adds this file)
```

If your installation uses a different path, adjust the Python interpreter path in scripts accordingly.

---

## Background

### 1.1 Memory System Defects

Hermes Agent stores persistent memory in two files: `MEMORY.md` (2200-character limit) and `USER.md` (1375-character limit). When either file reaches capacity, the system triggers an automatic compression cycle — merging existing entries, discarding context, and rewriting the file to free space. This process repeats each time the file fills again.

Over multiple cycles, the following issues manifest:

- **No category separation** — preferences, environment configuration, workflow notes, and system auto-summaries occupy the same file without structural partitioning.
- **No priority retention** — compression treats all entries equally. Recent and outdated information are merged or discarded without differentiation.
- **No write-time rule enforcement** — the agent writes via tool calls that do not read file contents beforehand. Rules defined inside `MEMORY.md` or `USER.md` are only evaluated when the file is full and compression is required, which is not a reliable enforcement point.
- **Context degradation** — the compressed output, when injected into the system prompt across sessions, reduces response coherence and increases debugging overhead.

These issues are architectural: the files are both writable and auto-injected. Any rules placed inside them can be overwritten or ignored at write time.

### 1.2 Skill System Limitations

Hermes Agent's built-in system prompt includes the following instruction:

> *"After completing a complex task (5+ tool calls), fixing a tricky error, or discovering a non-trivial workflow, save the approach as a skill with skill_manage."*

This mechanism opens a creation path but provides no corresponding maintenance infrastructure:

- **No expiry or deprecation** — once created, skills persist on disk indefinitely.
- **No quality validation** — malformed or empty skills are accepted without checks.
- **No duplicate detection** — newly created skills are not compared against existing ones for overlap.
- **No auto-registration** — created skills are not added to `user_capabilities.json`. The trigger matching system (`capability_finder.py`) cannot discover them.

The result is a unidirectional pipeline: creation without maintenance. Skills accumulate, quality degrades, and the registry becomes increasingly out of sync with what is on disk.

### 1.3 Scope of This Framework

This framework addresses the two problems described above. It provides infrastructure for:

- Disabling the default memory system and replacing it with file-based, categorized persistence
- Automating skill registration, validation, cleanup, and merge detection
- Maintaining a trigger-based skill retrieval system

---

## SOUL.md — The Core File

### What Makes SOUL.md Different

`~/.hermes/SOUL.md` is the central file of this framework. It has two properties that distinguish it from `MEMORY.md` and `USER.md`:

| Property | `MEMORY.md` / `USER.md` | `SOUL.md` |
|----------|------------------------|-----------|
| Injection | Auto-injected (configurable) | Auto-injected (no toggle) |
| Write path | Agent can write via `memory()` | **No write function exists** |
| Character limit | 2200 / 1375 | Unlimited |
| Priority in prompt | After system prompt | **First** (`prompt_parts[0]`) |

Because SOUL.md has **no write function** in the codebase, the agent cannot modify it through any tool call. This makes it a read-only anchor: rules defined here persist across sessions and cannot be overwritten by memory operations.

The native memory system (`MEMORY.md` / `USER.md`) is disabled via configuration:

```yaml
# config.yaml
memory:
  memory_enabled: false
  user_profile_enabled: false
```

### Section-by-Section Guide

#### Section 1: Identity & Role

Defines the agent's persona. **You must edit this section** after deploying:

```markdown
1.1 Role: <YOUR_ROLE>
# Example: "Backend Engineer", "Data Scientist", "Senior Developer"

1.2 Language: <YOUR_LANGUAGE>
# Example: "English", "Chinese (中文)"
```

#### Section 2: Response Standards

Quality constraints on agent output:
- Must end with a genuine question (no "is that correct?")
- Must cite evidence (check files before answering)
- Mode switching: exploration (brainstorm) vs execution (precise commands)

Chinese example keywords are included because this framework was originally developed for a Chinese-speaking user. Replace with your language as needed.

#### Section 3: Persistence — Write Protocol

**This is the core of the memory system.** It defines:

- **3.1**: When to write (user says "remember", states a preference, corrects a fact)
- **3.2**: How to write (`write_file` only, never `memory()`)
- **3.3-3.4**: Read-before-write enforcement (prevents data corruption)
- **3.5**: Trigger keyword matching (maps user input to specific files)
- **3.5.1**: The keyword-to-file mapping table:

```
"I like...", "I prefer..."         → user-memory/preferences.md
"I am...", "My name is..."         → user-memory/user-profile.md
"My system is...", "I use..."      → user-memory/environment-setup.md
"My steps for..."                  → user-memory/workflows/<name>.md
"Add a skill", "Register"          → user-registry/user_capabilities.json
```

This replaces the default memory system with structured, categorized files.

#### Section 4: Retrieval Protocol

Defines how the agent reads your stored information:
- Search-first: keyword match via `search_files`, only read matching paragraphs
- On-demand: never load all `user-memory/` files at once
- Freshness rule: always read from file, never from session context memory

#### Section 5: Operational Constraints

Rules for file operations:
- **5.1**: Backup before modification (to `user-memory/.backup/`)
- **5.3**: Protected directories (no deletion under `skills/`, `output/`, `memories/`)
- **5.4**: Output goes to `~/.hermes/output/{images|documents|data|temp}/`
- **5.5**: **Important** — All Python operations must use `~/.hermes/hermes-agent/venv/bin/python`, not system `python3`. This venv contains the required dependencies (httpx, openai, etc.). System Python is externally managed on some distributions and will fail.

#### Section 6: Skill Dispatch

How the agent routes user requests to registered skills:

```
User input → capability_finder.py → user_capabilities.json
  → Match found → execute skill script
  → No match → agent responds directly
```

`capability_finder.py` lives at `~/.hermes/user-registry/capability_finder.py`. It scores triggers: exact match (100), trigger in query (50), query in trigger (10).

#### Section 7: Skill Creation & Storage

Defines where skills live and how they're maintained:

| Type | Location | Created by | Maintained by |
|------|----------|------------|--------------|
| Auto-generated | `auto-generated/` | Agent (after complex tasks) | `maintain.py` + agent |
| User-created | `user-created/` | User | `maintain.py` (registry only) |

The maintenance script (`maintain.py`) at `~/.hermes/skills/user-created/skill-maintenance/scripts/maintain.py` runs four phases in sequence, then saves a registry snapshot:

| Phase | What it does |
|-------|-------------|
| [Orphan] | Scans category directories, migrates misplaced non-bundled skills to `auto-generated/`, registers and tracks them in one pass |
| [Sync] | Compares `auto-generated/` disk against registry lifecycle fields: detects new/deleted/revived skills, auto-syncs `description` changes from SKILL.md to registry |
| [Reg] | Checks `user-created/` registry consistency — adds missing entries, removes deleted ones. Never modifies skill content |
| [Check] | Validates registry entries (empty triggers, broken paths), auto-fixes malformed SKILL.md (auto-generated only), and detects merge candidates via 5-axis scoring (name, content keywords, heading structure, cross-references, file layout) with three-layer anti-false-positive gates |
| [Snapshot] | Saves a timestamped copy of `user_capabilities.json` to `.history/` for change audit and rollback reference |

#### Section 8: Compliance & Audit

Enforcement rules:
- Every write must be verified (post-write `read_file`)
- Failed writes must be reported and restored from backup
- Any deviation from these rules must be reported immediately

---

## Quick Start

```bash
# ============================================
# STEP 0: GET THE FRAMEWORK
# ============================================
# Download the repository to your machine
git clone https://github.com/jangyuxue/hermes-soul-governance.git

# Enter the project directory
cd hermes-soul-governance

# ============================================
# STEP 1: DEPLOY TO ~/.hermes/
# ============================================
# Prerequisite: Hermes Agent must already be installed at ~/.hermes/

# 1a. Deploy SOUL.md (the governance anchor - replaces default)
cp framework/SOUL.md ~/.hermes/SOUL.md

# 1b. Deploy user-memory/ (categorized memory files)
#     Creates: preferences.md, user-profile.md, environment-setup.md, workflows/
#     Read: cat ~/.hermes/user-memory/README.md
cp -r framework/user-memory ~/.hermes/

# 1c. Deploy user-registry/ (capability discovery system)
#     Creates: capability_finder.py, user_capabilities.json
#     Read: cat ~/.hermes/user-registry/README.md
cp -r framework/user-registry ~/.hermes/

# 1d. Merge skills/ - only user-created/ content
#     IMPORTANT: Does NOT touch auto-generated/ (your existing skills are safe)
#     Read: cat ~/.hermes/skills/user-created/skill-maintenance/README.md
cp -r framework/skills/user-created ~/.hermes/skills/

# 1e. Create output/ directories (agent file output locations)
mkdir -p ~/.hermes/output/{images,documents,data,temp}

# ============================================
# STEP 2: POST-DEPLOY CONFIGURATION
# ============================================

# 2a. Edit SOUL.md — replace placeholders in Section 1
vim ~/.hermes/SOUL.md
#    1.1 Role: <YOUR_ROLE>       → "Backend Engineer"
#    1.2 Language: <YOUR_LANGUAGE> → "English"

# 2b. Disable Hermes default memory system
#     MEMORY.md and USER.md remain on disk (harmless) but are no longer used
hermes config set memory.memory_enabled false
hermes config set memory.user_profile_enabled false
#
#     If hermes CLI is unavailable, edit config.yaml directly:
#     vim ~/.hermes/config.yaml
#     Add:
#       memory:
#         memory_enabled: false
#         user_profile_enabled: false

# 2c. Run maintenance script to register and sync all skills
~/.hermes/hermes-agent/venv/bin/python \
  ~/.hermes/skills/user-created/skill-maintenance/scripts/maintain.py

# 2d. Verify everything is in sync
~/.hermes/hermes-agent/venv/bin/python \
  ~/.hermes/skills/user-created/skill-maintenance/scripts/maintain.py
# Expected output: "No changes" — all skills registered and synced
```

---

## Repository Contents

```
hermes-soul-governance/
├── README.md                    # This file
├── README_CN.md                 # Chinese version
├── SOUL.md                      # Governance rules (core of the framework)
├── RELEASE_NOTE_v1.0.0.md       # v1.0.0 release notes
├── RELEASE_NOTE_v1.1.0.md       # v1.1.0 release notes
├── RELEASE_NOTE_v2.0.0.md       # v2.0.0 release notes
├── CONTRIBUTING.md              # Contribution guide
├── .gitignore
├── docs/
│   └── assets/
│       └── architecture.svg     # Architecture comparison diagram
├── framework/                   # Deployable template — copy to ~/.hermes/
│   ├── README.md                # Quick reference for each directory
│   ├── SOUL.md                  # Same as root SOUL.md (with placeholders)
│   ├── user-memory/             # Categorized memory storage
│   │   ├── README.md            # File descriptions and trigger keywords
│   │   ├── preferences.md       # Communication style, habits
│   │   ├── user-profile.md      # Identity, role
│   │   ├── environment-setup.md # Toolchain, paths
│   │   ├── .backup/             # Auto-created before each write
│   │   └── workflows/
│   │       ├── README.md
│   │       └── workflow-commands.json  # Machine-readable steps
│   ├── user-registry/           # Capability discovery system
│   │   ├── README.md
│   │   ├── user_capabilities.json
│   │   └── capability_finder.py
│   ├── skills/                  # Skill management
│   │   ├── auto-generated/
│   │   │   └── README.md
│   │   └── user-created/
│   │       ├── README.md
│   │       └── skill-maintenance/
│   │           ├── README.md
│   │           ├── SKILL.md
│   │           ├── scripts/
│   │           │   └── maintain.py    # Auto-register/validate/clean/merge-detect skills
│   └── output/                  # Agent output directories
│       ├── README.md
│       ├── images/
│       ├── documents/
│       ├── data/
│       └── temp/
└── examples/
    └── user_capabilities.json    # Example with lifecycle field
```

---

## Known Limitations

1. **Rule enforcement** — SOUL.md ensures rules are present in the system prompt, but compliance depends on model instruction-following capability. This is inherent to LLM-based systems.

2. **Merge detection is heuristic** — The 5-axis scoring identifies content overlap, but does not understand semantics. False positives are possible; always review candidates manually before merging. The three-layer gate (zero content, Jaccard < 0.15, < 2 axes) eliminates most coincidental matches but cannot guarantee zero errors.

3. **Skill classification** — The maintenance script uses heuristic criteria (session reference files, reference count, file size) to classify auto-generated skills. These heuristics match current generation patterns but may require adjustment.

---

## License

MIT
