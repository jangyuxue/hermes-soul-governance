# Framework Template

Copy to `~/.hermes/`:

```bash
# Deploy core components (from repository root)
cp framework/SOUL.md ~/.hermes/SOUL.md
cp -r framework/user-memory ~/.hermes/
cp -r framework/user-registry ~/.hermes/
cp -r framework/skills/user-created ~/.hermes/skills/

# Create output directories
mkdir -p ~/.hermes/output/{images,documents,data,temp}
```

Then configure and run (see main README):

```bash
vim ~/.hermes/SOUL.md              # Set role and language (Section 1)
hermes config set memory.memory_enabled false
hermes config set memory.user_profile_enabled false
~/.hermes/hermes-agent/venv/bin/python \
  ~/.hermes/skills/user-created/skill-maintenance/scripts/maintain.py
```

> **Or from within framework/:** `cd framework/` then run `cp SOUL.md ~/.hermes/SOUL.md`, etc. (same relative paths, no `framework/` prefix needed).

## What's Included

```
~/.hermes/
├── SOUL.md                          ← Edit Section 1 (role, language)
├── user-memory/
│   ├── README.md                    ← Trigger keyword reference
│   ├── preferences.md               ← Agent auto-fills
│   ├── user-profile.md              ← Agent auto-fills
│   ├── environment-setup.md         ← Agent auto-fills
│   └── workflows/
│       ├── README.md
│       └── workflow-commands.json   ← Machine-readable steps
├── user-registry/
│   ├── README.md
│   ├── user_capabilities.json       ← All skill entries
│   └── capability_finder.py         ← Trigger matcher
├── skills/
│   ├── auto-generated/              ← Agent's skills (lifecycle tracked in registry)
│   │   └── README.md
│   └── user-created/
│       ├── README.md
│       └── skill-maintenance/       ← Maintenance tool
│           ├── README.md
│           ├── SKILL.md
│           ├── scripts/
│           │   ├── maintain.py     ← Run this
│           │   └── test_maintain.py ← 9 test cases (local-only)
│           └── .history/            ← Registry snapshots (auto-created)
└── output/
    ├── README.md
    ├── images/
    ├── documents/
    ├── data/
    └── temp/
```
