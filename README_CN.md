<p align="center">
  <br>
  <b>SOUL.md 治理框架</b><br>
  <i>为 Hermes Agent 提供结构化治理层 — 以文件化持久存储替代默认记忆系统，实现技能生命周期的自动化管理。</i>
</p>

<br>

---

## 背景

Hermes Agent 通过两种机制管理持久数据：

**1. `MEMORY.md` / `USER.md` 自动压缩机制**

两个文件的容量上限分别为 2200 和 1375 个字符。写入超出容量时，系统自动对已有内容进行压缩——合并事实、丢弃上下文、重写条目。经多次循环后，文件积累了大量未按类别或优先级区分的数据。偏好、环境配置、工作流记录、系统自动总结混合在一起。这些内容注入系统提示词后，会降低回复的连贯性，并增加维护成本。

**2. 技能系统的单向创建**

在涉及多步工具调用的任务完成后，系统指示 agent 将处理方式保存为技能。但配套的维护机制缺失：无过期策略、无质量校验、无重复检测、无自动注册。技能在磁盘上不断积累，但未进入 `user_capabilities.json`，触发词匹配系统无法检索到它们。

上述问题的根本原因相同：在可写入文件中定义的规则（`MEMORY.md`、`USER.md`），在写入时无法被强制执行。agent 通过工具函数写入，这些函数不会先读取文件内容。规则只在文件写满、系统读取内容以腾出空间时才生效，这不是可靠的执行方式。

SOUL.md（`~/.hermes/SOUL.md`）提供了不同的注入路径——每次会话启动时无条件加载，且代码库中不存在对应的写入函数。这使其成为一个无法被记忆系统覆盖的只读锚点。

---

## 方案架构

### 第一层：SOUL.md — 只读规则锚点

SOUL.md 通过 `load_soul_md()` 在每轮对话中自动加载，放置在 `prompt_parts[0]`（最高优先级）。系统没有任何写入该文件的接口。此文件中的规则不会被记忆操作修改。

该文件定义了：
- 写入协议：读 → 合并 → 写 → 验证（第 3 节）
- 关键词到文件的映射表，用于结构化持久化（第 3.5.1 节）
- 优先搜索、按需加载的检索策略（第 4 节）
- 技能创建条件和存储路径（第 7 节）

原生记忆系统通过配置关闭：

```yaml
memory:
  memory_enabled: false
  user_profile_enabled: false
```

这阻止了 `MEMORY.md` 和 `USER.md` 的注入与写入。

### 第二层：user-memory/ — 文件化持久存储

替代 `MEMORY.md` / `USER.md`，使用分类化、无容量上限的文件：

| 路径 | 存储内容 | 读取时机 |
|------|---------|---------|
| `user-memory/preferences.md` | 沟通风格、语气、习惯 | 用户提及偏好时 |
| `user-memory/user-profile.md` | 身份、角色、领域 | 任务需要用户上下文时 |
| `user-memory/environment-setup.md` | 工具链、路径、已安装包 | 执行需要环境信息时 |
| `user-memory/workflows/<name>.md` | 步骤流程 | 触发特定工作流时 |

这些文件不会自动注入系统提示词。通过 `read_file` / `search_files` 按需加载。大部分轮次不消耗上下文窗口。文件大小仅受磁盘容量限制。

写入协议（第 3.3-3.4 节）：
1. 写入前：通过 `search_files` 或 `read_file` 确认文件是否存在
2. 文件存在：读取完整内容 → 合并新内容 → 写入合并结果
3. 文件不存在：直接写入
4. 写入后：`read_file` 验证内容完整性

### 第三层：user-registry/ — 技能注册表

自定义技能需要显式注册才能被触发词匹配系统检索到。三个组件：

| 组件 | 功能 |
|------|------|
| `user_capabilities.json` | 注册表：技能 ID、触发词、脚本路径、依赖、示例、配置 |
| `capability_finder.py` | 触发词匹配器——评分算法：精确匹配=100，包含=50，被包含=10 |
| `workflow-commands.json` | 技能 ID 到机器可执行步骤的映射 |

