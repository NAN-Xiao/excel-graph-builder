# 游戏配置表证据系统 — 外部 RAG 系统接入指南 v5

> 面向需要接入本系统数据的 **外部 RAG 系统**，完整描述产物目录、四层召回架构、文件读取方式、数值分析模式，以及构建后回归/回退机制。

v5 重点更新：

- `EvidenceAssembler` 采用 `summary + drill-down` 双层证据结构
- 首屏证据新增 `hidden_but_available` 和 `fetch_hints`
- `analytical_result` 保留全量分析结果，同时新增 `analytical_result_visible` 供首轮问答直接使用
- 更明确地区分“底层完整数据”和“首屏给 LLM 的受控上下文”

边界说明：

- 本工程只产出离线数据文件。
- 本工程不提供在线查询接口（无 HTTP/RPC endpoint）。

---

## 目录

1. [系统架构概述](#1-系统架构概述)
2. [数据目录与发布约定](#2-数据目录与发布约定)
3. [快速接入（最小可用）](#3-快速接入最小可用)
4. [层1 — 表级召回层](#4-层1--表级召回层)
5. [层2 — 列级裁剪层](#5-层2--列级裁剪层)
6. [层3 — 行级取数层](#6-层3--行级取数层)
7. [层4 — 证据组装层](#7-层4--证据组装层)
8. [pack_array 候选关系](#8-pack_array-候选关系)
9. [调优与进阶](#9-调优与进阶)
10. [常见问题](#10-常见问题)

---

## 1. 系统架构概述

```
用户自然语言问题
        │
        ▼
┌───────────────────────────────────────────────────────┐
│  层1: 表级召回层                                       │
│  schema_summary.txt → LLM 意图提取 → 种子表           │
│  llm_chunks.jsonl   → 向量召回 top-K                  │
│  relation_graph.json → BFS 扩展邻居                   │
│  analysis.json      → centrality / module 加权排序    │
└────────────────────────┬──────────────────────────────┘
                         │ table_names: ["hero_base", ...]
                         ▼
┌───────────────────────────────────────────────────────┐
│  层2: 列级裁剪层                                       │
│  table_profiles.jsonl 每列携带：                       │
│    semantic_type  identifier/metric/enum/flag/...      │
│    domain_role    id_key/stat_atk/cost/level_grade/... │
│    metric_tag     hp/attack/cost/rate/...              │
│  EvidenceAssembler 按 query 词义打分，保留 ≤25 列      │
└────────────────────────┬──────────────────────────────┘
                         │ selected_columns
                         ▼
┌───────────────────────────────────────────────────────┐
│  层3: 行级取数层                                       │
│  RowRetriever.generate_predicates(query, profile)      │
│    → ID 精确匹配 / 枚举命中 / 数值范围谓词             │
│  RowRetriever.fetch_rows(profile, predicates)          │
│    → 回源读 Excel，只返回命中行块                      │
└────────────────────────┬──────────────────────────────┘
                         │ key_rows
                         ▼
┌───────────────────────────────────────────────────────┐
│  层4: 证据组装层                                       │
│  EvidenceAssembler.assemble()                          │
│    ① schema     — 裁剪后的列 schema                   │
│    ② join       — 表间 JOIN 路径                       │
│    ③ key_rows   — 谓词过滤行块（Markdown 表格）        │
│    ④ stat_summary — 数值/枚举统计摘要                  │
│    ⑤ hidden_but_available / fetch_hints               │
│  → 首轮摘要问答 + 二次继续取数                         │
└───────────────────────────────────────────────────────┘
```

---

## 2. 数据目录与发布约定

构建产物位于 `graph/` 目录。推荐外部 RAG 系统始终优先读取 `graph/current/`，不要直接消费 `graph/builds/<build_id>/`。

目录约定：

| 路径 | 含义 | 使用建议 |
|:--|:--|:--|
| `graph/current/` | 当前已发布、可在线消费的版本 | **默认读取这里** |
| `graph/latest_success/` | 最近一次通过校验的成功版本 | 回退 / 对账 |
| `graph/builds/<build_id>/` | 单次构建的独立版本目录 | 调试 / 历史追溯 |
| `graph/reports/<build_id>.json/.md` | 构建后回归报表 | 运维和验收 |
| `graph/regression_queries.json` | 构建后自动回归样例配置 | 推荐维护 |
| `graph/alerts.log` | 本地告警摘要 | 推荐监控 |

发布规则：

- 构建先写入 `graph/builds/<build_id>/`
- 然后执行完整性检查和回归
- 只有通过门槛才同步到 `graph/current/`
- 若出现 `P0`，则继续保留上一版 `graph/current/`，不会让坏版本覆盖线上

补充说明：

- `增量构建` 说的是扫描和关系重算策略，不是产物目录格式
- 所以即使只重读了少量变更表，系统仍然会先写一个新的 `graph/builds/<build_id>/` 快照目录
- 下游 RAG 不需要关心这次是不是增量，只需要始终读取 `graph/current/`
- 若要排查某次具体构建，再回看对应的 `graph/builds/<build_id>/`

每个已发布版本目录中自动导出以下 16 个文件：

| # | 文件 | 用途 | 召回层 | 加载建议 |
|:--|:--|:--|:--|:--|
| 1 | `schema_summary.txt` | 全量表名按域分组，注入 system prompt（≈500 tokens） | 层1 | **必须**，常驻内存 |
| 2 | `llm_chunks.jsonl` | 每表/列组一条 JSON，向量化召回 | 层1 | **必须**，建向量索引 |
| 3 | `llm_chunks.md` | 同上 Markdown 版，供人工阅读调试 | — | 调试用 |
| 4 | `column_index.json` | 列名→表名倒排索引（精确/归一化/中文切词） | 层1 | **必须**，内存加载 |
| 5 | `relation_graph.json` | 邻接表+JOIN 条件，BFS 扩展候选表 | 层1 | **必须**，内存加载 |
| 6 | `join_paths.json` | 预计算 1~2 跳 JOIN 路径 | 层1/层4 | **必须** |
| 7 | `table_profiles.jsonl` | 每表富元数据（含 semantic_type/domain_role/metric_tag） | 层2/层4 | **必须** |
| 8 | `analysis.json` | PageRank 中心性/社区模块/孤立表/关键路径 | 层1 | 推荐 |
| 9 | `cell_locator.json` | 表→文件→行号→列号，精确溯源 | 辅助 | 推荐 |
| 10 | `value_index.json` | 跨表共享值反查（值→出现的表和列） | 层1 | 推荐 |
| 11 | `domain_graph.json` | 域级关系聚合统计（hero↔skill 共 N 条关系） | 层1 | 推荐 |
| 12 | `rag_preview.json` | 供静态前端 / RAG 调试使用的轻量预览资产 | 调试/UI | 可选 |
| 13 | `enum_cross_ref.json` | 跨表共享枚举空间列对 | 层2 | 可选 |
| 14 | `data_health.json` | 数据质量报告（空值率/数值范围/pack列/枢纽表） | 调试 | 可选 |
| 15 | `pack_array_candidates.json` | pack_array 弱信号候选关系（已从主图剥离） | 审核 | 可选 |
| 16 | `evidence_config.json` | EvidenceAssembler 初始化配置 | 层4 | 推荐 |

---

## 3. 快速接入（最小可用）

说明：这里的“接入”是指**读取产物文件并在你自己的 RAG 服务中使用**，不是调用本工程接口。

```python
import json
from pathlib import Path
from collections import defaultdict

ROOT = Path("path/to/graph")
DATA = ROOT / "current"        # 推荐：始终读取 current

# ① 全量表名摘要（注入 system prompt）
SCHEMA_SUMMARY = (DATA / "schema_summary.txt").read_text(encoding="utf-8")

# ② 列名倒排索引
with open(DATA / "column_index.json", encoding="utf-8") as f:
    COL_INDEX: dict = json.load(f)

# ③ llm_chunks — 向量化召回用文本 + 元数据
CHUNKS: dict[str, dict] = {}
with open(DATA / "llm_chunks.jsonl", encoding="utf-8") as f:
    for line in f:
        obj = json.loads(line)
        # v3 格式：每条记录含 id / table_name / chunk_type / chunk_group / text
        CHUNKS[obj["id"]] = obj

# ④ 主图（表结构 + 关系）
with open(DATA / "relation_graph.json", encoding="utf-8") as f:
    REL_GRAPH: dict = json.load(f)   # REL_GRAPH["tables"][name]["neighbors"]

# ⑤ 分析结果（centrality / modules / orphans）
with open(DATA / "analysis.json", encoding="utf-8") as f:
    ANALYSIS: dict = json.load(f)
CENTRALITY: dict[str, float] = ANALYSIS.get("centrality", {})
MODULES: list[list[str]] = ANALYSIS.get("modules", [])
TABLE_MODULE: dict[str, int] = {t: i for i, m in enumerate(MODULES) for t in m}
```

建议下游 RAG 默认采用两段式：

1. 首轮只给 LLM `summary evidence`
2. 若模型或编排器判断证据不够，再依据 `fetch_hints` 继续拉取 `drill-down evidence`

这样可以同时满足：

- 底层数据保持完整
- 首轮 prompt 不会被大表和宽表淹没
- 大表分析结果仍可按需完整展开

如果你还需要在静态可视化前端中查看与 RAG 证据一致的预览，可直接使用：

- `rag_preview.json`

它与 HTML 报告中的 RAG 证据面板共用同一套预览数据结构，适合：

- 调试“问题会命中哪些表”
- 调试“首轮证据会展示哪些列和统计”
- 校验前端视图与 RAG 编排层是否一致

---

## 4. 层1 — 表级召回层

### 4.1 LLM 意图提取（锁定种子表）

```python
import openai

def find_seed_tables(query: str) -> list[str]:
    """第一次 LLM 调用：从 schema_summary.txt 识别相关表名。"""
    resp = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": (
                f"{SCHEMA_SUMMARY}\n\n"
                "根据用户问题，从上方表名列表中找出最相关的 1-5 个表名，"
                "只返回 JSON 数组，如 [\"hero_base\", \"skill_base\"]。"
                "不存在的表名不要返回。"
            )},
            {"role": "user", "content": query},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )
    data = json.loads(resp.choices[0].message.content)
    # 兼容 {"tables": [...]} 或直接数组
    if isinstance(data, list):
        return data
    for v in data.values():
        if isinstance(v, list):
            return v
    return []
```

> **成本参考**：`schema_summary.txt` ≈ 800 tokens，gpt-4o-mini 单次 ~$0.0002，延迟 ~1s。

### 4.2 列名快速定位

当用户问题直接提到列名时（如"看 quality 列"），用倒排索引直接定位：

```python
def tables_by_column(col_name: str) -> list[str]:
    """精确列名 → 归属表名列表。"""
    exact = COL_INDEX.get(col_name, [])
    # 去掉 FK 后缀归一化查（hero_id → hero）
    norm = COL_INDEX.get("_normalized", {}).get(col_name.lower(), [])
    # 中文切词查（"英雄ID" → ["hero_base", ...]）
    cn = COL_INDEX.get("_cn_segments", {})
    cn_matches = []
    for kw, tables in cn.items():
        if kw in col_name:
            cn_matches.extend(tables)
    return list(dict.fromkeys(exact + norm + cn_matches))
```

### 4.3 BFS 图扩展（扩充候选集）

```python
def bfs_expand(seed_tables: list[str], max_hops: int = 2,
               min_confidence: float = 0.65) -> list[str]:
    """从种子表出发，BFS 扩展直接相关表，返回所有候选表（含种子）。"""
    visited = set(seed_tables)
    frontier = list(seed_tables)
    for _ in range(max_hops):
        next_frontier = []
        for tname in frontier:
            node = REL_GRAPH.get("tables", {}).get(tname, {})
            for nb in node.get("neighbors", []):
                if nb["confidence"] >= min_confidence:
                    t = nb["table"]
                    if t not in visited:
                        visited.add(t)
                        next_frontier.append(t)
        frontier = next_frontier
    return list(visited)
```

### 4.4 候选表排序与截断

```python
def rank_and_prune(candidates: list[str], seeds: list[str],
                   query: str, top_k: int = 8) -> list[str]:
    """对候选表打分排序，返回 top-K。"""
    query_lower = query.lower()
    seed_set = set(seeds)
    seed_modules = {TABLE_MODULE.get(s) for s in seeds} - {None}

    scored = []
    for name in candidates:
        score = 0.0
        node = REL_GRAPH.get("tables", {}).get(name, {})

        # 基础分：种子表最高
        if name in seed_set:
            score += 10.0
        # 与种子的关系置信度
        for nb in node.get("neighbors", []):
            if nb["table"] in seed_set:
                score += nb["confidence"] * 3.0
        # centrality 加权（枢纽表更可能被需要）
        score += CENTRALITY.get(name, 0) / 100.0 * 2.0
        # 同模块加分
        if TABLE_MODULE.get(name) in seed_modules:
            score += 1.0
        # 关键词命中
        if query_lower and any(
            p in query_lower for p in [name.lower()] +
            name.lower().split("_")
        ):
            score += 2.0
        scored.append((score, name))

    scored.sort(key=lambda x: -x[0])
    return [n for _, n in scored[:top_k]]
```

### 4.5 完整表级召回流程

```python
def recall_tables(query: str, top_k: int = 8) -> list[str]:
    seeds = find_seed_tables(query)                          # LLM 意图提取
    seeds += tables_by_column(query)                        # 列名精确定位补充
    candidates = bfs_expand(seeds, max_hops=2)              # BFS 图扩展
    return rank_and_prune(candidates, seeds, query, top_k)  # 排序截断
```

---

## 5. 层2 — 列级裁剪层

`table_profiles.jsonl` 中每列新增三个语义字段：

### 5.1 字段说明

| 字段 | 取值示例 | 含义 |
|:--|:--|:--|
| `semantic_type` | `identifier` `metric` `flag` `enum` `pack_array` `temporal` `descriptor` `coordinate` `text` | 列的语义类型 |
| `domain_role` | `id_key` `stat_atk` `stat_hp` `cost` `level_grade` `flag_switch` `type_category` `probability` `count_limit` 等 | 列的业务角色（17 种） |
| `metric_tag` | `hp` `attack` `defense` `speed` `cost` `level` `exp` `count` `rate` `resource` 等 | 仅数值列，可聚合的游戏指标语义 |

### 5.2 手动裁剪示例

```python
import json

# 加载 profiles
PROFILES: dict[str, dict] = {}
with open(DATA / "table_profiles.jsonl", encoding="utf-8") as f:
    for line in f:
        obj = json.loads(line)
        PROFILES[obj["table_name"]] = obj

def prune_columns(table_name: str, query: str,
                  max_cols: int = 25) -> list[dict]:
    """
    按 query 语义保留最相关的列，其余裁剪掉。
    EvidenceAssembler 内部会自动做这一步，此函数仅供单独使用。
    """
    profile = PROFILES.get(table_name, {})
    cols = profile.get("columns", [])
    query_lower = query.lower()

    scored = []
    for c in cols:
        score = 0
        if c.get("is_pk"):            score += 100
        if c.get("is_fk"):            score += 50
        sem = c.get("semantic_type", "")
        if sem in ("identifier", "flag", "enum"):  score += 30
        role = c.get("domain_role", "") or ""
        tag  = c.get("metric_tag",  "") or ""
        name = c.get("name", "").lower()
        # query 词义命中
        for kw in (name, role.replace("_", " "), tag):
            if kw and any(t in query_lower for t in kw.split()):
                score += 15
        if sem == "metric":           score += 10
        if sem == "descriptor":       score += 5
        scored.append((score, c))

    scored.sort(key=lambda x: -x[0])
    return [c for _, c in scored[:max_cols]]
```

### 5.3 按 semantic_type 过滤列

```python
# 只看数值指标列（用于统计分析类查询）
def get_metric_cols(table_name: str) -> list[dict]:
    profile = PROFILES.get(table_name, {})
    return [c for c in profile.get("columns", [])
            if c.get("semantic_type") == "metric"]

# 只看枚举列（用于过滤条件生成）
def get_enum_cols(table_name: str) -> dict[str, list]:
    profile = PROFILES.get(table_name, {})
    return {c["name"]: c.get("enum_values", [])
            for c in profile.get("columns", [])
            if c.get("is_enum") and c.get("enum_values")}
```

---

## 6. 层3 — 行级取数层

`RowRetriever` 从自然语言 query 提取谓词，回源读 Excel，只返回命中行块。

### 6.1 基本用法

```python
from indexer.retrieval.row_retriever import RowRetriever

retriever = RowRetriever(data_root="path/to/excel/data")

# 从 query + table profile 推导谓词
profile = PROFILES["hero_base"]
predicates = retriever.generate_predicates(
    query="攻击力大于500的英雄",
    table_schema=profile,
    max_predicates=6,
)
# 结果示例：
# [Predicate(column='atk', op='gt', value=500.0, source='comparison_expr')]

# 回源取行
block = retriever.fetch_rows(
    table_schema=profile,
    predicates=predicates,
    max_rows=20,
    return_cols=["id", "name", "atk", "hp", "quality"],   # 可选，配合列级裁剪
)
print(f"命中 {block.total_matched} 行，返回 {len(block.rows)} 行")
print(f"使用谓词: {block.predicates_used}")
print(f"跳过谓词（列不存在）: {block.predicates_skipped}")
# block.rows → [{"id": "1001", "name": "Arthur", "atk": "850", ...}, ...]
```

### 6.2 谓词生成策略与组合规则

`generate_predicates` 按以下优先级生成：

| 优先级 | 策略 | 示例 |
|:--|:--|:--|
| 1 | **ID 精确匹配** | query 含裸整数 → PK/FK 列 `eq` 谓词 |
| 2 | **枚举命中** | query 含枚举值字面量 → `eq` 谓词 |
| 3 | **数值范围** | `>=`/`大于`/`N到M` → `gte`/`lte`/`gt`/`lt` 谓词 |
| 4 | **关键词搜索** | 中文/英文词 → 文本列 `contains` 谓词 |

`fetch_rows` 的组合规则：

- 同列多个 `eq` / `contains` / `in`：使用 **OR**
- 同列多个范围条件（`gt/gte/lt/lte/ne`）：使用 **AND**
- 不同列之间：使用 **AND**

这意味着当前实现是“同列宽松、跨列收敛”的过滤策略，更适合分析场景；不是旧版那种“全局 OR 扩散式采样”。

### 6.3 谓词操作符一览

| op | 语义 | 示例 |
|:--|:--|:--|
| `eq` | 等于 | `quality eq 5` |
| `ne` | 不等于 | `is_enable ne 0` |
| `gt` `gte` | 大于/大于等于 | `atk gt 500` |
| `lt` `lte` | 小于/小于等于 | `cd lte 10` |
| `contains` | 字符串包含 | `name contains '骑士'` |
| `in` | 集合包含 | `camp in [1,2,3]` |

### 6.4 手动构建谓词

```python
from indexer.retrieval.row_retriever import Predicate

manual_preds = [
    Predicate("quality", "eq",  5,   "manual"),
    Predicate("atk",     "gte", 800, "manual"),
    Predicate("name",    "contains", "战士", "manual"),
]
block = retriever.fetch_rows(PROFILES["hero_base"], manual_preds, max_rows=50)
```

---

## 7. 层4 — 证据组装层

`EvidenceAssembler` 将前三层结果打包成四段式 LLM 上下文。

### 7.1 初始化

推荐从 `evidence_config.json` 读取配置：

```python
import json
from indexer.export.evidence_assembler import EvidenceAssembler

with open(DATA / "evidence_config.json", encoding="utf-8") as f:
    cfg = json.load(f)

assembler = EvidenceAssembler(**cfg["assembler_init"])
# 等价于：
# assembler = EvidenceAssembler(
#     profiles_path="path/to/graph/table_profiles.jsonl",
#     join_paths_path="path/to/graph/join_paths.json",
#     data_root="path/to/excel/data",
# )
```

### 7.1.1 `evidence_config.json` 字段说明

`evidence_config.json` 的目标是让下游 RAG 零猜测完成初始化。

典型结构如下：

```json
{
  "_meta": {
    "description": "...",
    "usage": "..."
  },
  "assembler_init": {
    "profiles_path": "D:/.../graph/current/table_profiles.jsonl",
    "join_paths_path": "D:/.../graph/current/join_paths.json",
    "data_root": "D:/.../excel"
  },
  "layer_description": {
    "表级召回层": "...",
    "列级裁剪层": "...",
    "行级取数层": "...",
    "证据组装层": "..."
  },
  "recommended_flow": [
    "..."
  ]
}
```

各字段含义：

| 字段 | 是否必需 | 用途 |
|:--|:--|:--|
| `_meta.description` | 否 | 给接入方的人类说明 |
| `_meta.usage` | 否 | 最小初始化示例 |
| `assembler_init.profiles_path` | **是** | 指向 `table_profiles.jsonl` |
| `assembler_init.join_paths_path` | **是** | 指向 `join_paths.json` |
| `assembler_init.data_root` | **是** | 指向原始 `excel` 数据根目录，供回源取数与全量统计 |
| `layer_description` | 否 | 解释四层召回 / 证据结构 |
| `recommended_flow` | 否 | 给编排器的推荐接入顺序 |

### 7.1.2 下游应如何使用 `assembler_init`

推荐直接透传：

```python
with open(DATA / "evidence_config.json", encoding="utf-8") as f:
    cfg = json.load(f)

assembler = EvidenceAssembler(**cfg["assembler_init"])
```

不建议下游自己手写这些路径，原因是：

- `graph/current/` 会随着发布切换
- `data_root` 可能和 `graph` 目录不在同一层
- 构建机和部署机路径可能不同，最好始终以产物中的配置为准

### 7.1.3 常见误区

- 不要把 `evidence_config.json` 当成完整索引数据，它只是入口配置
- 不要忽略 `data_root`，否则 `RowRetriever` 和全量分析模式无法回源
- 不要直接读取 `graph/builds/<build_id>/evidence_config.json` 做在线接入，应优先读 `graph/current/evidence_config.json`

### 7.2 组装证据

```python
evidence = assembler.assemble(
    query="攻击力大于500且品质为5的英雄列表",
    table_names=["hero_base", "hero_quality"],  # 层1 召回结果
    max_rows_per_table=20,    # 每表最多返回行数
    max_cols_per_table=25,    # 每表最多保留列数（列级裁剪）
    fetch_rows=True,          # 是否执行行级取数（False 时跳过层3）
    analysis_mode=None,       # 自动判断是否启用全量数值分析模式
)
```

### 7.3 证据结构详解（v5）

```python
# 段①: schema — 列级裁剪后的表结构
for tbl in evidence["schema"]:
    print(f"{tbl['table']} [{tbl['domain']}] {tbl['row_count']}行")
    print(f"  已选 {tbl['selected_columns']}/{tbl['total_columns']} 列")
    for c in tbl["columns"]:
        # 每列含: name, dtype, semantic_type, domain_role, metric_tag,
        #         is_pk, is_fk, fk_target, is_enum, enum_values, stats
        print(f"  - {c['name']}({c['dtype']}) "
              f"sem={c.get('semantic_type')} "
              f"role={c.get('domain_role')} "
              f"tag={c.get('metric_tag')}")

# 段②: join — 表间 JOIN 路径
for j in evidence["join"]:
    print(f"{j['from']} → {j['to']} ({j['hops']}跳, conf={j['min_confidence']})")
    for jc in j["joins"]:
        print(f"  {jc}")

# 段③: key_rows — 谓词过滤行块
for block in evidence["key_rows"]:
    print(f"{block['table']}: 命中{block['total_matched']}行, "
          f"返回{block['rows_returned']}行")
    print(f"  谓词: {block['predicates_used']}")
    for row in block["rows"][:3]:
        print(f"  {row}")

# 段④: stat_summary — 统计摘要
for s in evidence["stat_summary"]:
    if s["semantic_type"] == "metric":
        print(f"{s['table']}.{s['column']} [{s.get('metric_tag')}] "
              f"min={s['min']} max={s['max']} mean={s['mean']}")
    else:
        print(f"{s['table']}.{s['column']} 枚举: {s.get('enum_values')}")

# 段⑤: hidden_but_available — 首屏未展开、但仍可继续获取的内容
print(evidence["hidden_but_available"])
# 示例：
# {
#   "schema": [{"table": "libao", "hidden_columns": 37, ...}],
#   "join": {"total_paths": 3, "all_paths_available": True},
#   "rows": [{"table": "libao", "hidden_rows": 182, ...}],
#   "analytics": [{"table": "libao", "hidden_group_columns": [...], ...}]
# }

# 段⑥: fetch_hints — 建议下游继续追取的入口提示
for hint in evidence["fetch_hints"]:
    print(hint["type"], hint["reason"], hint["suggested_args"])
```

关键约定：

- `schema` / `join` / `key_rows` / `stat_summary` 仍然是首轮主要证据
- `analytical_result` 仍然保留全量分析结果，适合程序继续消费
- `analytical_result_visible` 是给首轮 LLM 使用的压缩版分析结果
- `hidden_but_available` 明确告诉下游“还有什么没展示，但系统里有”
- `fetch_hints` 明确告诉下游“下一步该取什么”

### 7.4 推荐接入方式：Summary + Drill-down

建议不要把 `analytical_result` 整体直接塞给 LLM，而是按下面方式接：

```python
evidence = assembler.assemble(
    query=query,
    table_names=table_names,
    analysis_mode=None,
)

# 首轮：只给摘要视图
prompt_text = assembler.to_prompt_text(evidence)

# 编排器判断是否需要继续展开
if evidence["fetch_hints"]:
    next_action = evidence["fetch_hints"][0]
    # 例如：
    # - expand_schema
    # - expand_rows
    # - expand_analysis_groups
    # - expand_global_stats
    # - expand_join_paths
```

推荐策略：

- 配置查询：优先用 `schema + join + key_rows`
- 分布分析：优先用 `analytical_result_visible + stat_summary + trend_hints`
- 需要完整性时：程序侧读取 `analytical_result` 或按 `fetch_hints` 继续回源

最小编排示例：

```python
def answer_with_drilldown(query: str, table_names: list[str]):
    evidence = assembler.assemble(
        query=query,
        table_names=table_names,
        analysis_mode=None,
    )

    first_prompt = assembler.to_prompt_text(evidence)
    answer_1 = llm_answer(first_prompt)

    # 如果首轮证据已经足够，直接返回
    if not evidence.get("fetch_hints"):
        return answer_1

    # 如果你的编排器发现模型还在要求“更多列 / 更多行 / 更完整分组”，
    # 可按 hint 类型继续回源补证据
    next_hint = evidence["fetch_hints"][0]
    hint_type = next_hint["type"]

    if hint_type == "expand_analysis_groups":
        # 程序侧可直接读取 evidence["analytical_result"]，
        # 或按 suggested_args 拉取更完整的分析结果
        full_analytics = evidence.get("analytical_result", [])
        second_prompt = first_prompt + "\n\n补充完整分析:\n" + json.dumps(
            full_analytics, ensure_ascii=False
        )
        return llm_answer(second_prompt)

    if hint_type == "expand_rows":
        # 这里示例为重新调高 max_rows_per_table
        evidence_2 = assembler.assemble(
            query=query,
            table_names=table_names,
            max_rows_per_table=100,
            analysis_mode=False,
        )
        return llm_answer(assembler.to_prompt_text(evidence_2))

    return answer_1
```

### 7.5 格式化为 Prompt

```python
prompt_text = assembler.to_prompt_text(
    evidence,
    max_rows_display=10,   # Markdown 表格最多展示行数
)

# prompt_text 结构：
# ## 用户问题
# ...
# ## 相关表结构（Schema）
# ### hero_base [hero] 1500行  主键: id
# > 英雄相关配置，含 id, name, quality, atk...
# （已选 12/32 列）
# - **id** `int` | PK, identifier, id_key
# - **atk** `int` | metric, [attack], stat_atk, 范围[100~2000]
# ...
# ## 表间 JOIN 路径
# - hero_base → skill_base (1跳, conf=0.92)
#   `hero_base.skill_id = skill_base.id`
# ## 关键数据行
# ### hero_base（命中 47 行，展示 10 行）
# 过滤条件: atk gt 500.0, quality eq 5
# | id | name | atk | hp | quality |
# |---|---|---|---|---|
# | 1001 | 亚瑟 | 850 | 5200 | 5 |
# ...
# ## 统计摘要
# - hero_base.atk [attack] min=100 max=2000 mean=650.3 unique=450

messages = [
    {"role": "system", "content": SCHEMA_SUMMARY + "\n\n" + ANSWER_RULES},
    {"role": "user",   "content": prompt_text},
]
```

### 7.6 数值分析模式（analysis_mode）— 游戏策划专用

当 query 为**数值分析**（各档位平均、分布、离群值、平衡性、商业化风险、异常值）时，`analysis_mode=None` 会自动启用全量统计；也可以显式传 `True`：
在 Python 侧做全量聚合，结果以紧凑表格给 LLM，**不丢数据、分析准确**。

```python
# 识别分析型 query（可按关键词或单独 LLM 调用判断）
ANALYSIS_KEYWORDS = frozenset([
    '平均', '分布', '各档次', '各等级', '各品质', '曲线', '离群', '异常',
    '平衡', '数值分析', '统计', '多少', '占比', '区间'
])
def is_analysis_query(q: str) -> bool:
    return any(kw in q for kw in ANALYSIS_KEYWORDS)

evidence = assembler.assemble(
    query=query,
    table_names=table_names,
    analysis_mode=None,  # 默认自动启用；如需强制可显式传 True
)

# analysis_mode 开启时：
# - key_rows 为空，改为 analytical_result
# - analytical_result 保留全量统计结果
# - analytical_result_visible 提供首轮可控摘要
# - 每表：按枚举列分组 → count + 各数值列 mean/min/max/p50/p90
# - 离群值：IQR 法检测，列出偏高/偏低的具体行（id + 值）
# - to_prompt_text() 默认优先使用 analytical_result_visible
```

对下游 RAG 的建议：

- 若只是首轮回答，优先使用 `analytical_result_visible`
- 若模型明确要求“完整分组”“全部指标”“全部异常值”，再读取 `analytical_result`
- 不要把“底层完整性”寄托在单次 prompt 上，应由编排器多轮追取保证

**输出示例**（紧凑，≈500–2000 tokens/表）：
```
## 表 hero_base 数值分析（全量 1500 行）
### 按 quality 分组
| quality | count | atk(mean/min/max) | hp(mean/min/max) |
| 1 | 52 | 210.3/100/320 | 2100/800/3500 |
| 2 | 118 | 380.2/250/510 | 4200/3200/5800 |
| 3 | 245 | 550.1/400/950 | ...  ← 注意 max=950 可能离群
...
### 离群值（IQR 法）
- **atk 偏高**: [{"id": 1234, "atk": 950}, ...]
```

### 7.6 完整端到端示例

```python
def answer_query(query: str) -> str:
    table_names = recall_tables(query, top_k=6)
    use_analysis = is_analysis_query(query)

    evidence = assembler.assemble(
        query=query,
        table_names=table_names,
        max_rows_per_table=20,
        fetch_rows=not use_analysis,   # 分析模式不取行样本
        analysis_mode=use_analysis,
    )
    prompt = assembler.to_prompt_text(evidence)

    resp = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SCHEMA_SUMMARY},
            {"role": "user",   "content": prompt},
        ],
        temperature=0,
    )
    return resp.choices[0].message.content
```

---

## 8. pack_array 候选关系

### 8.1 背景

pack_array 关系（如 `hero_base.skill_ids → skill_base.id`，值格式为 `"10001|10002|10003"`）已**从主关系图完全剥离**，不参与 BFS 扩展和 JOIN 路径。原因：纯值重叠检测假阳性率高，容易扩散干扰。

通过**业务关键词白名单**初筛（列名词段命中 `skill/buff/item/hero/monster/...` 等 47 个实体词）的候选关系会保存在 `pack_array_candidates.json`，供人工审核。

### 8.2 候选文件格式

```json
{
  "_meta": {
    "total": 38,
    "source": "BuildResult.pack_array_candidates",
    "description": "pack_array 弱信号候选关系，不在主关系图中..."
  },
  "candidates": [
    {
      "from_table": "hero_base",
      "from_column": "skill_ids",
      "to_table": "skill_base",
      "to_column": "id",
      "confidence": 0.75,
      "evidence": "sep='|', overlap=45/47 (96%)",
      "join": "hero_base.skill_ids = skill_base.id",
      "pack_info": {
        "separator": "|",
        "element_dtype": "int",
        "element_samples": [10001, 10002, 10015],
        "avg_pack_size": 3.2
      },
      "promote_hint": "列名含 ['skill'] 等业务关键词，建议人工确认后通过 feedback 提升"
    }
  ]
}
```

### 8.3 加载并作为扩展候选使用

```python
with open(DATA / "pack_array_candidates.json", encoding="utf-8") as f:
    pack_data = json.load(f)

# 按 from_table 建索引
PACK_CANDIDATES: dict[str, list[dict]] = {}
for c in pack_data.get("candidates", []):
    PACK_CANDIDATES.setdefault(c["from_table"], []).append(c)

def expand_with_pack(table_names: list[str],
                     min_confidence: float = 0.70) -> list[str]:
    """在主图 BFS 扩展之后，补充 pack_array 候选关系覆盖的表。"""
    extra = set()
    for tname in table_names:
        for cand in PACK_CANDIDATES.get(tname, []):
            if cand["confidence"] >= min_confidence:
                extra.add(cand["to_table"])
    return list(extra - set(table_names))

# 在 recall_tables() 之后可选追加：
# pack_extras = expand_with_pack(table_names)
# table_names = table_names + pack_extras[:3]
```

### 8.4 提升候选为正式关系（人工审核后）

编辑 `relation_feedback.json`（与 `graph/` 同目录），添加确认条目：

```json
{
  "confirmed": [
    {
      "from_table": "hero_base",
      "from_column": "skill_ids",
      "to_table": "skill_base",
      "to_column": "id"
    }
  ],
  "rejected": []
}
```

下次 `build_full_graph` 时，`FeedbackManager` 会自动提升该关系的置信度并纳入主图。

---

## 9. 调优与进阶

### 9.1 构建后回归与回退

系统现在内置了最小可用的构建后校验流程：

- 检查关键产物是否缺失
- 对比上一成功版本的 `relation_count / join_path_count / orphan_count`
- 执行 `graph/regression_queries.json` 中定义的默认回归样例
- 生成 `regression_report.json` 和 `regression_report.md`
- 若出现 `P0`，则**不切换** `graph/current/`

接入方建议：

- 在线服务只读 `graph/current/`
- 若线上结果异常，可快速对比 `graph/latest_success/`
- 运维侧可读取 `graph/reports/<build_id>.json` 做自动化监控

默认回归样例覆盖：

- 英雄平衡 / 技能链路
- 礼包和商店商业化风险
- 奖励 / 掉落链路
- 登录奖励 / 邮件增益风险 / 引用链

如需增加业务样例，直接编辑 `graph/regression_queries.json`

### 9.2 向量化索引策略

**方案 A：用 `table_profiles.jsonl` 的 `searchable_text`（推荐）**

```python
# searchable_text 专为语义匹配设计，无格式噪声（无 ## / → / @conf 等标记）
# 包含：表名、域名、中文同义词、列名、文本枚举值、关联表名
ids, texts = [], []
with open(DATA / "table_profiles.jsonl", encoding="utf-8") as f:
    for line in f:
        obj = json.loads(line)
        ids.append(obj["table_name"])
        texts.append(obj["searchable_text"])
collection.upsert(ids=ids, documents=texts)
```

**方案 B：用 `llm_chunks.jsonl`（多粒度，宽表有多条 chunk）**

```python
# v3 新字段：table_name / chunk_type / chunk_group
# 宽表拆分为多个 chunk（chunk_type="table_group"，chunk_group=1/2/...）
# 通过 table_name 字段可聚合同一张表的所有 chunk，无需解析 id 中的 __g 后缀

ids, texts, metadatas = [], [], []
with open(DATA / "llm_chunks.jsonl", encoding="utf-8") as f:
    for line in f:
        obj = json.loads(line)
        ids.append(obj["id"])
        texts.append(obj["text"])
        metadatas.append({
            "table_name":  obj["table_name"],
            "chunk_type":  obj["chunk_type"],   # "table" | "table_group"
            "chunk_group": obj["chunk_group"],  # null 或 int（列组序号）
        })
collection.upsert(ids=ids, documents=texts, metadatas=metadatas)

# 向量召回后按 table_name 聚合（防止宽表多个 chunk 算多次）
def vector_recall(query: str, top_k: int = 10) -> list[str]:
    results = collection.query(query_texts=[query], n_results=top_k * 2)
    seen, tables = set(), []
    for meta in results["metadatas"][0]:
        t = meta["table_name"]
        if t not in seen:
            seen.add(t)
            tables.append(t)
            if len(tables) >= top_k:
                break
    return tables
```

### 9.3 centrality 加权召回

`analysis.json` 的 `centrality` 是 PageRank 分数（0-100），越高代表被越多其他表引用。在排序阶段加权：

```python
# 枢纽表最多额外 +2 分
score += CENTRALITY.get(name, 0) / 100.0 * 2.0
```

### 9.4 同模块（社区）优先召回

Label Propagation 社区聚类：同一模块内的表业务耦合度高，应优先召回：

```python
# 预构建 table → module_id 映射
TABLE_MODULE: dict[str, int] = {
    t: i
    for i, mod in enumerate(MODULES)
    for t in mod
}

# 在排序时：种子表所在模块的候选表加分
seed_modules = {TABLE_MODULE.get(s) for s in seeds} - {None}
if TABLE_MODULE.get(name) in seed_modules:
    score += 1.0
```

### 9.5 join_paths 直接查 JOIN 条件

```python
with open(DATA / "join_paths.json", encoding="utf-8") as f:
    JOIN_PATHS: dict = json.load(f)

def get_join_path(table_a: str, table_b: str) -> dict | None:
    key = f"{table_a} -> {table_b}"
    rev = f"{table_b} -> {table_a}"
    return JOIN_PATHS["paths"].get(key) or JOIN_PATHS["paths"].get(rev)

jp = get_join_path("hero_base", "skill_base")
# {"hops": 1, "path": ["hero_base", "skill_base"],
#  "joins": ["hero_base.skill_id = skill_base.id"],
#  "min_confidence": 0.92}
```

### 9.6 value_index 反查值所在表

```python
with open(DATA / "value_index.json", encoding="utf-8") as f:
    VALUE_INDEX: dict = json.load(f)["values"]

def find_value(v: str) -> list[dict]:
    """查某个值（如 ID=1001）出现在哪些表的哪些列。"""
    return VALUE_INDEX.get(str(v), [])

# find_value("1001") → [{"table": "hero_base", "column": "id"}, ...]
```

### 9.7 domain_graph 快速判断跨域关系

```python
with open(DATA / "domain_graph.json", encoding="utf-8") as f:
    DOMAIN_GRAPH: dict = json.load(f)

# 查某个域下的所有表
hero_tables = DOMAIN_GRAPH["domains"].get("hero", {}).get("tables", [])

# 查两个域之间的关联强度
for dr in DOMAIN_GRAPH["domain_relations"]:
    if {dr["from"], dr["to"]} == {"hero", "skill"}:
        print(f"hero↔skill: {dr['relation_count']}条关系, "
              f"avg_conf={dr['avg_confidence']}")
```

### 9.8 Prefix Caching（降低延迟 30-50%）

```python
# system prompt 固定前缀（被 LLM API 缓存，首次之后不再计时）
SYSTEM_PREFIX = f"{SCHEMA_SUMMARY}\n\n{ANSWER_RULES}\n\n"

def build_prompt(evidence_text: str) -> list[dict]:
    return [
        {"role": "system", "content": SYSTEM_PREFIX + evidence_text},
        # user message 为空或包含原始 query（已在 evidence_text 里）
    ]
```

GPT-4o / Claude 支持 prefix caching：固定前缀首次之后费用和延迟大幅降低。

### 9.9 fetch_rows=False（纯 schema 模式）

当 query 是结构性问题（"hero_base 有哪些列"）而非数据查询时，跳过行级取数节省 I/O：

```python
evidence = assembler.assemble(
    query="hero_base 表有哪些攻击类属性列",
    table_names=["hero_base"],
    fetch_rows=False,    # 只返回 schema + join + stat_summary，不读 Excel
)
```

---

## 10. 常见问题

### Q1：召回了很多表，LLM 上下文装不下怎么办？

优先级截断顺序：
1. `rank_and_prune` 的 `top_k` 从 8 降到 5
2. `max_cols_per_table` 从 25 降到 15（列级裁剪更激进）
3. `max_rows_per_table` 从 20 降到 10
4. `fetch_rows=False`（跳过行级取数，只给 schema + stat_summary）

### Q2：表级召回时 LLM 返回了不存在的表名怎么办？

```python
seeds = [t for t in find_seed_tables(query)
         if t in REL_GRAPH.get("tables", {})]
```

### Q3：llm_chunks.jsonl 里的 `id` 字段有 `__g2` 后缀，消费侧怎么聚合？

v3 版本每条记录都有 `table_name` 字段，不需要解析 `id`：

```python
# 按 table_name 聚合同一张表的所有 chunk 文本
from collections import defaultdict
table_texts: dict[str, list[str]] = defaultdict(list)
with open(DATA / "llm_chunks.jsonl", encoding="utf-8") as f:
    for line in f:
        obj = json.loads(line)
        table_texts[obj["table_name"]].append(obj["text"])

# 合并同表 chunk（宽表分组 chunk 拼起来）
full_text = "\n".join(table_texts["hero_base"])
```

### Q4：pack_array 关系还能用吗？

不直接进入主图的 BFS 扩展，但可以：
1. 读 `pack_array_candidates.json`，作为**可选的扩展候选**（见 §8.3）
2. 置信度 ≥ 0.70 的候选经人工确认后写入 `relation_feedback.json` → 下次构建自动纳入主图

### Q5：`table_profiles.jsonl` 里列没有 `semantic_type` 字段怎么办？

旧版图谱（构建于本次升级前）的列不含该字段。重新执行一次全量构建即可补全：

```bash
python -m indexer --run-now
```

### Q6：如何调高 pack_array 候选的召回精度？

编辑 `indexer/discovery/pack_array.py` 中的 `_BUSINESS_COL_KEYWORDS` 集合，加入项目特有的实体词前缀（如 `army`、`troop`、`tech` 等）。

### Q7：BFS 扩展产生了很多低相关表，怎么过滤？

提高 `bfs_expand` 的 `min_confidence`（建议 0.70-0.75），或在 `rank_and_prune` 的 `top_k` 里设较小值（5-6）。噪声表通常 centrality 较低、与种子表置信度较低，排序后自然落到后面被截断。

### Q8：数值分析不准确怎么办？

优先用 `analysis_mode=None` 的默认自动判定；如需强制则传 `True`。该模式下在 Python 侧做全量 groupby/离群值检测，不依赖行采样，结果精确。适用于"各品质平均攻击力"、"有没有超模装备"、"各档位分布"等分析型 query。

### Q8.1：应该读取哪个目录？

始终优先读取 `graph/current/`。

- `graph/builds/<build_id>/` 是单次构建的版本目录，可能尚未通过校验
- `graph/latest_success/` 适合做人工回退和历史对账
- 线上 RAG 不建议直接读 `builds/`

### Q8.2：如果构建失败或告警怎么办？

看这三个位置：

- `graph/reports/<build_id>.md`：人读报表
- `graph/reports/<build_id>.json`：机器读报表
- `graph/alerts.log`：本地告警摘要

如果报表状态是：

- `P0`：当前版本不会切换，继续沿用上一版 `current`
- `P1`：版本已生成但有明显退化，建议人工复核
- `P2`：提示性异常，不一定影响在线使用

### Q9：行级取数层（RowRetriever）找不到 Excel 文件怎么办？

检查 `EvidenceAssembler` 初始化时的 `data_root` 是否指向正确的 Excel 根目录。`table_profiles.jsonl` 里每表的 `file` 字段是相对于 `data_root` 的文件名，RowRetriever 会在该目录下递归搜索：

```python
assembler = EvidenceAssembler(
    profiles_path=str(DATA / "table_profiles.jsonl"),
    join_paths_path=str(DATA / "join_paths.json"),
    data_root="D:/work/A_elex/策划表/excel_data/excel",  # Excel 文件实际位置
)
```

---

*文档对应版本：游戏配置表证据系统 v4，四层召回架构 + 构建后回归/回退机制。*
*如需重建图谱：`python -m indexer --run-now`*
