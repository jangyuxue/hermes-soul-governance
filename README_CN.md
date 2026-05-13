<p align="center">
  <br>
  <b>SOUL.md 治理框架</b><br>
  <i>用不可变治理层替代 Hermes Agent 脆弱的记忆压缩循环。</i>
</p>

<p align="center">
  <a href="https://github.com/jangyuxue/hermes-soul-governance/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="MIT License"></a>
  <a href="#"><img src="https://img.shields.io/badge/python-3.8%2B-blue" alt="Python 3.8+"></a>
  <a href="#"><img src="https://img.shields.io/badge/tests-11%20passing-brightgreen" alt="Tests Passing"></a>
  <a href="https://github.com/jangyuxue/hermes-soul-governance/stargazers"><img src="https://img.shields.io/github/stars/jangyuxue/hermes-soul-governance?style=social" alt="Stars"></a>
</p>

```mermaid
flowchart TD
    subgraph Native["⚡ Hermes 原生记忆系统"]
        direction TB
        A1[Agent 调用 memory() 写入] --> B1[MEMORY.md / USER.md]
        B1 --> C1{超出容量限制？\n2200 / 1375 字符}
        C1 -->|是| D1[自动压缩：\n合并条目、丢弃上下文]
        D1 --> E1[上下文退化。\n规则被覆盖。\n数据丢失。]
        E1 -.-> B1
        C1 -->|否| F1[追加写入。\n无分类。\n无优先级。]
    end

    subgraph Soul["🛡️ SOUL.md 治理框架"]
        direction TB
        A2[Agent 调用 write_file] --> B2{先读后写\n检查}
        B2 -->|文件已存在| C2[读取完整内容 →\n合并新旧数据]
        B2 -->|文件不存在| D2[直接写入]
        C2 --> E2[写入分类文件]
        D2 --> E2
        E2 --> F2[写后验证：\nread_file 确认完整性]
        F2 --> G2[✅ 数据保留。\n有分类。\n可审计。]
    end

    Native -->|"问题：数据随时间退化"| Soul
```

> **Hermes Agent 原生的 `MEMORY.md` 仅有 2200 字符上限，自动压缩循环会静默丢弃上下文。**
> SOUL.md 用**只读治理锚点** + **结构化文件持久化**替代它——无压缩，无数据丢失。

## 30 秒快速上手

```bash
# 1. 部署框架模板到你的 Hermes 安装目录
cp -r framework/* ~/.hermes/

# 2. 配置你的角色和语言
vim ~/.hermes/SOUL.md
#    → 第 1 节：替换 <YOUR_ROLE> 和 <YOUR_LANGUAGE>

# 3. 关闭 Hermes 原生记忆系统
hermes config set memory.memory_enabled false
hermes config set memory.user_profile_enabled false

# 4. 运行维护脚本，同步技能注册表
~/.hermes/hermes-agent/venv/bin/python \
  ~/.hermes/skills/user-created/skill-maintenance/scripts/maintain.py

# 5. 验证
~/.hermes/hermes-agent/venv/bin/python \
  ~/.hermes/skills/user-created/skill-maintenance/scripts/maintain.py
# 预期输出："No changes" — 一切同步
```

