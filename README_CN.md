<p align="center">
  <br>
  <b>SOUL.md 治理框架</b><br>
  <i>修复 Hermes Agent 残疾的记忆、没人管的技能、缺失的治理层</i>
</p>

<br>

---

## 解决了什么问题

### 1. 记忆功能残疾

Hermes 把记忆存在 `MEMORY.md` 和 `USER.md` 里——分别只有 **2200 和 1375 个字符**。加起来不到 3600 个字符，要塞下你的偏好、环境、身份、所有跨会话有用的信息。

写满之后，Hermes 会**自动压缩**已有内容腾空间。合并事实、丢掉上下文、继续写——直到再次写满，再次压缩。循环往复。

结果是：这两个文件变成一个垃圾场。偏好、环境配置、工作流、自动总结，全混在一起。注入到系统提示词后逻辑混乱，输出越来越偏离预期，维护成本远大于收益。

更糟的是，原生记忆系统**没有规则执行机制**。agent 通过 `memory()` 工具直接写入，不会先读文件里的约束条件。你写在 MEMORY.md 里的规则，它根本不知道。只有当文件写满、需要压缩的时候，它才去读——为的是腾空间，不是遵守规则。

### 2. 技能系统管生不管养

Hermes 鼓励在复杂任务后保存技能，但没有配套的维护工具：

- **没有过期策略** — 技能建了就永远躺在磁盘上
- **没有质量门禁** — 不管结构好坏都通过
- **没有重复检测** — 不会检查新技能是否跟已有技能重叠
- **没有自动注册** — 创建后不会加入 `user_capabilities.json`，agent 搜不到

结果：技能池越来越臃肿。重复的、过期的、垃圾的技能堆在一起，没人知道哪些有用。

### 3. 接入网关后没有隐私隔离

接入飞书、Telegram 等网关后，多用户共享同一个进程、同一个数据库、同一个 OS 用户权限。`session_search` 没有 `user_id` 过滤——任何人可以搜任何人的对话。`read_file` 不受审批机制限制，配置文件、API key、其他人的聊天记录都可以读。

现有防御（`allowed_chats`、操作审批、SOUL.md 规则）都依赖模型自律，不是真正的隔离。

---

## 这个方案做了什么

### 架构

```
SOUL.md (无条件注入，系统无法写入)
  ├── user-memory/          ← 结构化持久化（无容量限制，不会自动压缩）
  │   ├── preferences.md
  │   ├── user-profile.md
  │   ├── environment-setup.md
  │   └── workflows/
  ├── user-registry/        ← 自定义技能管理
  │   ├── user_capabilities.json
  │   └── capability_finder.py
  └── skills/
      ├── auto-generated/   ← Agent 自动生成
      └── user-created/     ← 用户创建
```

### 第一层：SOUL.md — 只读规则锚点

SOUL.md 是唯一同时满足两个条件的文件：**无条件注入**（没有开关，总是加载）、**系统无法写入**（没有对应的写函数）。放在这里的规则不会被记忆压缩机制覆盖。

核心约束：
- 禁止调用 `memory(action='add')` — 通过配置关闭
- 写入协议：读 → 合并 → 写 → 验证
- 触发词映射（偏好→preferences.md，身份→user-profile.md 等）
- 检索优先（关键词匹配优先于全文读取）

### 第二层：user-memory/ — 结构化持久化

替代 `MEMORY.md` 和 `USER.md`，使用无容量限制的分类文件：

| 文件 | 存什么 | 什么时候读 |
|------|--------|-----------|
| `preferences.md` | 沟通风格、语气、习惯 | 用户问偏好时 |
| `user-profile.md` | 身份、角色、领域 | 任务涉及用户上下文时 |
| `environment-setup.md` | 系统配置、路径、工具 | 需要执行操作时 |
| `workflows/<name>.md` | 步骤流程 | 触发工作流时 |

**不自动注入系统提示词**——按需读取。大部分轮次不消耗上下文窗口。

