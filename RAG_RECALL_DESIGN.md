# 游戏配置图谱 — RAG 接入指南

> 面向 RAG 开发人员。本文档说明如何使用 `excel-graph-builder` 产出的图谱数据，
> 在 LLM 问答中完成游戏数值分析、配置结构查询、影响面评估等任务。

---

## 零、运行环境

```bash
# 1. 安装依赖
pip install -r requirements.txt   # 只有 openpyxl, xlrd

# 2. 构建图谱（约30秒，自动产出所有 RAG 所需文件）
python -m indexer --data-root "I:\slgconfiguration\excel" --run-now
```

构建完成后 `data/indexer/` 自动产出：

```
data/indexer/
├── schema_graph.json     ← 主图谱：206 张表 + 3461 条关系
├── column_index.json     ← 列名→表名倒排索引
├── meta.json             ← 构建元信息
├── schema_summary.txt    ← 轻量表名摘要（~500 tokens，用于意图提取 prompt）
├── llm_chunks.md         ← 每表一段 Markdown（人工检查用）
└── llm_chunks.jsonl      ← 每表一行 JSON（向量化 / 程序加载用）
```

> **无需手动执行 `--export-llm`**，build 成功后三个 LLM 资产文件自动生成。

**在你的 RAG 服务中加载（不依赖 indexer 模块）：**

```python
import json
from pathlib import Path

DATA_DIR = Path("data/indexer")  # 相对于项目根目录

# 主图谱
with open(DATA_DIR / "schema_graph.json", encoding="utf-8") as f:
    GRAPH = json.load(f)

# 列名倒排索引
with open(DATA_DIR / "column_index.json", encoding="utf-8") as f:
    COL_IDX = json.load(f)["column_to_tables"]

# 意图提取用的表名摘要（直接读文本，注入 prompt）
SCHEMA_SUMMARY = (DATA_DIR / "schema_summary.txt").read_text(encoding="utf-8")

# GRAPH["tables"]  → dict, 206 张表
# GRAPH["relations"] → list, 3461 条关系
# COL_IDX → dict, 列名→表名列表
# SCHEMA_SUMMARY → str, ~500 tokens 的业务域分组表名
```

> 整个 RAG 接入**只需要 `data/indexer/` 下的文件**，不需要 import indexer 包。

---

## 一、你拿到什么

系统从 113 个 Excel 文件中自动提取，构建时自动产出以下文件：

```
data/indexer/
├── schema_graph.json     ← 主图谱：206 张表 + 3461 条关系
├── column_index.json     ← 列名→表名倒排索引
├── meta.json             ← 构建元信息
├── schema_summary.txt    ← 业务域分组表名摘要（RAG 步骤①用）
├── llm_chunks.md         ← 每表 chunk（Markdown）
└── llm_chunks.jsonl      ← 每表 chunk（JSONL，向量化用）
```

### 1.1 schema_graph.json 结构

```jsonc
{
  "version": "1.0",
  "tables": {
    "hero": {
      "name": "hero",
      "file_path": "hero.xlsx",
      "sheet_name": "hero",
      "row_count": 19,
      "primary_key": "键值",
      "domain_label": "hero",        // 业务域：hero/skill/battle/item/building/quest/alliance/...
      "columns": [
        {
          "name": "英雄主动技能ID",
          "dtype": "int64",
          "sample_values": [101, 102, 103],   // 最多200行采样
          "unique_count": 15,
          "null_count": 0,
          "total_count": 19,
          "is_fk_candidate": true
        }
        // ...
      ],
      "enum_columns": {"英雄品质": [2, 3, 4, 5]},
      "numeric_columns": ["英雄基础战斗力", "baseHP", "baseAttack"]
    }
    // ... 共206张表
  },
  "relations": [
    {
      "from_table": "hero",
      "from_column": "英雄主动技能ID",
      "to_table": "skill",
      "to_column": "键值",
      "relation_type": "fk_content_subset",   // 关系类型
      "confidence": 0.77,                     // 0-1 置信度
      "discovery_method": "containment",      // 发现算法
      "evidence": "shared(15): 101,102,103,..." // 可读证据
    }
    // ... 共3461条
  ]
}
```

### 1.2 column_index.json 结构

```jsonc
{
  "column_to_tables": {
    "键值": ["hero", "skill", "buff", "weapon", ...],  // 33张表都有"键值"列
    "英雄ID": ["monsterTroop_monsterHero", "instanceTroop_instancePlayerHero"]
  }
}
```

**用途**：快速回答"哪些表有 XX 列"或"XX 在哪些表里被引用"。

### 1.3 关系类型说明

