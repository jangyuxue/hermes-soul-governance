#!/usr/bin/env python3
"""Skill Maintenance Script Test Framework

Simulates ~/.hermes/skills/ directory structure to verify maintain.py logic:
1. Auto-generated manifest diff (new, missing, revived)
2. User-created registry check (register, unregister)
3. Idempotent runs (no duplicate changes)
4. Merge candidate detection

Usage:
  python3 test_maintain.py
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_PATH = os.path.expanduser("~/.hermes/skills/user-created/skill-maintenance/scripts/maintain.py")


class TestEnv:
    """Temporary directory simulating ~/.hermes/ environment"""

    def __init__(self):
        self.tmpdir = tempfile.mkdtemp(prefix="hermes_test_")
        self.skills_dir = os.path.join(self.tmpdir, "skills")
        self.auto_dir = os.path.join(self.skills_dir, "auto-generated")
        self.user_dir = os.path.join(self.skills_dir, "user-created")
        self.registry_path = os.path.join(self.tmpdir, "user_capabilities.json")
        self.manifest_path = os.path.join(self.auto_dir, "self_created_skills.json")

        os.makedirs(self.auto_dir, exist_ok=True)
        os.makedirs(self.user_dir, exist_ok=True)

        self._save_json(self.registry_path, {
            "version": "1.0",
            "description": "Test registry",
            "capabilities": []
        })

        self._save_json(self.manifest_path, {
            "version": "1.0",
            "last_updated": "2026-01-01",
            "description": "Test manifest",
            "self_created_skills": [],
            "builtin_skills": []
        })

    def cleanup(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _save_json(self, path, data):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load_json(self, path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def create_skill(self, directory, name, content="test", refs=0, has_session_ref=False):
        skill_dir = os.path.join(directory, name)
        os.makedirs(skill_dir, exist_ok=True)

        skill_md = f"""---
name: {name}
description: "Test skill: {name}"
version: 1.0.0
---

# {name}

