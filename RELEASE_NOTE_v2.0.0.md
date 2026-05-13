## v2.0.0 — Merge Detection Rigor Enhancement (2026-05-13)

### Bugfixes

| Bug | Impact | Fix |
|-----|--------|-----|
| `.split("_")` in name tokenization | All hyphenated skill names (e.g. `hermes-agent-setup`) treated as single tokens — merge detection effectively broken for ALL skills | `.split()` (whitespace) correctly produces `["hermes", "agent", "setup"]` |

### New Features

| Feature | Description |
|---------|-------------|
| [Check] 5-axis merge scoring | Name (+0.20), content keywords (+0.30), heading structure (+0.10), cross-refs (+0.20), file structure (+0.05) |
| Jaccard anti-false-positive gates | 3 layers: zero-content skip / Jaccard<0.15 skip / <2 axes skip |
| Description field extraction | Keyword extraction from `description:` frontmatter (stopword-filtered) |
| `get_skill_headings()` | New helper: extracts ## headings for structure comparison |
| `get_skill_related()` | New helper: parses `related_skills:` from frontmatter |
| SOUL.md 3.6 PRIORITY OVERRIDE | MUST/PROHIBITED rules take precedence over framework system prompt memory suggestions |

### Calibration

28 pairwise combinations tested against 8 real auto-generated skills:

| Configuration | Candidates | False Positives | Valid |
|---|---|---|---|
| Original (no gates) | 28 | 27 | 1 |
| + body keyword removal | 4 | 3 | 1 |
| + Jaccard 0.15 gate | 1 | 0 | 1 |
| **+ 5-axis scoring (final)** | **1** | **0** | **1** |

The single valid candidate: `hermes-agent-setup ↔ hermes-environment-troubleshooting`
(score=0.8, axes=[content+fstruct+name+xref], evidence from 4/5 dimensions).

### Documentation

- SKILL.md rewritten from 289-line implementation doc to 209-line usage guide
- Pitfalls trimmed from 12 to 7 (code conventions moved to reference files)
- Execution flow sections ([Orphan]/[Sync]/[Check]) rewritten as "output reading guides"
- Added reference: `session-2026-05-13-merge-rigor-enhancement.md`
- framework/README.md path commands fixed (`cp SOUL.md` → `cp framework/SOUL.md`)
- Test badge updated: 8 → 9 passing
- Duplicate `test_maintain.py` removed from skill root

### Quick Start

```bash
git clone https://github.com/jangyuxue/hermes-soul-governance.git
cd hermes-soul-governance
cp framework/SOUL.md ~/.hermes/SOUL.md
cp -r framework/user-memory ~/.hermes/
cp -r framework/user-registry ~/.hermes/
cp -r framework/skills/user-created ~/.hermes/skills/
# Edit Section 1 in ~/.hermes/SOUL.md, then:
hermes config set memory.memory_enabled false
~/.hermes/hermes-agent/venv/bin/python \
  ~/.hermes/skills/user-created/skill-maintenance/scripts/maintain.py
```

### License

MIT
