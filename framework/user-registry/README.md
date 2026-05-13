# user-registry

Custom skill management. See SOUL.md Section 6-7.

| File | Purpose |
|------|---------|
| `user_capabilities.json` | Skill registry: triggers, script paths, dependencies |
| `capability_finder.py` | Trigger word matcher (run by agent automatically) |

`capability_finder.py` is invoked by SOUL.md Section 6.1. It reads `user_capabilities.json`, scores user input against registered triggers, and returns the best matching skill. No manual modification needed.
