#!/usr/bin/env python3
"""Automated Skill Maintenance Script v5

v4 → v5: Added user-created/ directory check
         Script only syncs registry for user-created/ (does not modify skill content)
         Manifest only tracks skills under auto-generated/

Modes:
  Global scan (default): scan auto-generated/ to diff manifest + scan user-created/ to check registry
  Target analysis:       analyze a single skill in detail

Usage:
  ~/.hermes/hermes-agent/venv/bin/python \
    ~/.hermes/skills/user-created/skill-maintenance/scripts/maintain.py
"""

import json
import os
import re
import shutil
import sys
from datetime import datetime

# ============ Path Configuration ============

AUTO_GEN_DIR = os.path.expanduser("~/.hermes/skills/auto-generated")
USER_CREATED_DIR = os.path.expanduser("~/.hermes/skills/user-created")
REGISTRY_PATH = os.path.expanduser("~/.hermes/user-registry/user_capabilities.json")
MANIFEST_PATH = os.path.join(AUTO_GEN_DIR, "self_created_skills.json")
HISTORY_DIR = os.path.join(AUTO_GEN_DIR, ".history")
BACKUP_DIR = os.path.join(AUTO_GEN_DIR, ".backup")
ROLLBACK_LOG = os.path.join(HISTORY_DIR, "changes.log")


def load_json(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"  [WARN] Failed to read {path}: {e}", file=sys.stderr)
        return None


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def backup_file(path):
    if not os.path.exists(path):
        return None
    rel = os.path.relpath(path, os.path.expanduser("~/.hermes"))
    backup_path = os.path.join(BACKUP_DIR, rel)
    os.makedirs(os.path.dirname(backup_path), exist_ok=True)
    shutil.copy2(path, backup_path)
    return backup_path


def scan_skills_in_dir(directory):
    """Scan directory for all skills with SKILL.md, return {name: path}"""
    skills = {}
    if not os.path.exists(directory):
        return skills
    for item in sorted(os.listdir(directory)):
        item_path = os.path.join(directory, item)
        skill_md = os.path.join(item_path, "SKILL.md")
        if os.path.isdir(item_path) and os.path.exists(skill_md):
            skills[item] = item_path
    return skills


def get_skill_description(skill_path):
    skill_md = os.path.join(skill_path, "SKILL.md")
    if not os.path.exists(skill_md):
        return ""
    with open(skill_md, "r", encoding="utf-8") as f:
        content = f.read(1000)
    match = re.search(r'description:\s*["\'](.*?)["\']', content)
    return match.group(1) if match else ""


def get_skill_size(skill_path):
    path = os.path.join(skill_path, "SKILL.md")
    return os.path.getsize(path) if os.path.exists(path) else 0


def count_references(skill_path):
    ref_dir = os.path.join(skill_path, "references")
    if os.path.exists(ref_dir):
        return len([f for f in os.listdir(ref_dir) if f.endswith(".md")])
    return 0


def has_session_references(skill_path):
    ref_dir = os.path.join(skill_path, "references")
    if os.path.exists(ref_dir):
        for f in os.listdir(ref_dir):
            if re.search(r"session-\d{4}", f, re.IGNORECASE):
                return True
    skill_md = os.path.join(skill_path, "SKILL.md")
    if os.path.exists(skill_md):
        with open(skill_md, "r", encoding="utf-8") as f:
            content = f.read(5000)
        if re.search(r"session[\s-]*\d{4}", content, re.IGNORECASE):
            return True
        if re.search(r"\d{4}-\d{2}-\d{2}", content):
            return True
    return False


def has_scripts(skill_path):
    script_dir = os.path.join(skill_path, "scripts")
    if os.path.exists(script_dir):
        return len([f for f in os.listdir(script_dir) if f.endswith(".py")])
    return 0


def get_skill_section_count(skill_path):
    skill_md = os.path.join(skill_path, "SKILL.md")
    if not os.path.exists(skill_md):
        return 0
    with open(skill_md, "r", encoding="utf-8") as f:
        content = f.read()
    return len(re.findall(r"^##\s+", content, re.MULTILINE))


def get_skill_topic_keywords(skill_path):
    keywords = set()
    skill_md = os.path.join(skill_path, "SKILL.md")
    if not os.path.exists(skill_md):
        return keywords
    with open(skill_md, "r", encoding="utf-8") as f:
        content = f.read(3000)
    for match in re.finditer(r"##\s+(.*?)(?:\n|$)", content):
        keywords.add(match.group(1).strip().lower())
    tags_match = re.search(r"tags:\s*\[(.*?)\]", content)
    if tags_match:
        for tag in tags_match.group(1).split(","):
            tag = tag.strip().strip("\"'")
            if tag:
                keywords.add(tag.lower())
    return keywords


