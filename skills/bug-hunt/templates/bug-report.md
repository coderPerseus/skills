# <项目>: <一句话症状>

<!--
Bug report template — fill in each section. Delete this comment block before saving.
Filename convention: docs/bugfix-<kebab-slug>.md
-->

- **Date**: YYYY-MM-DD
- **Scope**: <which platform / page / route / user segment>
- **Severity**: P0 / P1 / P2 / P3
- **Affected systems**: <files / services / dependencies>

## 一、Bug 现象

<!-- What the user sees. Be concrete: include URL, role, screenshots if available. -->

- 触发条件: <minimal repro>
- 用户观察: <observable symptom>
- 不影响的范围: <what continues to work — useful for diff isolation>

## 二、Bug 产生的原因

<!-- The root cause. If multi-layered, use the indent format. -->

```
<Outer symptom>
  └─ Proximate cause: <closest reason>
      └─ Underlying cause: <next layer>
          └─ Root cause: <innermost reason>
```

### Layer 1: <name>

<technical explanation + evidence>

### Layer 2: <name>

<technical explanation + evidence>

### Layer 3 (root): <name>

<technical explanation + evidence>

## 三、Bug 排查 + 修复思路

### 1. Phase 1 — 自顶向下定位

| 层级 | 文件:行 | 关键值 |
|---|---|---|
| 渲染 | `file:line` | `condition` |
| 数据源 | `file:line` | `where the value comes from` |
| ... | ... | ... |

Phase 1 出口的命名假设:
- H1: <hypothesis>
- H2: <hypothesis>

### 2. Phase 2 — 全链路埋点

使用前缀 `[<PREFIX>]`,在 N 处加结构化日志:

- `<file>` — log at <where> capturing <fields>
- ...

样例输出(关键字段):

```
<paste actual log excerpt>
```

### 3. Phase 3 — 分层根因

(See section 二 above for the chain.)

每一层的证据来源:

| 层 | 证据 |
|---|---|
| Layer 1 | <log line / file inspection> |
| ... | ... |

### 4. 方案选型

| 候选 | 评估 |
|---|---|
| 方案 A | <why dismissed / chosen> |
| 方案 B | ... |
| ✅ 选定方案 | <why this one> |

## 四、修复方案

### 改动 1: <slug>

`<file>`:

```diff
- <old>
+ <new>
```

理由: <why this change>

### 改动 2: <slug>

...

### 不动什么 / 兼容性说明

- 保持 X 不动,因为 ...
- 其他平台 / 路径不受影响:<evidence>

## 五、验证结果

| 指标 | 修复前 | 修复后 |
|---|---|---|
| <metric 1> | <before> | <after> |
| <metric 2> | <before> | <after> |
| <symptom>  | <before> | <after> |

成功标准对照:
- ✅ <criterion 1 from Phase 0>
- ✅ <criterion 2>

## 六、改动文件清单

| 文件 | 改动 |
|---|---|
| `<file>` | <summary> |
| `<file>` | <summary> |

## 七、后续建议

1. **<follow-up name>** — <why> / <suggested action>
2. **<follow-up name>** — ...
3. **<follow-up name>** — ...

<!--
Recommended follow-up categories:
- Dependency hygiene (version drift was a cause → schedule reviews)
- Telemetry / monitoring (silent failure → add Sentry / structured log at the suspect point)
- Regression test (data-shape bug → fixture-based test)
- Documentation (undocumented behavior → docs PR or team CLAUDE.md/AGENTS.md note)
-->