### 技能维护 (maintain.py)

两个目录，两种行为：

**auto-generated/** — Agent 在复杂任务后自动创建的技能。
- 磁盘新增 → 加入 `self_created_skills.json` 清单 + 注册到 `user_capabilities.json`
- 磁盘删除 → 清单标记为已删除 + 从注册表注销
- `SKILL.md` 格式异常 → 自动修复（补全 frontmatter、name、description）

**user-created/** — 用户自定义的技能。
- 磁盘新增 → 注册到 `user_capabilities.json`
- 磁盘删除 → 从注册表注销
- 不修改技能内容

校验检查（第 C 节）：
- 触发词为空（技能已注册但无法被匹配）
- 脚本路径不存在
- `SKILL.md` 格式异常（自动修复并报告）

---

## 快速开始

```bash
# 1. 部署框架模板
cp -r framework/* ~/.hermes/

# 2. 配置身份 — 编辑 ~/.hermes/SOUL.md 第 1 节
#    - 将 <YOUR_ROLE> 替换为你的角色（如 "Backend Engineer"）
#    - 将 <YOUR_LANGUAGE> 替换为你的语言（如 "中文", "English"）

# 3. 关闭原生记忆系统
hermes config set memory.memory_enabled false
hermes config set memory.user_profile_enabled false

# 4. 运行维护脚本，注册已有技能
~/.hermes/hermes-agent/venv/bin/python \
  ~/.hermes/skills/user-created/skill-maintenance/scripts/maintain.py
```

---

## 仓库内容

```
hermes-soul-governance/
├── README.md                    # 本文档（英文版）
├── README_CN.md                 # 中文版
├── SOUL.md                      # 治理规则（单一真相源）
├── .gitignore                   # 排除用户数据
├── framework/                   # 可部署模板
│   ├── SOUL.md                  # 可自定义的规则（编辑第 1 节）
│   ├── user-memory/             # 结构化持久化（agent 自动填充）
│   │   ├── preferences.md
│   │   ├── user-profile.md
│   │   ├── environment-setup.md
│   │   └── workflows/
│   ├── user-registry/
│   │   ├── user_capabilities.json
│   │   └── capability_finder.py
│   └── skills/
│       ├── auto-generated/      # Agent 技能
│       │   └── self_created_skills.json
│       └── user-created/
│           └── skill-maintenance/
│               ├── scripts/maintain.py
│               ├── test_maintain.py
│               └── SKILL.md
├── examples/
│   ├── auto-generated/self_created_skills.json
│   └── user_capabilities.json
└── framework/skills/user-created/skill-maintenance/
    ├── scripts/maintain.py      # 维护脚本
    ├── test_maintain.py         # 11 个测试用例
    └── SKILL.md                 # 面向 agent 的技能文档
```

---

## 测试

```bash
python3 framework/skills/user-created/skill-maintenance/test_maintain.py
```

测试套件：空目录、新技能检测、SKILL.md 自动修复、注册表同步、删除注销、幂等性、清单一致性、混合技能类型、校验警告、清空后状态。**11 个用例，全部通过。**

---

## 已知限制

1. **规则执行** — SOUL.md 能够确保规则加载到系统提示词中，但模型能否遵守取决于其指令遵循能力。这是基于 LLM 的系统的固有属性，并非此框架独有问题。

2. **技能分类** — 维护脚本使用启发式标准判断技能的生成方式（session 引用文件、引用数量、文件大小、章节数量、是否存在可执行脚本）。当前规则与现有生成模式匹配，但 agent 行为发生变化时可能需要调整。

3. **网关隐私** — 通过消息网关（Telegram、飞书等）运行时，`session_search` 对整个 `state.db` 进行操作，没有按用户隔离。这是 Hermes Agent 单用户数据模型的架构限制。当前缓解措施：使用 `allowed_chats` 将访问限制在受信用户范围内。不能替代真正的多租户隔离。

---

## 开源许可证

MIT
