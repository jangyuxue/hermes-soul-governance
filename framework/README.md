# Framework Template

Copy to `~/.hermes/`:

```bash
cp -r * ~/.hermes/
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
│   ├── preferences.md               ← Agent auto-fills
│   ├── user-profile.md              ← Agent auto-fills
│   ├── environment-setup.md         ← Agent auto-fills
│   └── workflows/                   ← Agent auto-fills
├── user-registry/
│   ├── user_capabilities.json       ← All skill entries
│   └── capability_finder.py         ← Trigger matcher
└── skills/
    ├── auto-generated/              ← Agent's skills
    │   └── self_created_skills.json ← Manifest
    └── user-created/
        └── skill-maintenance/       ← Maintenance tool
            ├── scripts/maintain.py  ← Run this
            ├── README.md
            └── test_maintain.py
```