| relation_type          | 占比 | 含义                    | 置信度范围 |
| :--------------------- | :--- | :---------------------- | :--------- |
| `fk_content_subset`    | 98%  | A 列值集合 ⊆ B 列值集合 | 0.5–1.0    |
| `fk_naming_convention` | 1%   | 列名/表名命名规则匹配   | ~0.7       |
| `fk_content_overlap`   | 0.9% | A、B 列值域高度重叠     | 0.5–0.9    |
| `inferred_transitive`  | 0.1% | A→B + B→C 推断 A→C      | 较低       |

### 1.4 自动导出的 LLM 资产

构建时（`--run-now`）自动生成以下文件，无需手动执行：

| 文件                 | 用途                       | 格式                                  |
| :------------------- | :------------------------- | :------------------------------------ |
| `schema_summary.txt` | 步骤① 意图提取 prompt 注入 | 按域分组的表名列表，~500 tokens       |
| `llm_chunks.jsonl`   | 向量化 / 程序加载          | 每行一个 `{"id":"hero","text":"..."}` |
| `llm_chunks.md`      | 人工检查 / 直接阅读        | Markdown，每表一段                    |

> 也可手动导出到自定义路径：`python -m indexer --data-root <dir> --export-llm custom_path.jsonl`

每张表 chunk 格式（约 200-400 tokens）：
```
## 表: hero [hero]
- 文件: hero.xlsx | sheet: hero
- 行数: 19 | 列数: 35 | 主键: 键值
- 列: 键值(int), 英雄名字(str), 英雄品质(int), 英雄主动技能ID(int)→skill.键值, ...
- 关联: → skill(英雄主动技能ID→键值 @0.77), ← monsterTroop_monsterHero(英雄ID→键值 @0.77)
```

> **默认过滤 confidence < 0.6 的关系，每方向最多 10 条。**

---

## 二、Token 预算参考

在对接 LLM 前必须明确 token 开销，避免上下文溢出：

| 注入内容                            | tokens 估算 | 说明                             |
| :---------------------------------- | :---------- | :------------------------------- |
| 单张表 chunk（导出格式）            | 200–400     | 列多的宽表偏高                   |
| 全量 206 表 chunk                   | ~50K        | **不建议全塞**，超出多数模型窗口 |
| 单张表完整 JSON（含 sample_values） | 500–3000    | 列+采样数据大                    |
| 关系子图（1 表 + 1 跳邻居）         | 1K–5K       | 取决于邻居数                     |
| 关系子图（1 表 + 2 跳邻居）         | 3K–15K      | 膨胀快，必须剪枝                 |
| 系统提示词 + 规则                   | ~300        | 固定开销                         |

**建议上限**：单次注入 **8K–12K tokens** 的图谱上下文，留足空间给用户提问和模型输出。

---

## 三、推荐接入流程

### 总览

```
用户提问 ──→ ① 实体/意图提取 ──→ ② 定位种子表 ──→ ③ 图遍历展开 ──→ ④ 剪枝排序 ──→ ⑤ 组装 Prompt ──→ LLM
              (1次LLM调用)       (纯查表,0开销)    (纯遍历,0开销)   (纯计算,0开销)     (1次LLM调用)
```

**整个流程只需要 2 次 LLM 调用。** 中间步骤全部是确定性的字典查找和图遍历。

### 步骤 ① 实体/意图提取

用一次轻量 LLM 调用，从自然语言中提取结构化查询。

**关键：必须注入表名 + 业务域列表**，否则 LLM 无法知道有哪些可用实体。

构建工具已自动生成 `schema_summary.txt`，直接读取即可：

```python
# schema_summary.txt 在 build 时自动生成，无需手动维护
SCHEMA_SUMMARY = (DATA_DIR / "schema_summary.txt").read_text(encoding="utf-8")
```

意图提取 Prompt：

```
System: 你是一个游戏配置表查询解析器。

{SCHEMA_SUMMARY}

从用户问题中提取：
- entities: 涉及的游戏概念（中文），如 英雄、技能、道具
- table_hints: 如果能从上面的表名列表中直接定位到表，给出表名
- intent: schema(了解表结构) / value(查具体数值) / impact(影响分析) / validate(校验)
- columns: 如果提到了具体字段名就提取
输出 JSON。

User: "英雄升到5星要消耗多少道具"

→ {"entities":["英雄","道具"], "table_hints":["hero_hero_star","item"],
   "intent":"value", "columns":["星级","升阶消耗"]}
```

**token 开销：~700 输入（含 schema 摘要 500）+ ~80 输出 ≈ 780 tokens。**

> 注入 `SCHEMA_SUMMARY` 后，LLM 能直接看到 `hero_hero_star` 这个表名，
> 不需要靠猜；对冷门系统（如 `alliance_science`）也能准确定位。

### 步骤 ② 定位种子表