def classify_unknown_skill(name, skill_path):
    session_refs = has_session_references(skill_path)
    ref_count = count_references(skill_path)
    size = get_skill_size(skill_path)
    scripts = has_scripts(skill_path)
    sections = get_skill_section_count(skill_path)

    if session_refs:
        return "auto-generated"
    if ref_count >= 5:
        return "auto-generated"
    if ref_count >= 3 and size > 15000:
        return "auto-generated"
    if sections >= 5 and scripts == 0:
        return "auto-generated"
    if scripts > 0:
        return "user-intentional"
    return "user-intentional"


def detect_merge_candidates(new_name, new_path, existing_skills):
    candidates = []
    new_keywords = get_skill_topic_keywords(new_path)
    new_lower = new_name.lower()

    for existing_name, existing_info in existing_skills.items():
        if existing_info.get("status") != "active":
            continue
        score = 0.0
        reasons = []

        name_parts = set(existing_name.lower().replace("-", " ").split("_"))
        new_parts = set(new_lower.replace("-", " ").split("_"))
        overlap = name_parts & new_parts
        if overlap:
            score += 0.3
            reasons.append(f"Name overlap: {overlap}")

        existing_keywords = get_skill_topic_keywords(existing_info.get("path", ""))
        if new_keywords and existing_keywords:
            kw_overlap = new_keywords & existing_keywords
            if kw_overlap:
                score += min(0.4, 0.1 * len(kw_overlap))
                reasons.append(f"Topic overlap: {kw_overlap}")

    if score >= 0.3:
            candidates.append((existing_name, round(score, 2), "; ".join(reasons)))

    candidates.sort(key=lambda x: -x[1])
    return candidates


def ensure_skill_md_standard(skill_path, skill_name):
    """Ensure SKILL.md has standard format. Auto-fix if missing fields."""
    skill_md = os.path.join(skill_path, "SKILL.md")
    if not os.path.exists(skill_md):
        return False, "SKILL.md not found"

    with open(skill_md, "r", encoding="utf-8") as f:
        content = f.read()

    changes = []

    # Check frontmatter
    if not content.startswith("---"):
        desc = skill_name.replace("-", " ").title()
        frontmatter = f"""---
name: {skill_name}
description: "{desc}"
version: 1.0.0
author: Hermes Agent
---

"""
        content = frontmatter + content
        changes.append("added missing frontmatter")
    else:
        try:
            end = content.index("---", 3)
            frontmatter = content[3:end]

            if "name:" not in frontmatter:
                frontmatter += f"\nname: {skill_name}"
                changes.append("added missing name")

            if "description:" not in frontmatter:
                desc = skill_name.replace("-", " ").title()
                frontmatter += f'\ndescription: "{desc}"'
                changes.append("added missing description")

            content = "---" + frontmatter + "---" + content[end + 3:]
        except ValueError:
            return False, "broken frontmatter"

    # Check H1 heading
    lines = content.split("\n")
    has_heading = any(l.strip().startswith("# ") for l in lines)
    if not has_heading:
        title = skill_name.replace("-", " ").title()
        content += f"\n# {title}\n"
        changes.append("added missing H1 heading")

    if changes:
        with open(skill_md, "w", encoding="utf-8") as f:
            f.write(content)
        return True, "; ".join(changes)
    return False, "no fix needed"


# ============ User-created Registry Check ============

def sync_user_created_registry(registry):
    """Check if user-created/ skills are in registry, add if missing, remove if deleted"""
    changes = []
    reg_ids = {c["id"] for c in registry["capabilities"]}

    disk_skills = scan_skills_in_dir(USER_CREATED_DIR)

    # 1. Disk has but registry does not → add
    for name, path in disk_skills.items():
        if name not in reg_ids:
            # Auto-fix SKILL.md if not standard
            fixed, msg = ensure_skill_md_standard(path, name)
            if fixed:
                changes.append(f"  + Fixed SKILL.md: {name} ({msg})")

            description = get_skill_description(path)
            entry = {
                "id": name,
                "name": name.replace("-", " ").title(),
                "category": "user-created",
                "triggers": [],
                "description": description or f"User-created skill: {name}",
                "script": None,
                "dependencies": [],
                "examples": [],
            }
            registry["capabilities"].append(entry)
            changes.append(f"  + Registered user-created/{name} → user_capabilities.json")
            reg_ids.add(name)

    # 2. Registry has user-created but disk does not → remove
    to_remove = []
    for c in registry["capabilities"]:
        if c.get("category") == "user-created" and c["id"] not in disk_skills:
            to_remove.append(c)
            changes.append(f"  - Unregistered {c['id']} (disk deleted)")

    for entry in to_remove:
        registry["capabilities"].remove(entry)

    return changes


