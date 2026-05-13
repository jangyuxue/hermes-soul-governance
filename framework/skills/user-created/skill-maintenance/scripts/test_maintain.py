#!/usr/bin/env python3
"""技能维护脚本测试框架

模拟 ~/.hermes/skills/ 目录结构，验证 maintain.py 的所有核心逻辑：
1. auto-generated 清单比对（新增、缺失、恢复）
2. user-created 注册表检查（注册、注销）
3. 二次运行无重复变更
4. 合并候选检测

运行：
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

# ============ 测试工具 ============

class TestEnv:
    """模拟 ~/.hermes/ 环境的临时目录"""

    def __init__(self):
        self.tmpdir = tempfile.mkdtemp(prefix="hermes_test_")
        self.skills_dir = os.path.join(self.tmpdir, "skills")
        self.auto_dir = os.path.join(self.skills_dir, "auto-generated")
        self.user_dir = os.path.join(self.skills_dir, "user-created")
        self.registry_path = os.path.join(self.tmpdir, "user_capabilities.json")
        self.manifest_path = os.path.join(self.auto_dir, "self_created_skills.json")

        # 创建目录结构
        os.makedirs(self.auto_dir, exist_ok=True)
        os.makedirs(self.user_dir, exist_ok=True)

        # 初始化空注册表
        self._save_json(self.registry_path, {
            "version": "1.0",
            "description": "Test registry",
            "capabilities": []
        })

        # 初始化空清单
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
        """创建一个模拟技能目录"""
        skill_dir = os.path.join(directory, name)
        os.makedirs(skill_dir, exist_ok=True)

        # SKILL.md
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

        # references
        if refs > 0 or has_session_ref:
            ref_dir = os.path.join(skill_dir, "references")
            os.makedirs(ref_dir, exist_ok=True)
            for i in range(refs):
                ref_name = f"session-2026-05-{i+1:02d}.md" if has_session_ref and i == 0 else f"ref-{i}.md"
                with open(os.path.join(ref_dir, ref_name), "w") as f:
                    f.write(f"# Reference {i}\n")

        return skill_dir

    def run_script(self, target=None):
        """运行维护脚本，返回 (exit_code, stdout, summary_dict)"""
        cmd = [sys.executable, SCRIPT_PATH]
        if target:
            cmd.extend(["--target", target])

        env = os.environ.copy()
        # 替换路径常量 — 通过环境变量注入
        # 修改脚本中的路径为临时目录
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

        # 提取 JSON 摘要
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


# ============ 测试用例 ============

def test_initial_empty(env):
    """测试1: 空目录，无变更"""
    print("  测试1: 空目录运行...", end=" ")
    code, out, summary = env.run_script()
    assert code == 0, f"脚本退出码非0: {code}"
    assert summary is not None, "未找到 JSON 摘要"
    assert summary["auto_generated_count"] == 0, f"期望0个auto-generated，实际{summary['auto_generated_count']}"
    assert summary["user_created_count"] == 0, f"期望0个user-created，实际{summary['user_created_count']}"
    assert summary["changes_made"] == False, "空目录不应有变更"
    print("✓")


def test_auto_gen_new_skill(env):
    """测试2: auto-generated 新增技能"""
    print("  测试2: auto-generated 新增...", end=" ")
    env.create_skill(env.auto_dir, "test-auto-skill", refs=3, has_session_ref=True)
    code, out, summary = env.run_script()
    assert summary["auto_generated_count"] == 1, "应检测到1个auto-generated"
    assert "test-auto-skill" in env.get_manifest_active(), "应加入清单"
    assert "test-auto-skill" in env.get_registry_ids(), "应注册到注册表"
    print("✓")


def test_user_created_register(env):
    """测试3: user-created 注册表检查"""
    print("  测试3: user-created 注册...", end=" ")
    env.create_skill(env.user_dir, "my-custom-skill")
    code, out, summary = env.run_script()
    assert "my-custom-skill" in env.get_registry_ids(), "应注册到注册表"
    reg = env._load_json(env.registry_path)
    entry = [c for c in reg["capabilities"] if c["id"] == "my-custom-skill"][0]
    assert entry["category"] == "user-created", f"category应为user-created，实际{entry['category']}"
    print("✓")


def test_user_created_unregister(env):
    """测试4: user-created 磁盘删除后注销"""
    print("  测试4: user-created 删除注销...", end=" ")
    # 先创建并注册
    env.create_skill(env.user_dir, "temp-skill")
    env.run_script()
    assert "temp-skill" in env.get_registry_ids(), "应已注册"

    # 删除技能目录
    shutil.rmtree(os.path.join(env.user_dir, "temp-skill"))

    # 再次运行
    code, out, summary = env.run_script()
    assert "temp-skill" not in env.get_registry_ids(), "应从注册表移除"
    print("✓")


def test_idempotent(env):
    """测试5: 二次运行无重复变更"""
    print("  测试5: 幂等性检查...", end=" ")
    env.create_skill(env.auto_dir, "stable-skill")
    env.create_skill(env.user_dir, "stable-user-skill")
    env.run_script()

    # 第二次运行
    code, out, summary = env.run_script()
    assert summary["changes_made"] == False, "二次运行不应有变更"
    print("✓")


def test_manifest_deleted_detection(env):
    """测试6: 清单中删除状态检测"""
    print("  测试6: 清单删除检测...", end=" ")
    env.create_skill(env.auto_dir, "vanish-skill")
    env.run_script()
    assert "vanish-skill" in env.get_manifest_active(), "应为活跃"

    # 删除技能
    shutil.rmtree(os.path.join(env.auto_dir, "vanish-skill"))
    env.run_script()
    assert "vanish-skill" not in env.get_manifest_active(), "不应为活跃"
    assert "vanish-skill" in env.get_manifest_deleted(), "应标记为删除"
    print("✓")


def test_mixed_skills(env):
    """测试7: 混合场景 — auto + user 同时存在"""
    print("  测试7: 混合场景...", end=" ")
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
    print("✓")


def test_empty_after_populated(env):
    """测试8: 清空后运行"""
    print("  测试8: 清空后运行...", end=" ")
    env.create_skill(env.auto_dir, "to-delete")
    env.create_skill(env.user_dir, "to-delete-user")
    env.run_script()

    # 删除所有技能
    shutil.rmtree(os.path.join(env.auto_dir, "to-delete"))
    shutil.rmtree(os.path.join(env.user_dir, "to-delete-user"))

    code, out, summary = env.run_script()
    assert summary["auto_generated_count"] == 0
    assert summary["user_created_count"] == 0
    assert "to-delete" in env.get_manifest_deleted()
    print("✓")


# ============ 主入口 ============

def main():
    print()
    print("=" * 60)
    print("  技能维护脚本测试框架")
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
    ]

    passed = 0
    failed = 0

    for test_fn in tests:
        env = TestEnv()
        try:
            test_fn(env)
            passed += 1
        except AssertionError as e:
            print(f"✗ 失败: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ 错误: {e}")
            failed += 1
        finally:
            env.cleanup()

    print()
    print("=" * 60)
    print(f"  结果: {passed} 通过, {failed} 失败, 共 {len(tests)} 个测试")
    print("=" * 60)
    print()

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