用提取到的实体，在图谱中**零 LLM 开销**地定位核心表：

```python
# ── ENTITY_MAP 自动生成（启动时执行一次）──
def build_entity_map() -> dict:
    """从 domain_label 反查 + 手工补充，自动覆盖所有表"""
    # 基础映射：domain_label → 中文实体（覆盖全部 13 个 domain）
    DOMAIN_CN = {
        "hero": "英雄", "skill": "技能", "battle": "战斗", "item": "道具",
        "building": "建筑", "quest": "任务", "alliance": "联盟",
        "monster": "怪物", "reward": "奖励", "world": "世界",
        "social": "社交", "config": "配置", "other": "其他",
    }
    # 反转：中文 → 英文前缀
    cn_to_prefix = {v: k for k, v in DOMAIN_CN.items()}
    # 手工补充高频别名
    cn_to_prefix.update({
        "兵种": "army", "装备": "equip", "活动": "activity",
        "副本": "instance", "商店": "shop", "科技": "science",
        "buff": "buff", "邮件": "mail", "充值": "recharge",
        "资源": "resource", "地图": "map", "公会": "alliance",
    })
    return cn_to_prefix

ENTITY_MAP = build_entity_map()

def find_seed_tables(entities: list[str],
                     table_hints: list[str] = None) -> list[str]:
    """多策略定位种子表，确保不遗漏"""
    seeds = set()

    # 0. 步骤①直接给出的 table_hints（最精确）
    if table_hints:
        for hint in table_hints:
            if hint in GRAPH["tables"]:
                seeds.add(hint)

    for entity in entities:
        prefix = ENTITY_MAP.get(entity, entity.lower())
        # 1. 表名前缀匹配
        for name in GRAPH["tables"]:
            if name == prefix or name.startswith(prefix + "_"):
                seeds.add(name)
        # 2. domain_label 匹配（覆盖不在前缀命名规则内的表）
        for name, t in GRAPH["tables"].items():
            if t.get("domain_label") == prefix:
                seeds.add(name)
        # 3. 列名包含实体 → 补充相关表
        for col_name, tables in COL_IDX.items():
            if entity in col_name:
                seeds.update(tables)

    # ── FALLBACK：如果所有策略都没命中，做模糊表名搜索 ──
    if not seeds:
        for name in GRAPH["tables"]:
            if any(e.lower() in name.lower() for e in entities):
                seeds.add(name)

    return list(seeds)
```

### 步骤 ③ 图遍历展开

从种子表沿关系边做 **BFS（广度优先，深度 ≤ 2）**，拉取关联表：

```python
def expand_graph(seed_tables: list[str],
                 relations: list[dict],
                 max_depth: int = 2,
                 min_conf: float = 0.6) -> dict:
    """
    返回 {table_name: {"depth": int, "path": str}} 的命中表集合
    """
    # 预建邻接表（双向）
    adj = {}  # table → [(neighbor, relation_dict)]
    for rel in relations:
        if rel["confidence"] < min_conf:
            continue
        adj.setdefault(rel["from_table"], []).append((rel["to_table"], rel))
        adj.setdefault(rel["to_table"], []).append((rel["from_table"], rel))

    visited = {t: {"depth": 0, "path": "seed"} for t in seed_tables}
    frontier = list(seed_tables)

    for depth in range(1, max_depth + 1):
        next_frontier = []
        for table in frontier:
            for neighbor, rel in adj.get(table, []):
                if neighbor not in visited:
                    path = f"{rel['from_table']}.{rel['from_column']}→{rel['to_table']}.{rel['to_column']}"
                    visited[neighbor] = {"depth": depth, "path": path, "conf": rel["confidence"]}
                    next_frontier.append(neighbor)
        frontier = next_frontier

    return visited
```

**关键参数**：
- `min_conf=0.6`：过滤噪声关系。值查询场景可提高到 0.7。
- `max_depth=2`：一般足够。超过 2 跳开销急剧膨胀且相关性大幅下降。
- 自带**去环**：visited 集合保证每张表只入队一次。

### 步骤 ④ 剪枝排序

展开后可能命中 30-50 张表，必须剪枝到 **10-15 张**以控制 token：

```python
def rank_and_prune(hit_tables: dict, seed_tables: list[str],
                   entities: list[str], max_tables: int = 12) -> list[str]:
    scored = []
    for name, info in hit_tables.items():
        score = 0.0
        # 种子表最高权重
        if name in seed_tables:
            score += 5.0
        # 图距离衰减（每跳 ×0.5）
        score += 3.0 * (0.5 ** info["depth"])
        # 关系置信度
        score += info.get("conf", 0) * 2.0
        # 表名命中实体加分
        for e in entities:
            prefix = ENTITY_MAP.get(e, e.lower())
            if prefix in name:
                score += 1.0
        scored.append((name, score))

    scored.sort(key=lambda x: -x[1])
    return [name for name, _ in scored[:max_tables]]
```

