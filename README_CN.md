<p align="center">
  <br>
  <b>SOUL.md 治理框架</b><br>
  <i>别再重复说。让 agent 记住、整理、进化。</i>
</p>

<br>

---

## 解决了什么问题

Hermes Agent 很强大，但开箱即用有几个痛点：

- **没有持久记忆** — 每次对话都从零开始。你的偏好、环境、工作流，每次都要重新说
- **技能用完就丢** — 一次复杂的调试、一个棘手的工作流，做完就没了。下次 agent 还是不会
- **没有质量控制** — 自动生成的技能越来越多，哪些有用哪些过期，没人知道
- **触发词是空的** — 技能在磁盘上，但 agent 找不到，因为没人填触发词

结果就是：你不断重复说同样的话，agent 永远不会变聪明。

---

## 这个框架做了什么

**SOUL.md** 是 Hermes Agent 的治理层，把它从一个"会话级助手"变成一个"持续学习系统"。

三大能力：

| 能力 | 做什么 | 没有它 | 有它 |
|------|--------|--------|------|
| **结构化记忆** | 偏好、身份、环境、工作流存入持久文件 | Agent 下轮对话全忘光 | Agent 记住你的习惯、工具和流程 |
| **技能生命周期** | 技能自动注册、校验、清理 | 技能越堆越多，触发词永远空 | 技能可追踪、可匹配、有质量检查 |
| **触发词匹配** | 用户输入和所有技能触发词评分匹配 | Agent 找不到对的技能 | Agent 自动路由到正确的技能 |

---

## 功能特性

- **文件化记忆** — 偏好、身份、环境、工作流跨对话持久保存
- **自动注册** — 技能丢进目录，`maintain.py` 自动注册
- **自我修复** — `SKILL.md` 格式不对自动修复（缺 frontmatter、缺 name、缺 description）
- **校验提醒** — 触发词为空、脚本路径不存在、孤立技能未注册，都会警告
- **闭环** — 创建 → 注册 → 匹配 → 执行 → 清理，全自动化
- **不用手动改 JSON** — `user_capabilities.json` 完全由维护脚本管理
- **多语言支持** — 触发词用任何语言都可以

---

## 快速开始

```bash
# 1. 复制框架模板（包含所有文件）
cp -r framework/* ~/.hermes/

# 2. 编辑 SOUL.md 第 1 节（角色和语言）
vim ~/.hermes/SOUL.md

#    1.1 Role: <YOUR_ROLE>       → "后端工程师", "数据分析师" 等
#    1.2 Language: <YOUR_LANGUAGE> → "中文", "English" 等

# 3. 关闭 Hermes 默认记忆（本框架自己管理记忆）
hermes config set memory.memory_enabled false
hermes config set memory.user_profile_enabled false

# 4. 运行维护脚本
~/.hermes/hermes-agent/venv/bin/python \
  ~/.hermes/skills/user-created/skill-maintenance/scripts/maintain.py
```

---

## 工作流程

### 记忆管理

Agent 根据触发关键词将用户数据写入结构化文件：

| 文件 | 触发条件 |
|------|---------|
| `user-memory/preferences.md` | "我喜欢...", "我习惯...", "你说话要..." |
| `user-memory/user-profile.md` | "我是...", "我叫...", "我负责..." |
| `user-memory/environment-setup.md` | "我系统是...", "我装了...", "我用的是..." |
| `user-memory/workflows/<name>.md` | "我做XX的步骤...", "先A再B..." |

### 技能生命周期

```
新技能放入目录 → maintain.py 检测到
  → 自动修复 SKILL.md（缺少 frontmatter 自动补全）
  → 注册到 user_capabilities.json
  → Agent 补全触发词
  → 技能可被匹配

技能被删除 → maintain.py 检测到 → 从注册表中移除
```

两种技能类型：

| 类型 | 存放位置 | 创建者 | 管理者 |
|------|---------|--------|--------|
| 自动生成 | `auto-generated/` | Agent（完成复杂任务后） | maintain.py + agent |
| 用户创建 | `user-created/` | 用户 | maintain.py + agent |

### 技能匹配

```
用户说话 → capability_finder.py
  → 触发词评分：精确=100，包含=50，被包含=10
  → 返回最佳匹配
    → type="skill" → 执行脚本
    → type="direct_answer" → agent 直接回复
```

---

## 目录结构

```
~/.hermes/
├── SOUL.md                            ← 治理规则
├── skills/
│   ├── auto-generated/                ← Agent 自动学习到的技能
│   │   ├── self_created_skills.json   ← 清单文件
│   │   └── <skill-name>/
│   ├── user-created/                  ← 用户创建的技能
│   │   └── <skill-name>/
│   └── <category>/                    ← 内置技能
├── user-memory/                       ← Agent 自动填充
│   ├── preferences.md
│   ├── user-profile.md
│   ├── environment-setup.md
│   └── workflows/
└── user-registry/
    ├── user_capabilities.json         ← 技能注册表
    └── capability_finder.py           ← 触发词匹配器
```

---

## 脚本说明

### maintain.py

扫描 `auto-generated/` 和 `user-created/` 目录，检测新增/删除的技能，同步注册表，自动修复 SKILL.md 格式，校验触发词和脚本路径。

```bash
~/.hermes/hermes-agent/venv/bin/python \
  ~/.hermes/skills/user-created/skill-maintenance/scripts/maintain.py
```

### capability_finder.py

读取 `user_capabilities.json`，通过评分算法匹配用户输入到已注册技能。

```bash
~/.hermes/hermes-agent/venv/bin/python \
  ~/.hermes/user-registry/capability_finder.py "生成图片"
```

---

## 测试

```bash
python3 framework/skills/user-created/skill-maintenance/test_maintain.py
```

11 个测试用例：空目录、新技能检测、SKILL.md 自动修复、注册表同步、删除注销、幂等性、清单检测、混合场景、校验警告、清空状态 — **全部通过**。

---

## 设计原则

1. **单一真相源** — SOUL.md 是唯一的治理文件
2. **读前写** — 先读再写，防止数据损坏
3. **职责分离** — 自动生成、用户创建、内置技能目录独立
4. **非破坏性** — 脚本绝不修改用户创建的技能内容
5. **可追溯** — 所有变更都记录快照

---

## 开源许可证

MIT
