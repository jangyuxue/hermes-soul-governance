# Contributing to SOUL.md Governance Framework

First off, thanks for considering contributing! This project aims to solve real architectural problems in Hermes Agent, and every bit of help improves the ecosystem.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How to Contribute](#how-to-contribute)
  - [Reporting Bugs](#reporting-bugs)
  - [Suggesting Enhancements](#suggesting-enhancements)
  - [Pull Requests](#pull-requests)
- [Development Setup](#development-setup)
- [Running Tests](#running-tests)
- [Coding Guidelines](#coding-guidelines)
- [Commit Convention](#commit-convention)

## Code of Conduct

This project is governed by the [Contributor Covenant](https://www.contributor-covenant.org/). Be respectful, constructive, and assume good faith.

## How to Contribute

### Reporting Bugs

Open an issue with:

1. A clear title describing the bug
2. Steps to reproduce (what you did, what you expected, what actually happened)
3. Your Hermes Agent version (`hermes --version` or the commit hash of your installation)
4. Whether you deployed the framework or are reading it as documentation

### Suggesting Enhancements

Open an issue with:

1. What you want to achieve (the problem, not your proposed solution)
2. Why the current approach doesn't cover it
3. Any prior art or references (optional but helpful)

### Pull Requests

1. Fork the repository
2. Create a branch from `main` with a descriptive name: `fix/maintain-typo`, `feat/export-format`, `docs/quickstart-gif`
3. Make your changes
4. Run tests (see below)
5. Open a PR against `main`
6. Keep PRs focused — one change per PR

## Development Setup

```bash
# Clone the repo
git clone https://github.com/jangyuxue/hermes-soul-governance.git
cd hermes-soul-governance

# No external dependencies required for core infrastructure
# The Python scripts target >= 3.8 stdlib only

# For testing the maintain.py script specifically against a Hermes environment:
# Set HERMES_HOME to your ~/.hermes/ path (optional, defaults to ~/.hermes/)
export HERMES_HOME=~/.hermes
```

## Running Tests

```bash
# From the repository root
python3 framework/skills/user-created/skill-maintenance/test_maintain.py
```

All 11 tests should pass. If they don't, check whether your Hermes Agent installation path differs from the default (`~/.hermes/`).

## Coding Guidelines

### For Python (`maintain.py`, `capability_finder.py`)

- Target Python 3.8+ (stdlib only — no external dependencies)
- Use `pathlib.Path` for filesystem operations, not `os.path`
- Use `subprocess.run` with `check=True` for shell calls, capture output via `capture_output=True`
- Type hints are encouraged but not enforced
- Format: loosely follow PEP 8 (use `black` if you like, but not required)

### For Shell scripts

- Prefer Python over bash for logic-heavy scripts
- If you must use bash, enable `set -euo pipefail`

### For Markdown (`README.md`, `SOUL.md`)

- Keep line length under 100 characters where practical
- Use fenced code blocks with language annotations
- Mermaid diagrams are preferred over static images for architecture flows (they render natively on GitHub)

## Commit Convention

Use conventional commits:

```
<type>: <brief description>

<optional body>
```

Types:

| Type     | When to use                          |
|----------|--------------------------------------|
| `feat`   | New functionality                    |
| `fix`    | Bug fix                              |
| `docs`   | Documentation changes (README, etc.) |
| `style`  | Formatting, linting, no logic change |
| `refactor`| Code restructuring, no behavior change |
| `test`   | Adding or fixing tests               |
| `chore`  | Build, CI, tooling                   |

Examples:

```
docs: add Mermaid architecture diagram to README
fix: handle missing SKILL.md in empty auto-generated directory
feat: add export script for memory files
```

## What Needs Help

Check the [Issues](https://github.com/jangyuxue/hermes-soul-governance/issues) tab for open items. If you're looking for ideas:

- [ ] Translation: add README in other languages (Japanese, Korean, Spanish)
- [ ] GIF/asciicast demo of deployment workflow
- [ ] Integration test that deploys framework to a test Hermes installation end-to-end
- [ ] VS Code / Neovim config integration (auto-generate SOUL.md from editor)
- [ ] Comparison with other Hermes Agent memory alternatives

---

**Thank you for contributing!**