### 步骤 ⑤ 组装 Prompt

将命中表序列化为紧凑文本，拼入 system prompt：

```python
def build_context(table_names: list[str], graph: dict, relations: list[dict]) -> str:
    """将选中的表转为 LLM 上下文文本"""
    chunks = []
    for name in table_names:
        t = graph["tables"][name]
        pk = t.get("primary_key", "-")
        cols = t.get("columns", [])
        domain = t.get("domain_label", "other")

        # 列摘要（限制 20 列）
        col_parts = []
        for c in cols[:20]:
            col_parts.append(f"{c['name']}({c['dtype']})")
        if len(cols) > 20:
            col_parts.append(f"...+{len(cols)-20}列")

        # 关系摘要（该表的出向+入向，各限 5 条）
        out_rels = [r for r in relations if r["from_table"] == name and r["confidence"] >= 0.6]
        in_rels = [r for r in relations if r["to_table"] == name and r["confidence"] >= 0.6]
        out_rels.sort(key=lambda r: -r["confidence"])
        in_rels.sort(key=lambda r: -r["confidence"])

        rel_parts = []
        for r in out_rels[:5]:
            rel_parts.append(f"→{r['to_table']}({r['from_column']}→{r['to_column']} @{r['confidence']})")
        for r in in_rels[:5]:
            rel_parts.append(f"←{r['from_table']}({r['from_column']}→{r['to_column']} @{r['confidence']})")

        # 枚举值（token 高效的关键信息）
        enum_parts = []
        for col_name, values in t.get("enum_columns", {}).items():
            enum_parts.append(f"{col_name}={values}")

        chunk = f"### {name} [{domain}]\n"
        chunk += f"文件:{t['file_path']} 行:{t['row_count']} 列:{len(cols)} 主键:{pk}\n"
        chunk += f"列: {', '.join(col_parts)}\n"
        if enum_parts:
            chunk += f"枚举: {'; '.join(enum_parts)}\n"
        if rel_parts:
            chunk += f"关联: {', '.join(rel_parts)}\n"
        chunks.append(chunk)

    return "\n".join(chunks)
```

最终 Prompt 模板：

```
<system>
你是游戏配置数值分析助手。基于以下 Excel 配置表的元数据回答问题。

规则：
1. 只引用上下文中存在的表名、列名、枚举值，不编造
2. 跨表关系用 "A表.X列 → B表.Y列" 格式说明关联路径
3. 关系置信度 < 0.7 的标注"可能关联"
4. 涉及具体数值时说明数据来源（表名+列名+sample_values）
5. 不确定的回答"根据当前图谱数据无法确认"

<配置表上下文>
{build_context 输出，约 3K-8K tokens}
</配置表上下文>
</system>

<user>{用户问题}</user>
```

### 完整编排：answer_question()

将①-⑤串联为一个函数，另一个 AI 直接调用即可：

```python
def answer_question(user_input: str, llm_call) -> str:
    """
    端到端问答编排。
    
    参数:
        user_input: 用户自然语言问题
        llm_call: 你的 LLM 调用函数，签名 llm_call(system: str, user: str) -> str
    
    返回:
        LLM 的回答文本
    """
    # ① 意图提取（第 1 次 LLM 调用）
    extract_prompt = f"""你是一个游戏配置表查询解析器。

{SCHEMA_SUMMARY}

从用户问题中提取 JSON（只输出 JSON）：
- entities: 涉及的游戏概念（中文）
- table_hints: 从表名列表中定位到的表名
- intent: schema / value / impact / validate
- columns: 提到的具体字段名"""

    import json as _json
    raw = llm_call(extract_prompt, user_input)
    try:
        parsed = _json.loads(raw)
    except _json.JSONDecodeError:
        # 提取失败，用原文做模糊搜索
        parsed = {"entities": user_input.split(), "table_hints": [], "intent": "schema", "columns": []}

    entities = parsed.get("entities", [])
    table_hints = parsed.get("table_hints", [])
    intent = parsed.get("intent", "schema")

    # ② 定位种子表
    seeds = find_seed_tables(entities, table_hints)

    # ③ 图遍历展开
    min_conf = 0.7 if intent == "value" else 0.6
    hit_tables = expand_graph(seeds, GRAPH["relations"], max_depth=2, min_conf=min_conf)

    # ④ 剪枝排序
    selected = rank_and_prune(hit_tables, seeds, entities, max_tables=12)

    # ⑤ 组装 Prompt（第 2 次 LLM 调用）
    context = build_context(selected, GRAPH, GRAPH["relations"])

    system_prompt = f"""你是游戏配置数值分析助手。基于以下 Excel 配置表的元数据回答问题。

规则：
1. 只引用上下文中存在的表名、列名、枚举值，不编造
2. 跨表关系用 "A表.X列 → B表.Y列" 格式说明关联路径
3. 关系置信度 < 0.7 的标注"可能关联"
4. 涉及具体数值时说明数据来源（表名+列名+sample_values）
5. 不确定的回答"根据当前图谱数据无法确认"

<配置表上下文>
{context}
</配置表上下文>"""

    return llm_call(system_prompt, user_input)


# ── 使用示例 ──
# def my_llm(system, user):
#     return openai.chat(messages=[{"role":"system","content":system},{"role":"user","content":user}])
#
# answer = answer_question("英雄升到5星要消耗多少道具", my_llm)
```