{content}
"""
        with open(os.path.join(skill_dir, "SKILL.md"), "w") as f:
            f.write(skill_md)

        if refs > 0 or has_session_ref:
            ref_dir = os.path.join(skill_dir, "references")
            os.makedirs(ref_dir, exist_ok=True)
            for i in range(refs):
                ref_name = f"session-2026-05-{i+1:02d}.md" if has_session_ref and i == 0 else f"ref-{i}.md"
                with open(os.path.join(ref_dir, ref_name), "w") as f:
                    f.write(f"# Reference {i}\n")

        return skill_dir

    def run_script(self, target=None):
        cmd = [sys.executable, SCRIPT_PATH]
        if target:
            cmd.extend(["--target", target])

        script_content = open(SCRIPT_PATH, "r").read()
        test_script = script_content.replace(
            'AUTO_GEN_DIR = os.path.expanduser("~/.hermes/skills/auto-generated")',
            f'AUTO_GEN_DIR = "{self.auto_dir}"'
        ).replace(
            'USER_CREATED_DIR = os.path.expanduser("~/.hermes/skills/user-created")',
            f'USER_CREATED_DIR = "{self.user_dir}"'
        ).replace(
            'REGISTRY_PATH = os.path.expanduser("~/.hermes/user-registry/user_capabilities.json")',
            f'REGISTRY_PATH = "{self.registry_path}"'
        )

        test_script_path = os.path.join(self.tmpdir, "test_maintain.py")
        with open(test_script_path, "w") as f:
            f.write(test_script)

        result = subprocess.run(
            [sys.executable, test_script_path],
            capture_output=True, text=True, timeout=30
        )

        summary = None
        if "---SUMMARY_START---" in result.stdout:
            start = result.stdout.index("---SUMMARY_START---") + len("---SUMMARY_START---")
            end = result.stdout.index("---SUMMARY_END---")
            try:
                summary = json.loads(result.stdout[start:end].strip())
            except:
                pass

        return result.returncode, result.stdout, summary

    def get_registry_ids(self):
        reg = self._load_json(self.registry_path)
        return {c["id"] for c in reg["capabilities"]}

    def get_manifest_active(self):
        manifest = self._load_json(self.manifest_path)
        return {s["name"]: s for s in manifest["self_created_skills"] if s["status"] == "active"}

    def get_manifest_deleted(self):
        manifest = self._load_json(self.manifest_path)
        return {s["name"]: s for s in manifest["self_created_skills"] if s["status"] == "deleted"}


def test_initial_empty(env):
    """Test 1: Empty directory, no changes"""
    print("  Test 1: Empty directory...", end=" ")
    code, out, summary = env.run_script()
    assert code == 0, f"Script exit code non-zero: {code}"
    assert summary is not None, "JSON summary not found"
    assert summary["auto_generated_count"] == 0, f"Expected 0 auto-generated, got {summary['auto_generated_count']}"
    assert summary["user_created_count"] == 0, f"Expected 0 user-created, got {summary['user_created_count']}"
    assert summary["changes_made"] == False, "Empty directory should have no changes"
    print("PASS")


def test_auto_gen_new_skill(env):
    """Test 2: Auto-generated new skill detected"""
    print("  Test 2: Auto-generated new skill...", end=" ")
    env.create_skill(env.auto_dir, "test-auto-skill", refs=3, has_session_ref=True)
    code, out, summary = env.run_script()
    assert summary["auto_generated_count"] == 1, "Should detect 1 auto-generated"
    assert "test-auto-skill" in env.get_manifest_active(), "Should add to manifest"
    assert "test-auto-skill" in env.get_registry_ids(), "Should register in registry"
    print("PASS")


def test_user_created_register(env):
    """Test 3: User-created skill registered"""
    print("  Test 3: User-created registration...", end=" ")
    env.create_skill(env.user_dir, "my-custom-skill")
    code, out, summary = env.run_script()
    assert "my-custom-skill" in env.get_registry_ids(), "Should register in registry"
    reg = env._load_json(env.registry_path)
    entry = [c for c in reg["capabilities"] if c["id"] == "my-custom-skill"][0]
    assert entry["category"] == "user-created", f"Category should be user-created, got {entry['category']}"
    print("PASS")


def test_user_created_unregister(env):
    """Test 4: User-created skill unregistered after deletion"""
    print("  Test 4: User-created deletion unregister...", end=" ")
    env.create_skill(env.user_dir, "temp-skill")
    env.run_script()
    assert "temp-skill" in env.get_registry_ids(), "Should be registered"

    shutil.rmtree(os.path.join(env.user_dir, "temp-skill"))

    code, out, summary = env.run_script()
    assert "temp-skill" not in env.get_registry_ids(), "Should be removed from registry"
    print("PASS")


def test_idempotent(env):
    """Test 5: Second run has no duplicate changes"""
    print("  Test 5: Idempotency check...", end=" ")
    env.create_skill(env.auto_dir, "stable-skill")
    env.create_skill(env.user_dir, "stable-user-skill")
    env.run_script()

    code, out, summary = env.run_script()
    assert summary["changes_made"] == False, "Second run should have no changes"
    print("PASS")


def test_manifest_deleted_detection(env):
    """Test 6: Deleted skill detected in manifest"""
    print("  Test 6: Manifest deleted detection...", end=" ")
    env.create_skill(env.auto_dir, "vanish-skill")
    env.run_script()
    assert "vanish-skill" in env.get_manifest_active(), "Should be active"

    shutil.rmtree(os.path.join(env.auto_dir, "vanish-skill"))
    env.run_script()
    assert "vanish-skill" not in env.get_manifest_active(), "Should not be active"
    assert "vanish-skill" in env.get_manifest_deleted(), "Should be marked deleted"
    print("PASS")


def test_mixed_skills(env):
    """Test 7: Mixed auto + user skills coexist"""
    print("  Test 7: Mixed skills scenario...", end=" ")
    env.create_skill(env.auto_dir, "auto-1", refs=6)
    env.create_skill(env.auto_dir, "auto-2")
    env.create_skill(env.user_dir, "user-1")
    env.create_skill(env.user_dir, "user-2")

    code, out, summary = env.run_script()
    assert summary["auto_generated_count"] == 2
    assert summary["user_created_count"] == 2

    reg_ids = env.get_registry_ids()
    assert "auto-1" in reg_ids
    assert "auto-2" in reg_ids
    assert "user-1" in reg_ids
    assert "user-2" in reg_ids
    print("PASS")


def test_empty_after_populated(env):
    """Test 8: All skills removed, clean state"""
    print("  Test 8: Clean after removal...", end=" ")
    env.create_skill(env.auto_dir, "to-delete")
    env.create_skill(env.user_dir, "to-delete-user")
    env.run_script()

    shutil.rmtree(os.path.join(env.auto_dir, "to-delete"))
    shutil.rmtree(os.path.join(env.user_dir, "to-delete-user"))

    code, out, summary = env.run_script()
    assert summary["auto_generated_count"] == 0
    assert summary["user_created_count"] == 0
    assert "to-delete" in env.get_manifest_deleted()
    print("PASS")


def test_skill_md_auto_fix(env):
    """Test 9: Bare SKILL.md gets auto-fixed with frontmatter"""
    print("  Test 9: SKILL.md auto-fix...", end=" ")
    # Create skill with bare content (no frontmatter)
    skill_dir = os.path.join(env.user_dir, "bare-skill")
    os.makedirs(skill_dir, exist_ok=True)
    with open(os.path.join(skill_dir, "SKILL.md"), "w") as f:
        f.write("# Just a heading\n")

    code, out, summary = env.run_script()
    # Check that SKILL.md now has frontmatter
    with open(os.path.join(skill_dir, "SKILL.md")) as f:
        content = f.read()
    assert content.startswith("---"), "SKILL.md should have frontmatter after fix"
    assert "name: bare-skill" in content, "Should have name from dir name"
    assert "description:" in content, "Should have description"
    assert "# Just a heading" in content, "Should preserve original content"
    assert "bare-skill" in env.get_registry_ids(), "Should be registered"
    print("PASS")


def test_validation_empty_triggers(env):
    """Test 10: Validation warns about empty triggers"""
    print("  Test 10: Validation empty triggers...", end=" ")
    env.create_skill(env.auto_dir, "triggerless-skill")
    code, out, summary = env.run_script()
    assert "triggers is empty" in out, "Should warn about empty triggers"
    print("PASS")


def test_validation_bad_script_path(env):
    """Test 11: Validation warns about missing script"""
    print("  Test 11: Validation bad script path...", end=" ")
    env.create_skill(env.user_dir, "bad-script-skill")
    code, out, summary = env.run_script()

    # Manually add a bad script path
    import json
    with open(env.registry_path) as f:
        reg = json.load(f)
    for c in reg["capabilities"]:
        if c["id"] == "bad-script-skill":
            c["script"] = "~/.hermes/skills/nonexistent/script.py"
    with open(env.registry_path, "w") as f:
        json.dump(reg, f, indent=2)

    code, out, summary = env.run_script()
    assert "script not found" in out, "Should warn about missing script"
    print("PASS")


def main():
    print()
    print("=" * 60)
    print("  Skill Maintenance Script Test Framework")
    print("=" * 60)
    print()

    tests = [
        test_initial_empty,
        test_auto_gen_new_skill,
        test_user_created_register,
        test_user_created_unregister,
        test_idempotent,
        test_manifest_deleted_detection,
        test_mixed_skills,
        test_empty_after_populated,
        test_skill_md_auto_fix,
        test_validation_empty_triggers,
        test_validation_bad_script_path,
    ]

    passed = 0
    failed = 0

    for test_fn in tests:
        env = TestEnv()
        try:
            test_fn(env)
            passed += 1
        except AssertionError as e:
            print(f"FAIL: {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR: {e}")
            failed += 1
        finally:
            env.cleanup()

    print()
    print("=" * 60)
    print(f"  Results: {passed} passed, {failed} failed, {len(tests)} total")
    print("=" * 60)
    print()

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
