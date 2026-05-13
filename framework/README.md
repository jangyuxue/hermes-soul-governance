# Framework Template

Copy to `~/.hermes/`:

```bash
# Deploy core components (from the repository root)
cp SOUL.md ~/.hermes/SOUL.md
cp -r user-memory ~/.hermes/
cp -r user-registry ~/.hermes/
cp -r skills/user-created ~/.hermes/skills/

# Create output directories
mkdir -p ~/.hermes/output/{images,documents,data,temp}
```

Then configure and run (see main README):

```bash
vim ~/.hermes/SOUL.md              # Set role and language
hermes config set memory.memory_enabled false
~/.hermes/hermes-agent/venv/bin/python \
  ~/.hermes/skills/user-created/skill-maintenance/scripts/maintain.py
```

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
│   ├── auto-generated/              ← Agent's skills
│   │   ├── README.md
│   │   └── self_created_skills.json ← Manifest
│   └── user-created/
│       ├── README.md
│       └── skill-maintenance/       ← Maintenance tool
│           ├── README.md
│           ├── scripts/
│           │   └── maintain.py     ← Run this
│           ├── SKILL.md
└── output/
    ├── README.md
    ├── images/
    ├── documents/
    ├── data/
    └── temp/
```