> **整个 RAG 服务只需实现一个 `llm_call(system, user) -> str` 函数**，
> 剩下的召回、展开、剪枝、prompt 组装全在 `answer_question()` 内完成。

---

## 四、典型场景实操

### 4.1 结构查询："英雄怎么配置的"

| 步骤   | 操作                               | 结果                            |
| :----- | :--------------------------------- | :------------------------------ |
| ① 提取 | `entities=["英雄"], intent=schema` |                                 |
| ② 种子 | 前缀 `hero` + 列名含"英雄"         | 6 张表                          |
| ③ 展开 | BFS 深度 1                         | +skill, item, buff_attribute 等 |
| ④ 剪枝 | Top-10                             | hero + 4 子表 + 5 关联表        |
| ⑤ 注入 | ~4K tokens 上下文                  | LLM 输出表结构说明              |

### 4.2 数值查询："5星英雄升星消耗多少道具"

| 步骤   | 操作                                                                  | 结果                  |
| :----- | :-------------------------------------------------------------------- | :-------------------- |
| ① 提取 | `entities=["英雄","道具"], intent=value, columns=["星级","升阶消耗"]` |                       |
| ② 种子 | hero_hero_star（含 `星级+升阶消耗` 列） + item                        | 2 张核心表            |
| ③ 展开 | 深度 1，只拿 item 关联                                                | +3 张表               |
| ④ 剪枝 | Top-5 即够                                                            | hero_hero_star + item |
| ⑤ 注入 | hero_hero_star 的 sample_values 含具体消耗数据                        | LLM 直接引用          |

> **关键**：`sample_values` 最多采样 200 行，对于小表（hero_hero_star 仅 22 行）等于全量数据，LLM 可以直接从中提取具体数值。大表（>200 行）的 sample_values 只是抽样，LLM 应提示"基于采样数据"。

### 4.3 影响分析："改了英雄品质字段会影响什么"

| 步骤   | 操作                                     | 结果           |
| :----- | :--------------------------------------- | :------------- |
| ② 种子 | `hero`                                   |                |
| ③ 展开 | 重点看**入向关系**（谁引用了 hero）      | 被 6 张表引用  |
| ⑤ 注入 | 所有 `to_table=hero` 的关系 + 引用表结构 | LLM 列出影响面 |

```python
# 查"谁引用了 hero"的关系
impact_rels = [r for r in relations
               if r["to_table"] == "hero" and r["confidence"] >= 0.6]
# → monsterTroop_monsterHero.英雄ID, instanceTroop_instancePlayerHero.英雄ID, ...
```

### 4.4 配置校验："有没有引用了不存在道具ID的配置"

```python
# 取 item 表主键的所有值
item_table = graph["tables"]["item"]
pk_col = next(c for c in item_table["columns"] if c["name"] == item_table["primary_key"])
valid_ids = set(pk_col["sample_values"])

# 找所有引用 item 主键的关系
for rel in relations:
    if rel["to_table"] == "item" and rel["to_column"] == item_table["primary_key"]:
        src = graph["tables"][rel["from_table"]]
        src_col = next((c for c in src["columns"] if c["name"] == rel["from_column"]), None)
        if src_col:
            orphans = set(src_col["sample_values"]) - valid_ids
            if orphans:
                print(f"⚠ {rel['from_table']}.{rel['from_column']} 引用了不存在的ID: {orphans}")
```

> 注意：sample_values 是采样，大表可能漏检。要做完整校验需要加载原始 Excel。

---

## 五、置信度使用策略

关系的 `confidence` 是 RAG 质量的核心控制参数：