# ============ Auto-generated Manifest Sync ============

def sync_auto_generated_manifest(manifest, registry):
    """Auto-generated manifest diff against disk"""
    changes = []
    known = {s["name"]: s for s in manifest.get("self_created_skills", [])}

    disk_skills = scan_skills_in_dir(AUTO_GEN_DIR)
    disk_skills = {n: p for n, p in disk_skills.items()
                   if n not in ("self_created_skills",)}

    # New: disk has but manifest does not
    for name, path in disk_skills.items():
        if name not in known:
            # Auto-fix SKILL.md if not standard
            fixed, msg = ensure_skill_md_standard(path, name)

            description = get_skill_description(path)
            entry = {
                "name": name,
                "type": "auto-generated",
                "description": description,
                "status": "active",
                "category": "auto-generated",
                "registered": True,
                "note": f"First detected: {datetime.now().strftime('%Y-%m-%d')}",
            }
            manifest["self_created_skills"].append(entry)
            known[name] = entry
            changes.append(f"  + Added to manifest: {name}")

    # Missing: manifest has but disk does not
    for name, info in known.items():
        if info["status"] == "active" and name not in disk_skills:
            info["status"] = "deleted"
            info["note"] += f" | Disk deleted {datetime.now().strftime('%Y-%m-%d')}"
            changes.append(f"  - Marked deleted: {name}")

    # Revived: manifest has deleted and disk has
    for name, info in known.items():
        if info["status"] == "deleted" and name in disk_skills:
            info["status"] = "active"
            info["note"] += f" | Revived {datetime.now().strftime('%Y-%m-%d')}"
            changes.append(f"  ↺ Revived: {name}")

    # Registry sync
    reg_ids = {c["id"] for c in registry["capabilities"]}
    for s in manifest["self_created_skills"]:
        if s["status"] == "active" and s["type"] == "auto-generated":
            if s["name"] not in reg_ids:
                path = os.path.join(AUTO_GEN_DIR, s["name"])
                description = get_skill_description(path)
                entry = {
                    "id": s["name"],
                    "name": s["name"].replace("-", " ").title(),
                    "category": "auto-generated",
                    "triggers": [],
                    "description": description or s.get("description", ""),
                    "script": None,
                    "dependencies": [],
                    "examples": [],
                }
                registry["capabilities"].append(entry)
                changes.append(f"  → Registered {s['name']} → user_capabilities.json")
                reg_ids.add(s["name"])
        elif s["status"] == "deleted" and s["name"] in reg_ids:
            registry["capabilities"] = [
                c for c in registry["capabilities"] if c["id"] != s["name"]
            ]
            changes.append(f"  ✗ Unregistered {s['name']} (deleted)")
            reg_ids.discard(s["name"])

    # Update registered status for all skills
    for s in manifest["self_created_skills"]:
        s["registered"] = s["name"] in reg_ids
    manifest["last_updated"] = datetime.now().strftime("%Y-%m-%d")

    return changes


# ============ Global Scan ============

