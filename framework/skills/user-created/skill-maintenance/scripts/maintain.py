#!/usr/bin/env python3
"""Automated Skill Maintenance Script v6

v5 → v6: Removed self_created_skills.json manifest.
         All lifecycle tracking merged into user_capabilities.json via lifecycle field.
         Registry is now the single source of truth for all skills.

Modes:
  Global scan (default): 
    1. [Orphan]  Scan category dirs → move non-bundled to auto-generated/
    2. [Sync]    auto-generated/ vs registry lifecycle diff
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
BACKUP_DIR = os.path.join(AUTO_GEN_DIR, ".backup")
HISTORY_DIR = os.path.expanduser("~/.hermes/skills/user-created/skill-maintenance/.history")


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
    """Extract topic keywords from SKILL.md: headings, tags, and description field."""
    keywords = set()
    skill_md = os.path.join(skill_path, "SKILL.md")
    if not os.path.exists(skill_md):
        return keywords
    with open(skill_md, "r", encoding="utf-8") as f:
        content = f.read(3000)

    STOPWORDS = {
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'doing', 'will', 'would',
        'can', 'could', 'may', 'might', 'shall', 'should', 'to', 'too', 'for',
        'of', 'in', 'on', 'at', 'by', 'with', 'from', 'as', 'and', 'or', 'but',
        'not', 'no', 'nor', 'this', 'that', 'these', 'those', 'it', 'its',
        'you', 'your', 'we', 'our', 'they', 'their', 'he', 'she', 'him', 'her',
        'all', 'any', 'each', 'every', 'some', 'most', 'many', 'much', 'few',
        'use', 'used', 'using', 'uses', 'also', 'very', 'just', 'only', 'even',
        'than', 'then', 'when', 'what', 'which', 'who', 'whom', 'where', 'how',
        'into', 'over', 'about', 'after', 'before', 'between', 'through', 'during',
        'such', 'more', 'less', 'other', 'another', 'both', 'each', 'own',
        'skill', 'setup', 'help', 'need', 'want', 'work', 'working', 'works',
        'based', 'built', 'like', 'take', 'make', 'made', 'way', 'well',
    }

    # 1. Headings
    for match in re.finditer(r"##\s+(.*?)(?:\n|$)", content):
        keywords.add(match.group(1).strip().lower())

    # 2. Tags
    tags_match = re.search(r"tags:\s*\[(.*?)\]", content)
    if tags_match:
        for tag in tags_match.group(1).split(","):
            tag = tag.strip().strip("\"'")
            if tag:
                keywords.add(tag.lower())

    # 3. Description field — extract meaningful concepts
    desc_match = re.search(r'description:\s*["\']?(.*?)["\']?\s*(?:\n|platforms|version|author|tags)', content)
    if not desc_match:
        desc_match = re.search(r'description:\s*["\']?(.*?)(?:\n[a-z])', content)
    if desc_match:
        desc = desc_match.group(1).strip().rstrip('"\'')
        desc_words = re.findall(r'[a-zA-Z][a-zA-Z-]{2,}', desc.lower())
        for w in desc_words:
            w_clean = w.strip("-")
            if w_clean not in STOPWORDS and len(w_clean) > 2:
                keywords.add(w_clean)

    return keywords


def get_skill_headings(skill_path):
    headings = set()
    skill_md = os.path.join(skill_path, "SKILL.md")
    if not os.path.exists(skill_md):
        return headings
    with open(skill_md, "r", encoding="utf-8") as f:
        content = f.read(3000)
    for match in re.finditer(r"##\s+(.*?)(?:\n|$)", content):
        h = match.group(1).strip().lower()
        if h:
            headings.add(h)
    return headings


def get_skill_related(skill_path):
    related = set()
    skill_md = os.path.join(skill_path, "SKILL.md")
    if not os.path.exists(skill_md):
        return related
    with open(skill_md, "r", encoding="utf-8") as f:
        content = f.read(2000)
    match = re.search(r"related_skills:\s*\[(.*?)\]", content)
    if match:
        for item in match.group(1).split(","):
            item = item.strip().strip("\"'")
            if item:
                related.add(item)
    return related


def detect_merge_candidates(registry):
    """Detect merge candidates among active auto-generated skills in registry."""
    candidates = []
    active = [c for c in registry.get("capabilities", [])
              if c.get("lifecycle", {}).get("type") == "auto-generated"
              and c.get("lifecycle", {}).get("status") == "active"]

    skill_data = {}
    for cap in active:
        name = cap["id"]
        path = os.path.join(AUTO_GEN_DIR, name)
        skill_data[name] = {
            "keywords": get_skill_topic_keywords(path),
            "headings": get_skill_headings(path),
            "related": get_skill_related(path),
            "has_refs": os.path.isdir(os.path.join(path, "references")),
            "has_scripts": os.path.isdir(os.path.join(path, "scripts")),
        }

    for i in range(len(active)):
        for j in range(i + 1, len(active)):
            a, b = active[i]["id"], active[j]["id"]
            da, db = skill_data[a], skill_data[b]
            score = 0.0
            axes_used = set()
            reasons = []

            # [A] Name overlap (+0.20)
            a_parts = set(a.lower().replace("-", " ").split())
            b_parts = set(b.lower().replace("-", " ").split())
            name_overlap = a_parts & b_parts
            if name_overlap:
                score += 0.20
                axes_used.add("name")
                reasons.append(f"name overlap: {name_overlap}")

            # [B] Content keyword overlap (max +0.30)
            ka, kb = da["keywords"], db["keywords"]
            kw_overlap = ka & kb
            content_union = ka | kb
            has_kw = bool(kw_overlap)
            jaccard = len(kw_overlap) / len(content_union) if content_union else 0.0
            if name_overlap and not has_kw:
                continue
            if ka and kb and kw_overlap:
                kw_score = min(0.30, 0.10 * len(kw_overlap))
                score += kw_score
                axes_used.add("content")
                reasons.append(f"topic: {len(kw_overlap)} kw (j={jaccard:.2f})")

            # [C] Heading structure overlap (+0.10 if j >= 0.25)
            ha, hb = da["headings"], db["headings"]
            if ha and hb:
                h_overlap = ha & hb
                h_union = ha | hb
                h_jaccard = len(h_overlap) / len(h_union) if h_union else 0.0
                if h_jaccard >= 0.25:
                    score += 0.10
                    axes_used.add("struct")
                    reasons.append(f"headings (j={h_jaccard:.2f})")

            # [D] Related-skills cross-reference (+0.20)
            if a in db["related"] or b in da["related"]:
                score += 0.20
                axes_used.add("xref")
                reasons.append("related_skills ref")

            # [E] File structure (+0.05)
            struct_score = 0
            if da["has_refs"] and db["has_refs"]:
                struct_score += 1
            if da["has_scripts"] and db["has_scripts"]:
                struct_score += 1
            if struct_score >= 1:
                score += 0.05
                axes_used.add("fstruct")
                reasons.append("similar structure")

            # Gates
            if len(axes_used) < 2:
                continue
            if not name_overlap and jaccard < 0.15:
                continue
            if score >= 0.30:
                axes_str = "+".join(sorted(axes_used))
                candidates.append(
                    f"  ! {a} <-> {b} (score={score:.1f}, axes=[{axes_str}], "
                    + ", ".join(reasons) + ")"
                )

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


def make_lifecycle_entry(category, status="active", note=""):
    """Create a lifecycle dict for a skill capability entry."""
    return {
        "type": category,
        "status": status,
        "registered": True,
        "note": note,
    }


def get_or_create_lifecycle(cap):
    """Get lifecycle dict from a capability, creating default if missing."""
    if "lifecycle" not in cap:
        cat = cap.get("category", "auto-generated")
        cap["lifecycle"] = make_lifecycle_entry(cat)
    return cap["lifecycle"]


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
                "lifecycle": make_lifecycle_entry("user-created"),
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
        lc = get_or_create_lifecycle(c)
        if lc.get("type") == "user-created" and c["id"] not in disk_skills:
            to_remove.append(c)
            changes.append(f"  - Unregistered {c['id']} (disk deleted)")

    for entry in to_remove:
        registry["capabilities"].remove(entry)

    return changes


# ============ Auto-generated Sync (Registry-based) ============

def sync_auto_generated_skills(registry):
    """Sync auto-generated/ directory against registry lifecycle entries."""
    changes = []
    disk_skills = scan_skills_in_dir(AUTO_GEN_DIR)
    disk_skills = {n: p for n, p in disk_skills.items()
                   if n not in ("self_created_skills",)}

    reg_auto = {}
    for cap in registry["capabilities"]:
        lc = get_or_create_lifecycle(cap)
        if lc.get("type") == "auto-generated":
            reg_auto[cap["id"]] = cap

    reg_ids = {c["id"] for c in registry["capabilities"]}

    # New: disk has auto-generated skill but registry does not
    for name, path in disk_skills.items():
        if name not in reg_auto:
            # Auto-fix SKILL.md if not standard
            fixed, msg = ensure_skill_md_standard(path, name)

            description = get_skill_description(path)
            entry = {
                "id": name,
                "name": name.replace("-", " ").title(),
                "category": "auto-generated",
                "lifecycle": {
                    "type": "auto-generated",
                    "status": "active",
                    "registered": True,
                    "note": f"First detected: {datetime.now().strftime('%Y-%m-%d')}"
                },
                "triggers": [],
                "description": description or f"Auto-generated skill: {name}",
                "script": None,
                "dependencies": [],
                "examples": [],
            }
            registry["capabilities"].append(entry)
            reg_auto[name] = entry
            reg_ids.add(name)
            changes.append(f"  + Added to registry: {name}")

    # Deleted: registry has active auto-generated but disk does not → mark deleted
    for name, cap in reg_auto.items():
        lc = get_or_create_lifecycle(cap)
        if lc.get("status") == "active" and name not in disk_skills:
            lc["status"] = "deleted"
            lc["note"] += f" | Disk deleted {datetime.now().strftime('%Y-%m-%d')}"
            changes.append(f"  - Marked deleted: {name}")

    # Revived: registry has deleted auto-generated and disk has → restore
    for name, cap in reg_auto.items():
        lc = get_or_create_lifecycle(cap)
        if lc.get("status") == "deleted" and name in disk_skills:
            lc["status"] = "active"
            lc["note"] += f" | Revived {datetime.now().strftime('%Y-%m-%d')}"
            changes.append(f"  ↺ Revived: {name}")

    # Description sync: SKILL.md → registry
    for name, path in disk_skills.items():
        if name in reg_auto:
            disk_desc = get_skill_description(path)
            cap = reg_auto[name]
            if cap.get("description") != disk_desc:
                cap["description"] = disk_desc
                changes.append(f"  ~ Registry description sync: {name}")

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


def migrate_misplaced_skill(name, source_path, registry, bundled):
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
                lc = get_or_create_lifecycle(cap)
                lc["type"] = "auto-generated"
                lc["status"] = "active"
                lc["registered"] = True
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
            "lifecycle": make_lifecycle_entry("auto-generated", note=f"Migrated from {category_hint}/ ({datetime.now().strftime('%Y-%m-%d')})"),
            "triggers": [],
            "description": description or f"Auto-generated skill: {name}",
            "script": None,
            "dependencies": [],
            "examples": [],
        }
        registry["capabilities"].append(entry)
        changes.append(f"  → Registered {name} → user_capabilities.json")
        reg_ids.add(name)

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


def scan_and_migrate_misplaced(registry):
    """Orphan: Scan category dirs for non-bundled skills, migrate to auto-generated/.

    Detects two kinds of misplaced skills:
      1. Skills inside a category directory (e.g. creative/my-skill/)
      2. Standalone skills at skills/<name>/ (e.g. skills/soul-governance/)
         where the SKILL.md is directly inside the category-level dir itself.
    """
    changes = []
    bundled = load_bundled_manifest()

    # Scan each category directory
    for cat_dir in get_category_directories():
        # Case 1: Skills nested inside category dir (e.g. creative/sub-skill/)
        for name, path in sorted(scan_skills_in_dir(cat_dir).items()):
            if is_bundled_skill(name, path, bundled):
                continue  # Bundled system skill, leave it
            result = migrate_misplaced_skill(name, path, registry, bundled)
            changes.extend(result)

        # Case 2: Category dir itself IS a standalone skill (SKILL.md directly inside,
        # e.g. skills/soul-governance/SKILL.md). This happens when Hermes Agent creates
        # a skill directly under skills/ without using auto-generated/ or user-created/.
        cat_name = os.path.basename(cat_dir)
        cat_skill_md = os.path.join(cat_dir, "SKILL.md")
        if os.path.exists(cat_skill_md):
            if is_bundled_skill(cat_name, cat_dir, bundled):
                continue
            if cat_name in {os.path.basename(p) for _, p in
                            scan_skills_in_dir(AUTO_GEN_DIR).items()}:
                continue  # Already migrated (avoid double-move)
            result = migrate_misplaced_skill(cat_name, cat_dir, registry, bundled)
            changes.extend(result)

    return changes


# ============ Global Scan ============

def run_global_scan():
    print()
    print("=" * 66)
    print("  Skill Maintenance Tool v6 — Global Scan (Unified Registry)")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  auto-generated: {AUTO_GEN_DIR}")
    print(f"  user-created:   {USER_CREATED_DIR}")
    print("=" * 66)
    print()

    # Load registry — create default if missing for portability
    registry = load_json(REGISTRY_PATH)
    if registry is None:
        registry = {
            "version": "2.0",
            "last_updated": datetime.now().strftime("%Y-%m-%d"),
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

    reg_before = len(registry["capabilities"])

    # ========== Orphan Detection & Migration ==========
    print("  [Orphan] Misplaced skill check...")
    if not os.path.exists(BUNDLED_MANIFEST_PATH):
        print("    [ERROR] .bundled_manifest not found — cannot identify bundled skills,")
        print("            skipping orphan check to prevent accidental skill relocation.")
        print("    Fix: run 'hermes curator sync-manifest' or ask your Hermes provider")
        print("         to regenerate ~/.hermes/skills/.bundled_manifest")
        misplaced_changes = []
    else:
        misplaced_changes = scan_and_migrate_misplaced(registry)
    if misplaced_changes:
        for c in misplaced_changes:
            print(c)
    else:
        print("    No misplaced skills found")
    print()

    # ========== Sync: Auto-generated vs Registry Lifecycle ==========
    print("  [Sync] Auto-generated skill lifecycle sync...")
    auto_changes = sync_auto_generated_skills(registry)
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
    if os.path.exists(AUTO_GEN_DIR):
        for item in os.listdir(AUTO_GEN_DIR):
            item_path = os.path.join(AUTO_GEN_DIR, item)
            if os.path.isdir(item_path) and os.path.exists(os.path.join(item_path, "SKILL.md")):
                fixed, msg = ensure_skill_md_standard(item_path, item)
                if fixed:
                    warnings.append(f"  ! {item}: SKILL.md auto-fixed ({msg})")
                    warnings.append(f"    → re-run to register")

    # Merge candidate detection
    merge_warnings = detect_merge_candidates(registry)
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
    print("  [Write] Saving registry...")
    registry["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    save_json(REGISTRY_PATH, registry)

    # Save snapshot
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(HISTORY_DIR, exist_ok=True)
    snapshot_path = os.path.join(HISTORY_DIR, f"snapshot_{run_id}.json")
    save_json(snapshot_path, registry)
    print(f"    Snapshot: {snapshot_path}")

    print(f"    Registry: {REGISTRY_PATH}")
    print()

    # ========== Summary ==========
    auto_active = len([c for c in registry["capabilities"]
                       if c.get("lifecycle", {}).get("type") == "auto-generated"
                       and c.get("lifecycle", {}).get("status") == "active"])
    auto_deleted = len([c for c in registry["capabilities"]
                        if c.get("lifecycle", {}).get("type") == "auto-generated"
                        and c.get("lifecycle", {}).get("status") == "deleted"])
    uc_active = len(scan_skills_in_dir(USER_CREATED_DIR))

    print("  " + "=" * 66)
    print()
    print(f"  auto-generated: {auto_active} active, {auto_deleted} deleted")
    for cap in sorted(registry["capabilities"], key=lambda x: (x.get("lifecycle", {}).get("status", ""), x["id"])):
        lc = cap.get("lifecycle", {})
        if lc.get("type") == "auto-generated":
            tag = "OK" if lc.get("status") == "active" else "DEL"
            print(f"    [{tag}] {cap['id']}")
    print()
    print(f"  user-created: {uc_active}")
    for name in sorted(scan_skills_in_dir(USER_CREATED_DIR).keys()):
        in_reg = any(c["id"] == name for c in registry["capabilities"])
        tag = "OK" if in_reg else "WARN"
        print(f"    [{tag}] {name}")
    print()
    print(f"  Registry total: {len(registry['capabilities'])} entries")
    print()

    all_changes = misplaced_changes + auto_changes + uc_changes
    summary = {
        "version": 6,
        "timestamp": datetime.now().isoformat(),
        "changes_made": len(all_changes) > 0,
        "auto_generated_active": auto_active,
        "auto_generated_deleted": auto_deleted,
        "user_created_count": uc_active,
        "registry_count": len(registry["capabilities"]),
        "changes": all_changes,
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
