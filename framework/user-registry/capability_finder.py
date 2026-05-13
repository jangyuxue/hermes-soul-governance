import json
from pathlib import Path

REGISTRY_PATH = Path.home() / ".hermes" / "user-registry" / "user_capabilities.json"
COMMANDS_PATH = Path.home() / ".hermes" / "user-memory" / "workflows" / "workflow-commands.json"

# Fallback candidates if primary path missing
COMMANDS_FALLBACKS = [
    Path.home() / ".hermes" / "workflow-commands.json",
    Path.home() / ".hermes" / "user-memory" / "workflow-commands.json",
]


def load_registry():
    """Load user capabilities registry."""
    if not REGISTRY_PATH.exists():
        return {"capabilities": []}
    with open(REGISTRY_PATH) as f:
        return json.load(f)


def load_workflow_commands():
    """Load workflow commands with fallback paths."""
    for path in [COMMANDS_PATH] + COMMANDS_FALLBACKS:
        if path.exists():
            with open(path) as f:
                return json.load(f)
    return {}


def _score(query_lower: str, trigger: str) -> int:
    """Score a trigger against query.

    Returns:
        100: exact match
        50:  trigger contained in query
        10:  query contained in trigger
        0:   no match
    """
    t = trigger.lower().strip()
    if t == query_lower:
        return 100
    if t in query_lower:
        return 50
    if query_lower in t:
        return 10
    return 0


def find_capability(query: str):
    """Find matching capability or workflow by trigger words.

    Scoring:
    - exact match: 100
    - trigger in query: 50
    - query in trigger: 10

    Returns highest-scoring match with unified format:
    {"type": "skill|workflow", "id": "...", "data": {...}}
    """
    query_lower = query.lower().strip()
    best_score = 0
    best_result = None

    # Search user capabilities
    registry = load_registry()
    for cap in registry.get("capabilities", []):
        cap_id = cap.get("id", "")
        for trigger in cap.get("triggers", []):
            score = _score(query_lower, trigger)
            if score > best_score:
                best_score = score
                best_result = {"type": "skill", "id": cap_id, "data": cap}

    # Search workflow commands
    commands = load_workflow_commands()
    for wf_id, wf in commands.get("workflows", {}).items():
        for trigger in wf.get("trigger_phrases", []):
            score = _score(query_lower, trigger)
            if score > best_score:
                best_score = score
                best_result = {"type": "workflow", "id": wf_id, "data": wf}

    if best_result is None:
        return {"type": "direct_answer", "id": "default", "data": {"note": "No matching skill or workflow. Use direct_answer."}}
    return best_result


def get_capability_by_id(cap_id: str):
    """Get capability by ID."""
    registry = load_registry()
    for cap in registry.get("capabilities", []):
        if cap["id"] == cap_id:
            return cap
    return None


def list_capabilities():
    """List all user capabilities and workflows."""
    registry = load_registry()
    commands = load_workflow_commands()
    return {
        "skills": registry.get("capabilities", []),
        "workflows": list(commands.get("workflows", {}).keys())
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        result = find_capability(query)
        if result:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print("No matching capability or workflow found")
    else:
        all_items = list_capabilities()
        print(f"Skills: {len(all_items['skills'])}")
        for cap in all_items["skills"]:
            print(f"  - {cap['id']}: {cap['name']}")
        print(f"Workflows: {len(all_items['workflows'])}")
        for wf in all_items["workflows"]:
            print(f"  - {wf}")