| 场景                         | 建议 min_conf                                  | 原因                     |
| :--------------------------- | :--------------------------------------------- | :----------------------- |
| 结构查询（"XX 怎么配的"）    | 0.6                                            | 需要全面性，容忍一些噪声 |
| 数值查询（"XX 消耗多少"）    | 0.7                                            | 需要精确关联，减少误导   |
| DAG 布局 / 依赖链分析        | 0.85                                           | 只保留核心骨架边         |
| 影响分析（"改 XX 影响什么"） | 0.6                                            | 宁可多报不能漏报         |
| 向 LLM 展示时的文案          | ≥0.8 直接陈述，0.6-0.8 加"关联"，<0.6 加"可能" | 分级标注不确定性         |

**当前数据的置信度分布**：
- 0.5–0.6: 1052 条（30%）— 噪声较多，慎用
- 0.6–0.7: 913 条（26%）— 基本可用
- 0.7–0.8: 963 条（28%）— 较可靠
- 0.8–1.0: 533 条（16%）— 高可信

---

## 六、防幻觉要点

| 风险                       | 对策                                              |
| :------------------------- | :------------------------------------------------ |
| LLM 编造不存在的表名/列名  | Prompt 限制"只引用上下文中的表名和列名"           |
| LLM 推算具体数值           | 要求"数值必须来自 sample_values，不要自行计算"    |
| 低置信度关系被当作确定事实 | 在上下文中标注 `@confidence`，Prompt 要求分级展示 |
| 误把 A→B 关系讲成 B→A      | 上下文中用 `→` / `←` 明确标注方向                 |
| 复合字段未解析（如 `"251,3 | 254,5"`）                                         | 在上下文中备注字段格式，让 LLM 解释而非盲猜 |

---

## 七、进阶用法

### 7.1 图分析能力

系统内置 `GraphAnalyzer`（`indexer/analysis/analyzer.py`），提供：

| 分析         | 用途                       | 调用                              |
| :----------- | :------------------------- | :-------------------------------- |
| **环检测**   | 找循环依赖（A→B→C→A）      | `analyzer.find_cycles()`          |
| **中心性**   | 找"核心表"（被引用最多的） | `analyzer.calculate_centrality()` |
| **社区发现** | 自动聚类业务模块           | `analyzer.find_communities()`     |
| **孤立节点** | 找没有任何关联的表         | `analyzer.find_isolated_nodes()`  |
| **关键路径** | 最长依赖链                 | `analyzer.find_critical_path()`   |

可以先跑 `analyzer.get_summary()` 拿到全局分析报告，作为 LLM 的"全局背景知识"注入。

### 7.2 CLI 快速查表

```bash
# 查询包含 "hero" 的表及其关系
python -m indexer --data-root <dir> --query hero
```

输出表元信息 + 出向/入向关系（按置信度排序），适合开发调试。

### 7.3 批量向量化

```bash
python -m indexer --data-root <dir> --export-llm chunks.jsonl
```

JSONL 每行：`{"id": "hero", "text": "## 表: hero [hero]\n- 文件: ..."}` — 直接灌入向量数据库做 embedding 索引。

### 7.4 多轮对话

单轮 `answer_question()` 无法处理追问（如"那具体消耗什么道具"依赖上文的"英雄升星"）。

推荐方案：**维护会话级种子表缓存**：

```python
class ConversationRAG:
    def __init__(self, llm_call):
        self.llm_call = llm_call
        self.history_seeds = []   # 最近 3 轮的种子表
        self.history_entities = []
    
    def ask(self, user_input: str) -> str:
        # ① 提取（同上）
        parsed = self._extract_intent(user_input)
        entities = parsed.get("entities", [])
        table_hints = parsed.get("table_hints", [])
        
        # 合并历史实体（追问场景）
        if not entities and self.history_entities:
            entities = self.history_entities[-1]
        
        seeds = find_seed_tables(entities, table_hints)
        
        # 合并历史种子（最近 1 轮，去重）
        if self.history_seeds:
            seeds = list(set(seeds + self.history_seeds[-1][:5]))  # 最多补 5 张
        
        # ②③④⑤ 同 answer_question()
        hit_tables = expand_graph(seeds, GRAPH["relations"])
        selected = rank_and_prune(hit_tables, seeds, entities)
        context = build_context(selected, GRAPH, GRAPH["relations"])
        answer = self.llm_call(self._build_system(context), user_input)
        
        # 记录本轮
        self.history_seeds.append(seeds)
        self.history_entities.append(entities)
        if len(self.history_seeds) > 3:
            self.history_seeds.pop(0)
            self.history_entities.pop(0)
        
        return answer
```

> 核心思路：追问时如果实体提取为空，复用上一轮的种子表；
> 如果有新实体，合并上一轮的 Top-5 种子表作为上下文延续。

### 7.5 反馈闭环

系统支持人工反馈修正关系（`data/indexer/feedback.json`）：

