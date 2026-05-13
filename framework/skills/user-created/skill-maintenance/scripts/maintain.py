#!/usr/bin/env python3
"""Automated Skill Maintenance Script v5

v4 → v5: Added user-created/ directory check
         Script only syncs registry for user-created/ (does not modify skill content)
         Manifest only tracks skills under auto-generated/

Modes:
  Global scan (default): 
    1. [Orphan]  Scan category dirs → move non-bundled to auto-generated/
    2. [Sync]    auto-generated/ vs manifest diff
    3. [Reg]     user-created/ vs registry consistency
    4. [Check]   Validate warnings (empty triggers, missing paths, format fix,
                 merge candidate detection)
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


def get_skill_topic_keywords(skill_path):
    """Extract topic keywords from SKILL.md headings and tags."""
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


def detect_merge_candidates(manifest, registry):
    """Compare all active auto-generated skills pairwise, return merge suggestions.
    
    Only scans auto-generated/ skills (tracked in manifest). Does NOT scan
    user-created/ skills — those are hand-crafted by the user and should not
    be suggested for merging.
    """
    candidates = []
    active = [s for s in manifest.get("self_created_skills", []) if s["status"] == "active"]
    name_keywords = {}

    for s in active:
        path = os.path.join(AUTO_GEN_DIR, s["name"])
        kws = get_skill_topic_keywords(path)
        name_keywords[s["name"]] = kws

    for i in range(len(active)):
        for j in range(i + 1, len(active)):
            a, b = active[i]["name"], active[j]["name"]
            score = 0.0
            reasons = []

            # Name overlap
            a_parts = set(a.lower().replace("-", " ").split("_"))
            b_parts = set(b.lower().replace("-", " ").split("_"))
            overlap = a_parts & b_parts
            if overlap:
                score += 0.3
                reasons.append(f"name overlap: {overlap}")

            # Keyword overlap
            ka = name_keywords.get(a, set())
            kb = name_keywords.get(b, set())
            if ka and kb:
                kw_overlap = ka & kb
                if kw_overlap:
                    score += min(0.4, 0.1 * len(kw_overlap))
                    reasons.append(f"topic overlap: {kw_overlap}")

            if score >= 0.3:
                candidates.append(f"  ! {a} <-> {b} (score={score:.1f}, {', '.join(reasons)})")

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

    # Sync description: SKILL.md → manifest + registry
    for name, path in disk_skills.items():
        if name in known:
            disk_desc = get_skill_description(path)
            man = known[name]
            if man.get("description") != disk_desc:
                man["description"] = disk_desc
                changes.append(f"  ~ Manifest description sync: {name}")
                # Also update registry if present
                for cap in registry.get("capabilities", []):
                    if cap["id"] == name and cap.get("description") != disk_desc:
                        cap["description"] = disk_desc
                        changes.append(f"  ~ Registry description sync: {name}")

    # Update registered status for all skills
    for s in manifest["self_created_skills"]:
        s["registered"] = s["name"] in reg_ids
    manifest["last_updated"] = datetime.now().strftime("%Y-%m-%d")

    return changes


# ============ Orphan Detection & Migration ============

SKILLS_BASE = os.path.expanduser("~/.hermes/skills")
BUNDLED_MANIFEST_PATH = os.path.join(SKILLS_BASE, ".bundled_manifest")

EXCLUDED_CATEGORIES = {"auto-generated", "user-created", ".hub", ".backup", ".history"}


def load_bundled_manifest():
    """Load .bundled_manifest and return set of bundled skill names."""
    if not os.path.exists(BUNDLED_MANIFEST_PATH):
        return set()
    bundled = set()
    with open(BUNDLED_MANIFEST_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and ":" in line:
                bundled.add(line.split(":")[0])
    return bundled


def get_category_directories():
    """Get all category directories under skills/ (exclude system/internal dirs)."""
    cats = []
    if not os.path.exists(SKILLS_BASE):
        return cats
    for item in sorted(os.listdir(SKILLS_BASE)):
        if item.startswith(".") or item in EXCLUDED_CATEGORIES:
            continue
        item_path = os.path.join(SKILLS_BASE, item)
        if os.path.isdir(item_path):
            cats.append(item_path)
    return cats


def migrate_misplaced_skill(name, source_path, registry, manifest, bundled):
    """Move a misplaced skill to auto-generated/ and update records.

    Returns list of change descriptions.
    """
    changes = []
    target_path = os.path.join(AUTO_GEN_DIR, name)

    # Conflict: target already exists
    if os.path.exists(target_path):
        changes.append(f"  ! {name}: target auto-generated/{name} already exists (manual merge needed)")
        return changes

    # Determine origin info before moving
    category_hint = os.path.basename(os.path.dirname(source_path))

    # Move directory
    shutil.move(source_path, target_path)
    changes.append(f"  ✓ {name}: {category_hint}/ → auto-generated/")

    # Register or update in user_capabilities.json
    reg_ids = {c["id"] for c in registry.get("capabilities", [])}
    if name in reg_ids:
        for cap in registry["capabilities"]:
            if cap["id"] == name:
                old_cat = cap.get("category", "")
                cap["category"] = "auto-generated"
                # Rewrite script path if present
                script = cap.get("script")
                if script:
                    new_path = os.path.join(AUTO_GEN_DIR, name, os.path.basename(script.replace("~", os.path.expanduser("~"))))
                    cap["script"] = new_path.replace(os.path.expanduser("~"), "~")
                changes.append(f"  → Registry updated: {name} (category: {old_cat} → auto-generated)")
    else:
        description = get_skill_description(target_path)
        entry = {
            "id": name,
            "name": name.replace("-", " ").title(),
            "category": "auto-generated",
            "triggers": [],
            "description": description or f"Auto-generated skill: {name}",
            "script": None,
            "dependencies": [],
            "examples": [],
        }
        registry["capabilities"].append(entry)
        changes.append(f"  → Registered {name} → user_capabilities.json")
        reg_ids.add(name)

    # Add or update manifest entry
    known = {s["name"]: s for s in manifest.get("self_created_skills", [])}
    description = get_skill_description(target_path)
    if name not in known:
        entry = {
            "name": name,
            "type": "auto-generated",
            "description": description,
            "status": "active",
            "category": "auto-generated",
            "registered": True,
            "note": f"Migrated from {category_hint}/ ({datetime.now().strftime('%Y-%m-%d')})",
        }
        manifest["self_created_skills"].append(entry)
        changes.append(f"  + Manifest added: {name}")
    else:
        existing = known[name]
        if existing.get("description") != description:
            existing["description"] = description
            changes.append(f"  ~ Manifest updated: {name} description")
        if existing.get("status") != "active":
            existing["status"] = "active"
            changes.append(f"  ~ Manifest updated: {name} status → active")
        if not existing.get("registered"):
            existing["registered"] = True
            changes.append(f"  ~ Manifest updated: {name} registered → True")

    return changes


def is_bundled_skill(name, path, bundled):
    """Check if a skill is bundled by matching directory name OR SKILL.md name field."""
    if name in bundled:
        return True
    # Also check the SKILL.md frontmatter 'name:' field
    skill_name = get_skill_name_from_frontmatter(path)
    if skill_name and skill_name in bundled:
        return True
    return False


def get_skill_name_from_frontmatter(skill_path):
    """Extract 'name:' from SKILL.md frontmatter."""
    skill_md = os.path.join(skill_path, "SKILL.md")
    if not os.path.exists(skill_md):
        return None
    with open(skill_md, "r", encoding="utf-8") as f:
        content = f.read(2000)
    # Only match inside frontmatter (between --- markers)
    if not content.startswith("---"):
        return None
    end = content.find("---", 3)
    if end == -1:
        return None
    frontmatter = content[3:end]
    match = re.search(r"^name:\s*(.*?)$", frontmatter, re.MULTILINE)
    return match.group(1).strip() if match else None


def scan_and_migrate_misplaced(registry, manifest):
    """Orphan: Scan category dirs for non-bundled skills, migrate to auto-generated/."""
    changes = []
    bundled = load_bundled_manifest()

    # Scan each category directory
    for cat_dir in get_category_directories():
        for name, path in sorted(scan_skills_in_dir(cat_dir).items()):
            if is_bundled_skill(name, path, bundled):
                continue  # Bundled system skill, leave it
            result = migrate_misplaced_skill(name, path, registry, manifest, bundled)
            changes.extend(result)

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

    # Load registry — create default if missing for portability
    registry = load_json(REGISTRY_PATH)
    if registry is None:
        registry = {
            "version": "1.0",
            "description": "User custom capabilities registry",
            "capabilities": [],
        }
        print("    Created new registry: user_capabilities.json")
    backup_file(REGISTRY_PATH)

    # Ensure target directories exist
    if not os.path.exists(AUTO_GEN_DIR):
        os.makedirs(AUTO_GEN_DIR, exist_ok=True)
        print(f"    Created directory: auto-generated/")
    if not os.path.exists(USER_CREATED_DIR):
        os.makedirs(USER_CREATED_DIR, exist_ok=True)
        print(f"    Created directory: user-created/")

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

    # ========== Orphan Detection & Migration ==========
    # Run FIRST: move non-bundled skills from category dirs to auto-generated/
    # so Sync can pick them up in the same run.
    print("  [Orphan] Misplaced skill check...")
    misplaced_changes = scan_and_migrate_misplaced(registry, manifest)
    if misplaced_changes:
        for c in misplaced_changes:
            print(c)
    else:
        print("    No misplaced skills found")
    print()

    # ========== Sync: Auto-generated Manifest Diff ==========
    # After orphan migration, all misplaced skills are now in auto-generated/.
    print("  [Sync] Auto-generated manifest diff...")
    auto_changes = sync_auto_generated_manifest(manifest, registry)
    if auto_changes:
        for c in auto_changes:
            print(c)
    else:
        print("    No changes")
    print()

    # ========== Reg: User-created Registry Check ==========
    print("  [Reg] User-created registry check...")
    uc_changes = sync_user_created_registry(registry)
    if uc_changes:
        for c in uc_changes:
            print(c)
    else:
        print("    Registry consistent, no changes")
    print()

    # ========== Validation ==========
    print("  [Check] Validation warnings...")
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

    # Check SKILL.md format for auto-generated skills only
    for skill_dir in [AUTO_GEN_DIR]:
        if not os.path.exists(skill_dir):
            continue
        for item in os.listdir(skill_dir):
            item_path = os.path.join(skill_dir, item)
            if os.path.isdir(item_path) and os.path.exists(os.path.join(item_path, "SKILL.md")):
                fixed, msg = ensure_skill_md_standard(item_path, item)
                if fixed:
                    warnings.append(f"  ! {item}: SKILL.md auto-fixed ({msg})")
                    warnings.append(f"    → re-run to register")

    # Merge candidate detection
    merge_warnings = detect_merge_candidates(manifest, registry)
    if merge_warnings:
        warnings.append("")
        for m in merge_warnings:
            warnings.append(m)

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
        "misplaced_changes": misplaced_changes,
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

    all_changes = auto_changes + uc_changes + misplaced_changes
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