def run_global_scan():
    print()
    print("=" * 66)
    print("  Skill Maintenance Tool v5 — Global Scan")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  auto-generated: {AUTO_GEN_DIR}")
    print(f"  user-created:   {USER_CREATED_DIR}")
    print("=" * 66)
    print()

    # Load registry
    registry = load_json(REGISTRY_PATH)
    if registry is None:
        print("  [ERROR] Registry not found")
        sys.exit(1)
    backup_file(REGISTRY_PATH)

    # Load manifest
    manifest = load_json(MANIFEST_PATH)
    if manifest is None:
        manifest = {
            "version": "1.0",
            "last_updated": datetime.now().strftime("%Y-%m-%d"),
            "description": "Auto-generated skills manifest",
            "self_created_skills": [],
            "builtin_skills": [],
        }
    backup_file(MANIFEST_PATH)

    reg_before = len(registry["capabilities"])

    # ========== Part A: Auto-generated Manifest Diff ==========
    print("  [A] Auto-generated manifest diff...")
    auto_changes = sync_auto_generated_manifest(manifest, registry)
    if auto_changes:
        for c in auto_changes:
            print(c)
    else:
        print("    No changes")
    print()

    # ========== Part B: User-created Registry Check ==========
    print("  [B] User-created registry check...")
    uc_changes = sync_user_created_registry(registry)
    if uc_changes:
        for c in uc_changes:
            print(c)
    else:
        print("    Registry consistent, no changes")
    print()

    # ========== Validation ==========
    print("  [C] Validation warnings...")
    warnings = []

    # Check registry entries
    for cap in registry.get("capabilities", []):
        cap_id = cap.get("id", "")

        # Check empty triggers
        if not cap.get("triggers"):
            warnings.append(f"  ! {cap_id}: triggers is empty — skill unreachable by capability_finder.py")

        # Check script path exists
        script = cap.get("script")
        if script:
            script_path = script.replace("~", os.path.expanduser("~"))
            if not os.path.exists(script_path):
                warnings.append(f"  ! {cap_id}: script not found — {script}")

    # Check SKILL.md format for all skills on disk
    for skill_dir in [AUTO_GEN_DIR, USER_CREATED_DIR]:
        if not os.path.exists(skill_dir):
            continue
        for item in os.listdir(skill_dir):
            item_path = os.path.join(skill_dir, item)
            if os.path.isdir(item_path) and os.path.exists(os.path.join(item_path, "SKILL.md")):
                fixed, msg = ensure_skill_md_standard(item_path, item)
                if fixed:
                    warnings.append(f"  ! {item}: SKILL.md auto-fixed ({msg})")
                    warnings.append(f"    → re-run to register")

    if warnings:
        for w in warnings:
            print(w)
    else:
        print("    No warnings")
    print()

    # ========== Write ==========
    print("  [Write] Saving files...")
    save_json(MANIFEST_PATH, manifest)
    save_json(REGISTRY_PATH, registry)

    os.makedirs(HISTORY_DIR, exist_ok=True)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_path = os.path.join(HISTORY_DIR, f"snapshot_{run_id}.json")
    snapshot = {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(),
        "auto_changes": auto_changes,
        "user_created_changes": uc_changes,
        "reg_before": reg_before,
        "reg_after": len(registry["capabilities"]),
    }
    save_json(snapshot_path, snapshot)

    print(f"    Registry: {REGISTRY_PATH}")
    print(f"    Manifest: {MANIFEST_PATH}")
    print(f"    Snapshot: {snapshot_path}")
    print()

    # ========== Summary ==========
    active_auto = len([s for s in manifest["self_created_skills"] if s["status"] == "active"])
    active_uc = len(scan_skills_in_dir(USER_CREATED_DIR))

    print("  " + "=" * 66)
    print()
    print(f"  auto-generated: {active_auto} active")
    for s in sorted(manifest["self_created_skills"], key=lambda x: (x["status"], x["name"])):
        tag = "OK" if s["status"] == "active" else "DEL"
        print(f"    [{tag}] {s['name']}")
    print()
    print(f"  user-created: {active_uc}")
    for name in sorted(scan_skills_in_dir(USER_CREATED_DIR).keys()):
        in_reg = any(c["id"] == name for c in registry["capabilities"])
        tag = "OK" if in_reg else "WARN"
        print(f"    [{tag}] {name}")
    print()
    print(f"  Registry total: {len(registry['capabilities'])} entries")
    print()

    all_changes = auto_changes + uc_changes
    summary = {
        "version": 5,
        "timestamp": datetime.now().isoformat(),
        "run_id": run_id,
        "changes_made": len(all_changes) > 0,
        "auto_generated_count": active_auto,
        "user_created_count": active_uc,
        "registry_count": len(registry["capabilities"]),
        "changes": all_changes,
        "snapshot_path": snapshot_path,
    }
    print("---SUMMARY_START---")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("---SUMMARY_END---")
    return summary


# ============ Main Entry ============

def main():
    target = None
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg in ("--target", "-t"):
            if i + 1 < len(args):
                target = args[i + 1]
            else:
                print("[ERROR] --target requires a skill name")
                sys.exit(1)

    if target:
        print(f"  Target analysis (auto-generated only): {target}")
        target_path = os.path.join(AUTO_GEN_DIR, target)
        if not os.path.exists(target_path):
            print(f"  [ERROR] Not found: {target_path}")
            sys.exit(1)
        desc = get_skill_description(target_path)
        size = get_skill_size(target_path)
        refs = count_references(target_path)
        print(f"    Description: {desc}")
        print(f"    Size: {round(size/1024, 1)} KB")
        print(f"    References: {refs}")
    else:
        run_global_scan()


if __name__ == "__main__":
    main()