```jsonc
[
  {"from_table":"hero", "from_column":"英雄品质", "to_table":"hero_hero_star",
   "to_column":"稀有度", "action":"confirm"},  // 确认这条关系
  {"from_table":"activity", "from_column":"活动入口", "to_table":"item",
   "to_column":"道具分类排序", "action":"reject"}  // 拒绝误判关系
]
```

下次构建时自动应用。RAG 发现误召回时可以写回 feedback 形成闭环。

---

## 八、快速开始 Checklist

```
□ 1. 运行构建：python -m indexer --data-root <excel_dir> --run-now
□ 2. 导出 chunks：python -m indexer --data-root <dir> --export-llm chunks.jsonl
□ 3. 加载 schema_graph.json + column_index.json 到你的 RAG 服务
□ 4. 实现 find_seed_tables()：实体→表名映射 + 列索引查找
□ 5. 实现 expand_graph()：BFS 2 跳展开，min_conf=0.6
□ 6. 实现 rank_and_prune()：按距离/置信度/实体命中排序，剪枝到 12 张表
□ 7. 实现 build_context()：序列化为紧凑文本，控制在 8K tokens 内
□ 8. 组装 Prompt，加入防幻觉规则
□ 9. 测试：用 "英雄怎么配的" / "5星消耗多少" / "改品质影响什么" 验证召回质量
□ 10. 接入 feedback.json 做关系纠错闭环
```

---

## 附录：最小可运行示例

将以下代码保存为 `rag_service.py`，放在项目根目录，即可直接运行：