### 第三层：user-registry/ — 技能管理

自定义技能需要注册、触发词匹配和维护，系统自带的机制不够用：

| 文件 | 用途 |
|------|------|
| `user_capabilities.json` | 技能注册表（触发词、脚本路径、配置） |
| `capability_finder.py` | 触发词匹配器（精确=100，包含=50，被包含=10） |
| `maintain.py` | 自动检测新增/删除技能，同步注册表，修复 SKILL.md |

---

## 功能特性

- **关闭残疾的记忆** — `memory_enabled: false`，用结构化文件替代
- **无限存储** — 不限 2200/1375 字符，写到磁盘满为止
- **不自动压缩** — 事实保持原样，不会被合并或丢弃
- **技能自动注册** — 放目录就行，`maintain.py` 自动处理
- **SKILL.md 自动修复** — 缺 frontmatter、name、description 自动补全
- **校验提醒** — 触发词为空、脚本路径不存在、孤立技能未注册
- **闭环** — 创建 → 注册 → 匹配 → 执行 → 清理
- **不用手动改 JSON** — `user_capabilities.json` 完全由脚本管理
- **隐私防护** — `allowed_chats` 白名单、SOUL.md 只读

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

用户说话 → SOUL.md 3.5 匹配触发关键词：

| 关键词 | 目标文件 |
|--------|---------|
| "我喜欢...", "我习惯...", "你说话要..." | `user-memory/preferences.md` |
| "我是...", "我叫...", "我负责..." | `user-memory/user-profile.md` |
| "我系统是...", "我装了...", "我用的是..." | `user-memory/environment-setup.md` |
| "我做XX的步骤...", "先A再B..." | `user-memory/workflows/<name>.md` |

写入协议：`read_file → 合并 → write_file → read_file 验证`

### 技能生命周期

```
新技能放入目录 → maintain.py 检测到
  → 自动修复 SKILL.md（缺 frontmatter 自动补全）
  → 注册到 user_capabilities.json
  → Agent 补全触发词
  → 技能可被匹配

技能被删除 → maintain.py 检测到 → 从注册表移除
```

### 触发词匹配

```
用户说话 → capability_finder.py
  → 评分：精确=100，包含=50，被包含=10
  → 返回最佳匹配
    → "skill" → 执行脚本
    → "direct_answer" → agent 直接回复
```

---

## 目录结构

```
~/.hermes/
├── SOUL.md                            ← 治理规则（只读锚点）
├── skills/
│   ├── auto-generated/                ← Agent 自动学习到的技能
│   │   ├── self_created_skills.json   ← 清单文件
│   │   └── <skill-name>/
│   ├── user-created/                  ← 用户创建的技能
│   │   └── <skill-name>/
│   └── <category>/                    ← 内置技能
├── user-memory/                       ← 结构化持久化
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

扫描 `auto-generated/` 和 `user-created/`，检测新增/删除技能，同步注册表，自动修复 SKILL.md，校验触发词和脚本路径。

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

11 个测试：空目录、新技能检测、SKILL.md 自动修复、注册表同步、删除注销、幂等性、清单检测、混合场景、校验警告、清空状态 — **全部通过**。

---

## 设计原则

1. **单一真相源** — SOUL.md 是唯一的治理文件
2. **读前写** — 先读再写，防止数据损坏
3. **职责分离** — 自动生成、用户创建、内置技能目录独立
4. **非破坏性** — 脚本绝不修改用户创建的技能内容
5. **可追溯** — 所有变更都记录快照

---

## 已知问题

- **模型自律** — SOUL.md 能确保规则被读到，不能确保一定遵守。当前可用，不同模型可能有差异
- **网关隐私** — `session_search` 没有 `user_id` 隔离，用 `allowed_chats` 白名单缓解
- **技能分类** — 基于启发式规则（session 引用、文件大小），当前可用，未来可能需要调整

---

## 开源许可证

MIT