[完整部署指南 →](#快速开始)

---

## 前置条件

本框架专为 **Hermes Agent** 设计。使用前必须已安装并正常运行 Hermes Agent。

框架中引用的路径均基于默认安装路径：

```
~/.hermes/
├── hermes-agent/           ← 源码
│   └── venv/bin/python     ← Python 解释器（脚本使用）
├── config.yaml             ← 配置文件
└── SOUL.md                 ← 本框架（新增此文件）
```

如果安装路径不同，请相应调整脚本中的 Python 解释器路径。

---

## 背景

### 1.1 记忆系统缺陷

Hermes Agent 将持久性记忆存储在 `MEMORY.md`（2200 字符上限）和 `USER.md`（1375 字符上限）两个文件中。写入超出容量时，系统自动触发压缩流程——合并已有条目、丢弃上下文、重写文件以腾出空间。每次写满后重复此流程。

经过多次循环后，出现以下问题：

- **缺乏分类隔离** — 偏好、环境配置、工作流记录、系统自动总结混合在同一个文件中。
- **缺乏优先级保留** — 压缩对所有条目一视同仁，近期信息与过期信息被同等处理。
- **写入时无法执行规则** — agent 通过工具函数写入，不会先读取文件内容。规则仅在文件写满需要压缩时才被读取。
- **上下文退化** — 压缩后的内容在各轮对话间持续注入，降低回复一致性。

这些问题的根源在架构层面：两个文件既可写入又会自动注入。定义其中的规则可能在写入时被覆盖或忽略。

### 1.2 技能系统缺陷

Hermes Agent 的系统提示词中有一句指令：

> *"完成复杂任务（5+ 次工具调用）、修复棘手错误或发现非平凡工作流后，使用 skill_manage 将方法保存为技能。"*

此机制只开了创建的口子，没有配套的维护工具：

- **无过期机制** — 技能创建后永久存在于磁盘。
- **无质量校验** — 格式异常或内容为空的技能同样通过。
- **无重复检测** — 新技能不与已有技能进行比较。
- **无自动注册** — 创建的技能不会自动加入 `user_capabilities.json`。

结果是单向管道：只有创建，没有维护。

### 1.3 本框架的范围

本框架针对上述两个问题提供解决方案。

---

## SOUL.md — 核心文件

### SOUL.md 的独特之处

`~/.hermes/SOUL.md` 是本框架的核心文件。它有两个区别于 `MEMORY.md` 和 `USER.md` 的特性：

| 特性 | `MEMORY.md` / `USER.md` | `SOUL.md` |
|------|------------------------|-----------|
| 注入方式 | 自动注入（可配置） | 自动注入（不可关闭） |
| 写入入口 | agent 可通过 `memory()` 写入 | **不存在写函数** |
| 容量限制 | 2200 / 1375 字符 | 不限制 |
| 提示词优先级 | 在系统提示词之后 | **首位**（`prompt_parts[0]`） |

因为代码库中没有 SOUL.md 的写入函数，agent 无法通过任何工具调用修改它。这使其成为一个只读锚点：规则跨会话持续有效，不会被记忆操作覆盖。

原生命令系统通过配置关闭：

```yaml
# config.yaml
memory:
  memory_enabled: false
  user_profile_enabled: false
```

### 各章节详解

#### 第 1 节：身份与角色

定义 agent 的人设。**部署后必须编辑这一节**：

```markdown
1.1 Role: <YOUR_ROLE>
# 示例："后端工程师", "数据分析师"

1.2 Language: <YOUR_LANGUAGE>
# 示例："中文", "English"
```

#### 第 2 节：响应标准

对 agent 输出的质量约束：
- 必须以真问题结尾（不要"对吗？""明白了吗？"）
- 必须引用证据（回答前先查文件）
- 模式切换：探索模式（头脑风暴）vs 执行模式（精确执行）

#### 第 3 节：持久化写入协议

**这是记忆系统的核心。**定义了：

- **3.1**：何时写入（用户说"记住"、陈述偏好、纠正事实）
- **3.2**：如何写入（只能用 `write_file`，禁用 `memory()`）
- **3.3-3.4**：写前先读（防止数据损坏）
- **3.5**：触发关键词匹配（将用户输入映射到具体文件）
- **3.5.1**：关键词到文件的映射表：

```
"我喜欢...", "我习惯..."         → user-memory/preferences.md
"我是...", "我叫..."             → user-memory/user-profile.md
"我系统是...", "我用了..."        → user-memory/environment-setup.md
"我做XX的步骤..."                 → user-memory/workflows/<name>.md
"加一个技能", "注册"             → user-registry/user_capabilities.json
```

这替代了默认记忆系统，使用结构化、分类化的文件存储。

#### 第 4 节：检索协议

定义 agent 如何读取你的存储信息：
- 优先搜索：通过 `search_files` 关键词匹配，只读匹配段落
- 按需加载：不一次性加载全部 `user-memory/` 文件
- 新鲜度规则：始终从文件读取，不依赖会话上下文

#### 第 5 节：操作约束

文件操作规则：
- **5.1**：修改前备份（到 `user-memory/.backup/`）
- **5.3**：受保护目录（禁止删除 `skills/`、`output/`、`memories/` 下的文件）
- **5.4**：输出路径 `~/.hermes/output/{images|documents|data|temp}/`
- **5.5**：**重要** — 所有 Python 操作必须使用 `~/.hermes/hermes-agent/venv/bin/python`，不能使用系统 `python3`。此 venv 包含所需的依赖包。部分发行版的系统 Python 是外部管理的，直接使用会失败。

#### 第 6 节：技能分发

如何将用户请求路由到已注册的技能：

```
用户输入 → capability_finder.py → user_capabilities.json
  → 匹配成功 → 执行技能脚本
  → 无匹配 → agent 直接回复
```

`capability_finder.py` 位于 `~/.hermes/user-registry/capability_finder.py`。评分算法：精确匹配（100）、包含匹配（50）、被包含匹配（10）。

#### 第 7 节：技能创建与存储

定义技能存放位置和维护方式：

| 类型 | 位置 | 创建者 | 维护者 |
|------|------|--------|--------|
| 自动生成 | `auto-generated/` | Agent（复杂任务后） | `maintain.py` + agent |
| 用户创建 | `user-created/` | 用户 | `maintain.py`（仅注册表） |

维护脚本（`maintain.py`）位于 `~/.hermes/skills/user-created/skill-maintenance/scripts/maintain.py`：
- 扫描两个目录
- 自动注册新技能到 `user_capabilities.json`
- 自动注销已删除的技能
- 修复格式异常的 `SKILL.md`（补全 frontmatter、name、description）
- 校验触发词（空触发词 = 技能不可达）

#### 第 8 节：合规与审计

执行规则：
- 每次写入必须验证（写后执行 `read_file`）
- 写入失败必须报告并从备份恢复
- 任何偏离规则的行为必须立即报告

---

## 快速开始

```bash
# 0. 前置条件：必须已安装 Hermes Agent
#    如未安装：curl -fsSL https://raw.githubusercontent.com/... | bash

# 1. 部署框架模板
cp -r framework/* ~/.hermes/

#    这会向 ~/.hermes/ 添加 SOUL.md、user-memory/、user-registry/、
#    skills/、output/，并覆盖默认的 SOUL.md。
#    如果之前自定义过 SOUL.md，请先备份。

# 2. 编辑 SOUL.md — 替换第 1 节的占位符
vim ~/.hermes/SOUL.md
#    1.1 Role: <YOUR_ROLE>       → "后端工程师"
#    1.2 Language: <YOUR_LANGUAGE> → "中文"

# 3. 关闭 Hermes 默认记忆
#    原生的 MEMORY.md 和 USER.md 不再使用。
#    可以保留（不影响）或删除。
hermes config set memory.memory_enabled false
hermes config set memory.user_profile_enabled false
#
#    如果 hermes CLI 不可用，直接编辑 config.yaml：
#
#    vim ~/.hermes/config.yaml
#
#    找到或添加 memory 配置段：
#
#    memory:
#      memory_enabled: false
#      user_profile_enabled: false
#
#    保存文件后重启 Hermes 使配置生效。

# 4. 运行维护脚本，注册已有技能
~/.hermes/hermes-agent/venv/bin/python \
  ~/.hermes/skills/user-created/skill-maintenance/scripts/maintain.py

# 5. 验证一切正常
~/.hermes/hermes-agent/venv/bin/python \
  ~/.hermes/skills/user-created/skill-maintenance/scripts/maintain.py
# 预期输出："No changes"（说明一切同步）
```

---

## 仓库内容

```
hermes-soul-governance/
├── README.md                    # 本文档（英文版）
├── README_CN.md                 # 中文版
├── SOUL.md                      # 治理规则（框架核心）
├── .gitignore
├── framework/                   # 可部署模板 — 复制到 ~/.hermes/
│   ├── README.md                # 目录说明
│   ├── SOUL.md                  # 与根目录 SOUL.md 相同（含占位符）
│   ├── user-memory/
│   │   ├── README.md            # 文件功能与触发词说明
│   │   ├── preferences.md       # 沟通风格、习惯
│   │   ├── user-profile.md      # 身份、角色
│   │   ├── environment-setup.md # 工具链、路径
│   │   ├── .backup/             # 写入前自动备份
│   │   └── workflows/
│   │       └── workflow-commands.json  # 机器可执行指令
│   ├── user-registry/
│   │   ├── README.md            # 组件说明
│   │   ├── user_capabilities.json
│   │   └── capability_finder.py
│   ├── skills/
│   │   ├── auto-generated/
│   │   │   ├── README.md
│   │   │   └── self_created_skills.json
│   │   └── user-created/
│   │       └── skill-maintenance/
│   │           ├── scripts/maintain.py
│   │           ├── test_maintain.py
│   │           └── SKILL.md
│   └── output/                  # 输出目录
│       ├── README.md
│       ├── images/
│       ├── documents/
│       ├── data/
│       └── temp/
├── examples/
│   ├── auto-generated/self_created_skills.json
│   └── user_capabilities.json
└── framework/skills/user-created/skill-maintenance/
    ├── scripts/maintain.py
    ├── test_maintain.py
    └── SKILL.md
```

---

## 测试

```bash
python3 framework/skills/user-created/skill-maintenance/test_maintain.py
```

11 个测试用例：空目录、新技能检测、SKILL.md 自动修复、注册表同步、删除注销、幂等性、清单一致性、混合类型、校验警告、清空状态。全部通过。

---

## 已知限制

1. **规则执行** — SOUL.md 能确保规则加载到系统提示词中，但模型是否遵守取决于其指令遵循能力。这是基于 LLM 的系统的固有属性。

2. **技能分类** — 维护脚本使用启发式标准（session 引用文件、引用数量、文件大小）判断技能类型。当前规则与现有模式匹配，但 agent 行为变化时可能需要调整。

---

## 开源许可证

MIT