```python
"""最小可运行 RAG 服务 — 复制即用"""
import json
from pathlib import Path

# ═══════════════════════════════════════════
# 1. 加载数据（启动时执行一次）
# ═══════════════════════════════════════════
DATA_DIR = Path("data/indexer")
with open(DATA_DIR / "schema_graph.json", encoding="utf-8") as f:
    GRAPH = json.load(f)
with open(DATA_DIR / "column_index.json", encoding="utf-8") as f:
    COL_IDX = json.load(f)["column_to_tables"]

# ═══════════════════════════════════════════
# 2. 实体映射（自动 + 手工补充）
# ═══════════════════════════════════════════
ENTITY_MAP = {
    "英雄": "hero", "技能": "skill", "战斗": "battle", "道具": "item",
    "建筑": "building", "任务": "quest", "联盟": "alliance",
    "怪物": "monster", "奖励": "reward", "世界": "world",
    "社交": "social", "配置": "config",
    "兵种": "army", "装备": "equip", "活动": "activity",
    "副本": "instance", "商店": "shop", "科技": "science",
    "buff": "buff", "邮件": "mail", "充值": "recharge",
    "资源": "resource", "地图": "map", "公会": "alliance",
}

# ═══════════════════════════════════════════
# 3. Schema 摘要（build 时自动生成，直接读取）
# ═══════════════════════════════════════════
SCHEMA_SUMMARY = (DATA_DIR / "schema_summary.txt").read_text(encoding="utf-8")

# ═══════════════════════════════════════════
# 4. 核心函数（直接从文档第三章复制）
# ═══════════════════════════════════════════
def find_seed_tables(entities, table_hints=None):
    seeds = set()
    if table_hints:
        for h in table_hints:
            if h in GRAPH["tables"]:
                seeds.add(h)
    for entity in entities:
        prefix = ENTITY_MAP.get(entity, entity.lower())
        for name in GRAPH["tables"]:
            if name == prefix or name.startswith(prefix + "_"):
                seeds.add(name)
        for name, t in GRAPH["tables"].items():
            if t.get("domain_label") == prefix:
                seeds.add(name)
        for col_name, tables in COL_IDX.items():
            if entity in col_name:
                seeds.update(tables)
    if not seeds:  # fallback: 模糊表名匹配
        for name in GRAPH["tables"]:
            if any(e.lower() in name.lower() for e in entities):
                seeds.add(name)
    return list(seeds)

def expand_graph(seed_tables, relations, max_depth=2, min_conf=0.6):
    adj = {}
    for rel in relations:
        if rel["confidence"] < min_conf:
            continue
        adj.setdefault(rel["from_table"], []).append((rel["to_table"], rel))
        adj.setdefault(rel["to_table"], []).append((rel["from_table"], rel))
    visited = {t: {"depth": 0, "path": "seed", "conf": 1.0} for t in seed_tables}
    frontier = list(seed_tables)
    for depth in range(1, max_depth + 1):
        next_frontier = []
        for table in frontier:
            for neighbor, rel in adj.get(table, []):
                if neighbor not in visited:
                    visited[neighbor] = {
                        "depth": depth,
                        "path": f"{rel['from_table']}.{rel['from_column']}→{rel['to_table']}.{rel['to_column']}",
                        "conf": rel["confidence"]
                    }
                    next_frontier.append(neighbor)
        frontier = next_frontier
    return visited

def rank_and_prune(hit_tables, seed_tables, entities, max_tables=12):
    scored = []
    for name, info in hit_tables.items():
        score = 0.0
        if name in seed_tables:
            score += 5.0
        score += 3.0 * (0.5 ** info["depth"])
        score += info.get("conf", 0) * 2.0
        for e in entities:
            prefix = ENTITY_MAP.get(e, e.lower())
            if prefix in name:
                score += 1.0
        scored.append((name, score))
    scored.sort(key=lambda x: -x[1])
    return [name for name, _ in scored[:max_tables]]

def build_context(table_names, graph, relations):
    chunks = []
    for name in table_names:
        t = graph["tables"][name]
        pk = t.get("primary_key", "-")
        cols = t.get("columns", [])
        domain = t.get("domain_label", "other")
        col_parts = [f"{c['name']}({c['dtype']})" for c in cols[:20]]
        if len(cols) > 20:
            col_parts.append(f"...+{len(cols)-20}列")
        out_rels = sorted([r for r in relations if r["from_table"] == name and r["confidence"] >= 0.6],
                          key=lambda r: -r["confidence"])[:5]
        in_rels = sorted([r for r in relations if r["to_table"] == name and r["confidence"] >= 0.6],
                         key=lambda r: -r["confidence"])[:5]
        rel_parts = []
        for r in out_rels:
            rel_parts.append(f"→{r['to_table']}({r['from_column']}→{r['to_column']} @{r['confidence']})")
        for r in in_rels:
            rel_parts.append(f"←{r['from_table']}({r['from_column']}→{r['to_column']} @{r['confidence']})")
        enum_parts = [f"{k}={v}" for k, v in t.get("enum_columns", {}).items()]
        chunk = f"### {name} [{domain}]\n"
        chunk += f"文件:{t['file_path']} 行:{t['row_count']} 列:{len(cols)} 主键:{pk}\n"
        chunk += f"列: {', '.join(col_parts)}\n"
        if enum_parts:
            chunk += f"枚举: {'; '.join(enum_parts)}\n"
        if rel_parts:
            chunk += f"关联: {', '.join(rel_parts)}\n"
        chunks.append(chunk)
    return "\n".join(chunks)

# ═══════════════════════════════════════════
# 5. 端到端问答
# ═══════════════════════════════════════════
def answer_question(user_input: str, llm_call) -> str:
    """
    user_input: 用户问题
    llm_call: 接受 (system_prompt, user_msg) 返回 str 的函数
    """
    # ① 意图提取
    extract_sys = f"""你是一个游戏配置表查询解析器。
{SCHEMA_SUMMARY}
从用户问题中提取 JSON（只输出 JSON）：
- entities: 涉及的游戏概念（中文）
- table_hints: 从表名列表中定位到的表名
- intent: schema / value / impact / validate
- columns: 提到的具体字段名"""
    raw = llm_call(extract_sys, user_input)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {"entities": user_input.split(), "table_hints": [], "intent": "schema"}
    
    entities = parsed.get("entities", [])
    table_hints = parsed.get("table_hints", [])
    intent = parsed.get("intent", "schema")
    
    # ② 种子 → ③ 展开 → ④ 剪枝
    seeds = find_seed_tables(entities, table_hints)
    min_conf = 0.7 if intent == "value" else 0.6
    hit = expand_graph(seeds, GRAPH["relations"], max_depth=2, min_conf=min_conf)
    selected = rank_and_prune(hit, seeds, entities)
    
    # ⑤ 组装 + 调用
    ctx = build_context(selected, GRAPH, GRAPH["relations"])
    sys_prompt = f"""你是游戏配置数值分析助手。基于以下配置表元数据回答问题。
规则：
1. 只引用上下文中存在的表名、列名，不编造
2. 跨表关系用 "A表.X列 → B表.Y列" 格式
3. 置信度 < 0.7 标注"可能关联"
4. 数值必须来自 sample_values
5. 不确定回答"根据当前图谱数据无法确认"

<配置表上下文>
{ctx}
</配置表上下文>"""
    return llm_call(sys_prompt, user_input)


# ═══════════════════════════════════════════
# 6. 测试入口
# ═══════════════════════════════════════════
if __name__ == "__main__":
    # 替换为你的 LLM 调用
    def mock_llm(system, user):
        print(f"\n[System prompt] {len(system)} chars")
        print(f"[User] {user}")
        return '{"entities":["英雄"],"table_hints":["hero"],"intent":"schema","columns":[]}'
    
    result = answer_question("英雄怎么配置的", mock_llm)
    print(result)
```

> 将 `mock_llm` 替换为你的 OpenAI / 本地模型调用即可跑通全流程。
