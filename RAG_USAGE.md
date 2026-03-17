# 游戏配置表 Graph — 外部 RAG 系统接入指南

> 本文档面向需要接入当前图谱数据的**另一个 RAG 系统**，提供完整的数据说明、加载方式、召回接口和使用示例。

## 一、数据资产总览

所有导出文件在 `<excel_dir>/graph/` 目录下（即 `--data-root` 指定目录的 `graph/` 子目录）。当前版本：**1559 张表，32334 条关系**。

| 文件 | 大小 | 用途 | 加载优先级 |
|:--|:--|:--|:--|
| `schema_summary.txt` | 42 KB | 全量表名按域分组，注入 system prompt | **必须** |
| `column_index.json` | 1.0 MB | 列名→表名倒排索引，精确定位 | **必须** |
| `llm_chunks.jsonl` | 1.6 MB | 每表一条摘要，向量化召回 | **必须** |
| `schema_graph.json` | ~8 MB | 主图谱：表结构+关系+sample_values（持久化截断至30个） | **必须** |
| `cell_locator.json` | 2.6 MB | 单元格定位：表→文件→行号→列号 | 推荐 |
| `relation_graph.json` | 21 MB | 邻接表+JOIN 条件（双向） | 可选 |
| `table_profiles.jsonl` | ~5 MB | 每表富元数据 profile（sample_values 截断至8个） | 可选 |
| `join_paths.json` | ~20 MB | 预计算 1 跳直接 JOIN 路径 | 可选 |

> **v2 瘦身说明：** 相比 v1，`schema_graph.json` 从 52MB 降至 ~8MB（持久化时每列 sample_values 截断为 30 个，内存中关系发现仍使用完整采样）；`table_profiles.jsonl` 从 27MB 降至 ~5MB；`join_paths.json` 从 358MB 降至 ~20MB（默认 1 跳）。

---

## 二、快速接入（3 步）

### Step 1：加载数据

```python
import json
from pathlib import Path
from collections import defaultdict

DATA = Path("<excel_dir>/graph")  # --data-root 指定目录的 graph/ 子目录

# 1. 全量表名摘要（~42KB，常驻 system prompt）
SCHEMA_SUMMARY = (DATA / "schema_summary.txt").read_text(encoding="utf-8")

# 2. 列名倒排索引（7235 个列名 → 表名映射）
with open(DATA / "column_index.json", encoding="utf-8") as f:
    COL_INDEX: dict = json.load(f)
    # 兼容旧格式
    if "column_to_tables" in COL_INDEX:
        COL_INDEX = COL_INDEX["column_to_tables"]

# 3. 每表摘要 chunk（1559 条，用于向量化）
CHUNKS: dict[str, str] = {}
with open(DATA / "llm_chunks.jsonl", encoding="utf-8") as f:
    for line in f:
        obj = json.loads(line)
        CHUNKS[obj["id"]] = obj["text"]

# 4. 主图谱（表结构 + 关系，~8MB）
with open(DATA / "schema_graph.json", encoding="utf-8") as f:
    GRAPH = json.load(f)

# 5. 预构建关系索引（加速图扩展，~6ms）
REL_FROM: dict[str, list] = defaultdict(list)  # table → outgoing relations
REL_TO: dict[str, list] = defaultdict(list)    # table → incoming relations
for rel in GRAPH["relations"]:
    REL_FROM[rel["from_table"]].append(rel)
    REL_TO[rel["to_table"]].append(rel)

# 6. 单元格定位索引（可选）
CELL_LOCATOR: dict = {}
cell_loc_path = DATA / "cell_locator.json"
if cell_loc_path.exists():
    with open(cell_loc_path, encoding="utf-8") as f:
        CELL_LOCATOR = json.load(f)["tables"]
```

加载耗时：首次约 **120ms**，内存占用约 **80MB**（v2 瘦身后）。

### Step 2：向量化 llm_chunks

将 `CHUNKS` 中的 1559 条 `text` 做 embedding 存入向量数据库。

```python
# 示例：用 chromadb
import chromadb

client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection("game_tables")

ids = list(CHUNKS.keys())
texts = [CHUNKS[k] for k in ids]
collection.upsert(ids=ids, documents=texts)
```

每条 chunk 约 800-1800 字符，总共 1559 条，embedding 一次约 30 秒。

### Step 3：接入查询接口

见下方「核心接口」。

---

## 三、核心接口

### 接口 1：多路召回（推荐）

```python
def recall_tables(user_query: str, vector_db, top_k: int = 10) -> list[str]:
    """
    多路召回相关表名，返回排序后的表名列表。
    
    召回策略：
      1. 向量语义召回（模糊匹配）
      2. 列名精确匹配（精确匹配）
      3. 域名匹配（领域匹配）
    
    Returns:
        排序后的表名列表（最相关在前）
    """
    # ── 路径 1: 向量语义召回 ──
    hits = vector_db.query(query_texts=[user_query], n_results=top_k)
    vec_tables = hits["ids"][0] if hits["ids"] else []

    # ── 路径 2: 列名精确/模糊匹配 ──
    col_tables = find_tables_by_column(user_query)

    # ── 路径 3: 域名匹配 ──
    domain_kw = {
        "英雄": "hero", "技能": "skill", "buff": "skill",
        "道具": "item", "装备": "item", "商店": "item",
        "联盟": "alliance", "建筑": "building",
        "怪物": "monster", "战斗": "battle", "任务": "quest",
    }
    domain_tables = []
    for kw, domain in domain_kw.items():
        if kw in user_query:
            domain_tables.extend(
                name for name, t in GRAPH["tables"].items()
                if t.get("domain_label") == domain
            )

    # ── 合并去重（向量优先） ──
    seen = set()
    result = []
    for t in vec_tables + col_tables + domain_tables:
        if t not in seen and t in GRAPH["tables"]:
            seen.add(t)
            result.append(t)
    return result


def find_tables_by_column(query: str) -> list[str]:
    """通过列名关键词查找包含该列的表"""
    tables = set()
    for col_name, table_list in COL_INDEX.items():
        # 对查询中每个关键词做子串匹配
        for kw in _extract_keywords(query):
            if kw in col_name:
                tables.update(table_list)
    return list(tables)


def _extract_keywords(query: str) -> list[str]:
    """从查询中提取关键词（简单实现，可替换为分词器）"""
    # 去掉常见停用词，按 2-4 字滑窗提取
    stop = {"的", "是", "有", "在", "了", "吗", "呢", "怎么", "什么", "哪些", "如何"}
    words = [w for w in query if w not in stop]
    keywords = set()
    text = "".join(words)
    for length in [4, 3, 2]:
        for i in range(len(text) - length + 1):
            keywords.add(text[i:i+length])
    return list(keywords)
```

### 接口 2：图扩展

```python
def expand_tables(seed_tables: list[str],
                  min_confidence: float = 0.7,
                  max_total: int = 15) -> list[str]:
    """
    从种子表出发，沿关系图做 1-hop 扩展。
    
    Args:
        seed_tables: 召回的种子表名列表
        min_confidence: 关系置信度下限
        max_total: 最终返回的最大表数
    
    Returns:
        扩展后的表名列表（种子表在前，扩展表在后）
    """
    expanded = set()
    seed_set = set(seed_tables)

    for t in seed_tables:
        # outgoing: 本表引用的其他表
        for rel in REL_FROM.get(t, []):
            if rel["confidence"] >= min_confidence:
                expanded.add(rel["to_table"])
        # incoming: 引用本表的其他表
        for rel in REL_TO.get(t, []):
            if rel["confidence"] >= min_confidence:
                expanded.add(rel["from_table"])

    extra = [t for t in expanded if t not in seed_set]
    return (seed_tables + extra)[:max_total]
```

### 接口 3：组装 Context

```python
def build_context(tables: list[str],
                  include_joins: bool = True,
                  include_samples: bool = False) -> str:
    """
    将表列表组装为 LLM 可理解的 context 文本。
    
    Args:
        tables: 最终要注入的表名列表
        include_joins: 是否附加表间 JOIN 关系
        include_samples: 是否附加 sample_values（增加细节但更长）
    
    Returns:
        组装好的 context 文本
    """
    parts = []

    # 每张表的摘要
    for t in tables:
        if t in CHUNKS:
            parts.append(CHUNKS[t])

        # 可选：追加 sample_values 细节
        # 注意：持久化的 sample_values 最多 30 个（v2 瘦身）
        if include_samples and t in GRAPH["tables"]:
            table_info = GRAPH["tables"][t]
            for col in table_info["columns"][:10]:
                sv = col.get("sample_values", [])
                if sv:
                    parts.append(
                        f"  {t}.{col['name']}(采样{len(sv)}值): "
                        f"{str(sv[:10])}"
                    )

    # 补充表间 JOIN 关系
    if include_joins:
        table_set = set(tables)
        joins = []
        for t in tables:
            for rel in REL_FROM.get(t, []):
                if rel["to_table"] in table_set and rel["confidence"] >= 0.7:
                    joins.append(
                        f"JOIN: {rel['from_table']}.{rel['from_column']} → "
                        f"{rel['to_table']}.{rel['to_column']} "
                        f"(置信度:{rel['confidence']:.2f})"
                    )
        if joins:
            parts.append("\n".join(joins))

    return "\n\n".join(parts)
```

### 接口 4：单元格定位

```python
def locate_cell(table_name: str, pk_value, column_name: str) -> dict | None:
    """
    定位到具体的 Excel 单元格地址。
    
    Args:
        table_name: 表名（如 "hero"）
        pk_value: 主键值（如 5）
        column_name: 列名（如 "英雄主动技能ID"）
    
    Returns:
        {
          "file": "hero.xlsx",
          "sheet": "hero",
          "cell": "P6",           # Excel 单元格地址
          "excel_row": 6,
          "excel_col": "P"
        }
        或 None（定位失败）
    
    覆盖范围:
        261/1559 张表可精确到单元格（行数≤200且主键唯一的表）
        其余表只能定位到列 + 数据起始行
    """
    if not CELL_LOCATOR:
        return None

    loc = CELL_LOCATOR.get(table_name)
    if not loc:
        return None

    col_info = loc["columns"].get(column_name)
    if not col_info:
        return None

    excel_col = col_info["excel_col"]

    # 精确行定位（小表）
    pk_map = loc.get("pk_to_excel_row", {})
    excel_row = pk_map.get(str(pk_value))

    if excel_row:
        return {
            "file": loc["file"],
            "sheet": loc["sheet"],
            "cell": f"{excel_col}{excel_row}",
            "excel_row": excel_row,
            "excel_col": excel_col,
        }

    # 大表：返回列+起始行
    return {
        "file": loc["file"],
        "sheet": loc["sheet"],
        "cell": None,
        "excel_col": excel_col,
        "data_start_row": loc["data_start_row"],
        "hint": f"在 {loc['file']} 的 {loc['sheet']} sheet "
                f"的 {excel_col} 列查找主键={pk_value}",
    }
```

### 接口 5：完整 answer（一站式）

```python
def answer(user_query: str, vector_db, llm_call) -> str:
    """
    一站式问答接口：召回 → 扩展 → 组装 → LLM 推理。
    
    Args:
        user_query: 用户问题
        vector_db: 向量数据库实例（需有 .query() 方法）
        llm_call: LLM 调用函数 fn(system_prompt, user_msg) -> str
    
    Returns:
        LLM 生成的回答文本
    
    典型延迟:
        本地处理 ~5ms + LLM 推理 ~2-4s = 总计 ~2-4s
    """
    # 1. 多路召回
    seed_tables = recall_tables(user_query, vector_db, top_k=10)

    # 2. 图扩展
    final_tables = expand_tables(seed_tables, min_confidence=0.7, max_total=15)

    # 3. 组装 context
    context = build_context(final_tables, include_joins=True)

    # 4. 注入 LLM
    system = f"""你是游戏配置数值分析助手。基于以下配置表元数据回答问题。

规则：
1. 只引用上下文中存在的表名和列名，不编造
2. 跨表关系用 "A表.X列 → B表.Y列" 格式
3. 引用数据时说明是全量还是采样
4. 需要定位原始数据时给出 文件名/sheet/列名
5. 不确定时回答"根据当前图谱数据无法确认"

<全量表名索引>
{SCHEMA_SUMMARY}
</全量表名索引>

<召回的配置表详情>
{context}
</召回的配置表详情>"""

    return llm_call(system, user_query)
```

---

## 四、数据格式详解

### schema_graph.json — 主图谱

```json
{
  "tables": {
    "hero": {
      "name": "hero",
      "file_path": "hero.xlsx",
      "sheet_name": "hero",
      "row_count": 17,
      "primary_key": "键值",
      "domain_label": "hero",
      "header_offset": 0,
      "columns": [
        {
          "name": "英雄主动技能ID",
          "dtype": "int",
          "sample_values": [101, 102, 103],
          "unique_count": 15,
          "is_fk_candidate": true
        }
      ],
      "enum_columns": {"英雄品质": [2, 3, 4, 5]},
      "numeric_columns": ["基础战斗力", "baseHP"]
    }
  },
  "relations": [
    {
      "from_table": "hero",
      "from_column": "英雄主动技能ID",
      "to_table": "skill",
      "to_column": "键值",
      "confidence": 0.77,
      "relation_type": "fk_content_subset",
      "discovery_method": "containment",
      "evidence": "shared(15): 101,102,103..."
    }
  ]
}
```

**关键字段说明：**

| 字段 | 说明 |
|:--|:--|
| `row_count` | 数据行数（不含表头） |
| `header_offset` | pandas header 后跳过的元数据行数（类型行等） |
| `sample_values` | 列的采样值（持久化截断至 **30 个**；构建时内存中使用完整采样做关系发现） |
| `enum_columns` | 枚举列及其所有值（唯一值少且比例低的列） |
| `confidence` | 关系置信度 0-1（≥0.8 高信度，0.6-0.8 中等，<0.6 低） |
| `relation_type` | `fk_naming_convention`(命名推断) / `fk_content_subset`(值包含) / `fk_abbreviation`(缩写匹配) / `inferred_transitive`(传递推断) |
| `discovery_method` | 发现策略：`naming_convention` / `containment` / `abbreviation` / `transitive` |
| `evidence` | 可读证据摘要（共享值样本、命名匹配说明等） |

### llm_chunks.jsonl — 向量化摘要

每行一个 JSON，共 1559 行：

```json
{"id": "hero", "text": "## 表: hero [hero]\n- 文件: hero.xlsx | sheet: hero\n- 行数: 17 | 列数: 37 | 主键: 键值\n- 列: 键值(int), 英雄名字(str), 英雄品质(int), 英雄主动技能ID(int)→skill.键值, ...\n- 关联: → skill(英雄主动技能ID→键值 @0.77), ← monsterTroop_monsterHero(英雄ID→键值 @0.77)\n- 标注: 中心性:5.2 | 同模块: hero_hero_level, hero_hero_star, ...\n"}
```

### column_index.json — 列名倒排索引

```json
{
  "键值": ["hero", "skill", "buff", "weapon", ...],
  "英雄ID": ["monsterTroop_monsterHero", ...],
  "configEditor": ["ABtest", "Setting", "Switch", ...]
}
```

共 7235 个列名，每个映射到包含该列的表名列表。

### cell_locator.json — 单元格定位

```json
{
  "tables": {
    "hero": {
      "file": "hero.xlsx",
      "sheet": "hero",
      "data_start_row": 2,
      "row_count": 17,
      "columns": {
        "键值":           {"excel_col": "A", "col_idx": 0},
        "英雄名字":       {"excel_col": "C", "col_idx": 2},
        "英雄主动技能ID": {"excel_col": "P", "col_idx": 15}
      },
      "pk_column": "键值",
      "pk_excel_col": "A",
      "pk_to_excel_row": {
        "1": 2, "2": 3, "3": 4, "5": 6, "1000": 19
      }
    }
  }
}
```

`pk_to_excel_row` 仅对行数 ≤200 且主键唯一的表提供（261/1559 张）。

### schema_summary.txt — 表名总览

```
# Schema Summary — 1559 tables, 32334 relations

可用配置表（按业务域分组）：
[alliance] Alliance_AllianceSetting, AllianceTech, AllianceShop, ...
[battle] army, battleAttribute, combatStrength, BattlePass, ...
[hero] hero, hero_hero_star, hero_hero_level, ...
[item] item, equip, shop_shop_item, resource, ...
[skill] skill, buff, buff_attribute, instanceSkill, ...
[monster] monsterTroop, worldMonster, instanceMonster, ...
...
```

---

## 五、性能基准

### 一次查询各阶段耗时（实测）

| 阶段 | 耗时 | 说明 |
|:--|:--|:--|
| 向量检索 (1559 docs) | 5-20 ms | 本地 FAISS/Chroma |
| 列名匹配 (7235 cols) | ~2 ms | 内存 dict 遍历 |
| 图扩展 (1-hop) | ~0.05 ms | 预构建索引 |
| 组装 Context | ~3 ms | 15 张表拼接 |
| 单元格定位 | ~0.01 ms | dict 查找 |
| **本地总计** | **~5 ms** | |
| Embedding API | 50-200 ms | OpenAI / 本地模型 |
| LLM 推理 | 1500-5000 ms | **95% 的时间在这** |
| **端到端总计** | **~2-5 秒** | |

### 启动加载耗时

| 文件 | 耗时 |
|:--|:--|
| schema_graph.json (~8 MB) | ~50 ms |
| llm_chunks.jsonl (1.6 MB) | 8 ms |
| column_index.json (1.0 MB) | 6 ms |
| cell_locator.json (2.6 MB) | 19 ms |
| 关系索引构建 | 6.5 ms |
| **合计** | **~120 ms** |

### 图谱构建耗时

| 模式 | 耗时 | 说明 |
|:--|:--|:--|
| 全量构建 (1559 表) | ~60-120s | 首次构建或强制全量 |
| 增量构建 (1 表变更) | ~3-10s | 只重新发现涉及变更表的关系 |
| 增量构建 (无变更) | <1s | 跳过关系发现，直接返回 |

---

## 六、关键参数调优

| 参数 | 推荐值 | 说明 |
|:--|:--|:--|
| 向量召回 `top_k` | 10 | 1559 张表，适当放宽 |
| 列名匹配关键词长度 | 2-4 字 | 太短噪声多，太长漏召 |
| 图扩展 `min_confidence` | 0.7 | 只用高置信度关系 |
| 图扩展 `max_total` | 15 | 控制 context 在 20K tokens 内 |
| Context 中 confidence 展示 | ≥0.8 直述，0.6-0.8 标注"可能" | 给 LLM 判断参考 |

---

## 七、128K 上下文优化方案

如果你的 LLM 支持 128K context，可以采用分层策略：

```
┌──────────── 128K Context Window ────────────┐
│                                              │
│  Layer 0 (常驻 ~15K tokens)                  │
│  ├── System Prompt + 规则                    │
│  └── schema_summary.txt（全量表名索引）       │
│                                              │
│  Layer 1 (动态 ~40-60K tokens)               │
│  ├── 核心表的 llm_chunks（详细摘要）          │
│  ├── sample_values（关键列的采样值）          │
│  └── JOIN 路径                               │
│                                              │
│  Layer 2 (预留 ~40K tokens)                  │
│  └── 多轮对话历史                            │
│                                              │
└──────────────────────────────────────────────┘
```

开启 **Prefix Caching** 后，Layer 0 的 ~15K tokens 只在首次请求时计算，后续请求自动复用缓存，可降低 30-50% 延迟和费用。

---

## 八、LLM 自动调用示例（Tool Use / Function Calling）

如果你的 RAG 系统支持 Tool Use，可以将上述接口注册为 LLM 可调用的工具：

```python
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_game_tables",
            "description": "搜索游戏配置表。输入关键词，返回相关表的结构、列信息和表间关系。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词，如'英雄技能'、'商店价格'、'联盟科技'"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "返回的最大表数量",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_table_detail",
            "description": "获取指定表的完整结构信息，包括所有列、数据类型、采样值、关联关系。",
            "parameters": {
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "表名，如 'hero'、'skill'、'item'"
                    }
                },
                "required": ["table_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "locate_excel_cell",
            "description": "定位配置数据在 Excel 文件中的具体位置（文件、sheet、单元格地址）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "table_name": {"type": "string", "description": "表名"},
                    "pk_value": {"type": "string", "description": "主键值"},
                    "column_name": {"type": "string", "description": "列名"}
                },
                "required": ["table_name", "pk_value", "column_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_join_path",
            "description": "查找两张表之间的关联路径（经过哪些中间表、用哪些列 JOIN）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "from_table": {"type": "string", "description": "起始表名"},
                    "to_table": {"type": "string", "description": "目标表名"}
                },
                "required": ["from_table", "to_table"]
            }
        }
    }
]
```

### Tool 实现

```python
def handle_tool_call(tool_name: str, args: dict) -> str:
    """处理 LLM 发起的 tool call，返回 JSON 字符串结果。"""

    if tool_name == "search_game_tables":
        query = args["query"]
        top_k = args.get("top_k", 10)
        seed = recall_tables(query, vector_db, top_k=top_k)
        tables = expand_tables(seed, max_total=top_k)
        context = build_context(tables, include_joins=True)
        return json.dumps({
            "tables_found": len(tables),
            "table_names": tables,
            "detail": context
        }, ensure_ascii=False)

    elif tool_name == "get_table_detail":
        name = args["table_name"]
        table = GRAPH["tables"].get(name)
        if not table:
            return json.dumps({"error": f"表 '{name}' 不存在"})
        # 返回完整结构
        result = {
            "name": name,
            "file": table["file_path"],
            "sheet": table["sheet_name"],
            "row_count": table["row_count"],
            "primary_key": table["primary_key"],
            "domain": table.get("domain_label", "other"),
            "columns": [
                {
                    "name": c["name"],
                    "dtype": c.get("dtype", "?"),
                    "sample_values": c.get("sample_values", [])[:10],
                    "unique_count": c.get("unique_count", 0),
                }
                for c in table["columns"]
            ],
            "outgoing": [
                f"{r['from_column']} → {r['to_table']}.{r['to_column']} "
                f"(@{r['confidence']:.2f})"
                for r in REL_FROM.get(name, [])
                if r["confidence"] >= 0.6
            ][:20],
            "incoming": [
                f"{r['from_table']}.{r['from_column']} → {r['to_column']} "
                f"(@{r['confidence']:.2f})"
                for r in REL_TO.get(name, [])
                if r["confidence"] >= 0.6
            ][:20],
        }
        return json.dumps(result, ensure_ascii=False)

    elif tool_name == "locate_excel_cell":
        result = locate_cell(
            args["table_name"], args["pk_value"], args["column_name"]
        )
        return json.dumps(result or {"error": "无法定位"}, ensure_ascii=False)

    elif tool_name == "find_join_path":
        ft, tt = args["from_table"], args["to_table"]
        # 实时 BFS 查找最短路径（≤3 跳，join_paths.json 仅预计算 1 跳）
        path = _bfs_join_path(ft, tt, max_hops=3)
        return json.dumps(path or {"error": f"未找到 {ft} → {tt} 的路径"},
                          ensure_ascii=False)

    return json.dumps({"error": f"未知工具: {tool_name}"})


def _bfs_join_path(src: str, dst: str, max_hops: int = 3) -> dict | None:
    """BFS 查找两表间最短 JOIN 路径"""
    from collections import deque
    if src not in GRAPH["tables"] or dst not in GRAPH["tables"]:
        return None
    queue = deque([(src, [src], [], 1.0)])
    visited = {src}
    while queue:
        node, path, joins, min_conf = queue.popleft()
        if node == dst:
            return {
                "from": src, "to": dst,
                "hops": len(path) - 1,
                "path": path,
                "joins": joins,
                "min_confidence": round(min_conf, 3)
            }
        if len(path) - 1 >= max_hops:
            continue
        for rel in REL_FROM.get(node, []) + REL_TO.get(node, []):
            neighbor = (rel["to_table"] if rel["from_table"] == node
                        else rel["from_table"])
            if neighbor not in visited and rel["confidence"] >= 0.6:
                visited.add(neighbor)
                join_str = (f"{rel['from_table']}.{rel['from_column']} = "
                            f"{rel['to_table']}.{rel['to_column']}")
                queue.append((
                    neighbor,
                    path + [neighbor],
                    joins + [join_str],
                    min(min_conf, rel["confidence"])
                ))
    return None
```

---

## 九、完整接入示例

```python
"""
完整示例：接入 OpenAI GPT-4o + ChromaDB
"""
import json
from openai import OpenAI

# ── 初始化 ──
# 1. 加载图谱数据（见 Step 1）
# 2. 初始化向量库（见 Step 2）
# 3. 初始化 LLM
client = OpenAI()

def llm_with_tools(user_query: str) -> str:
    """支持 tool use 的多轮调用"""
    messages = [
        {"role": "system", "content": f"""你是游戏配置数值分析助手。
你可以通过工具查询游戏配置表的结构和关联关系。
可用配置表总览：
{SCHEMA_SUMMARY}"""},
        {"role": "user", "content": user_query}
    ]

    while True:
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto"
        )
        msg = resp.choices[0].message

        # 无 tool call → 直接返回
        if not msg.tool_calls:
            return msg.content

        # 执行 tool calls
        messages.append(msg)
        for tc in msg.tool_calls:
            result = handle_tool_call(
                tc.function.name,
                json.loads(tc.function.arguments)
            )
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result
            })

# ── 使用 ──
print(llm_with_tools("英雄的主动技能伤害在哪些表里配置？"))
print(llm_with_tools("帮我定位5号英雄的技能ID在Excel哪个位置"))
print(llm_with_tools("item表和reward表之间怎么关联？"))
```

---

## 十、数据更新（增量构建）

### 构建模式

```bash
# 首次全量构建（产出到 <excel_dir>/graph/）
python -m indexer --data-root "你的Excel目录" --run-now

# 增量构建（推荐：Excel 修改后执行，秒级完成）
python -m indexer --data-root "你的Excel目录" --run-now

# 可选：后台守护模式（监听文件变化 + 定时重建）
python -m indexer --data-root "你的Excel目录" --daemon --schedule daily:02:00

# 产出目录默认为 <data-root>/graph/，可通过 --storage-dir 自定义
```

> `--run-now` 默认使用增量模式：加载已有图谱，只处理变更文件。

### 增量构建原理

增量构建通过以下机制实现秒级更新：

```
                     ┌─────────────────────────────────────────┐
 磁盘文件变更         │  Scanner（mtime 对比）                   │
 ──────────────────> │  ├── 新文件 → new_tables                │
                     │  ├── mtime 变化 → updated_tables        │
                     │  ├── 文件消失 → deleted_tables           │
                     │  └── 未变化 → unchanged（跳过读取）       │
                     └───────────────┬─────────────────────────┘
                                     │ affected_tables = new ∪ updated ∪ deleted
                                     ▼
                     ┌─────────────────────────────────────────┐
 已有 32000+ 关系     │  Builder（精确增量）                      │
 ──────────────────> │  1. 只删除 affected_tables 涉及的关系     │
                     │  2. 保留其余关系不动                       │
                     │  3. 只重新发现涉及 affected_tables 的关系  │
                     │  4. 融合 + 去重 + 导出                    │
                     └─────────────────────────────────────────┘
```

**关键优化点：**

| 阶段 | 全量 | 增量（1 表变更） |
|:--|:--|:--|
| 文件读取 | 1559 个 Excel | 仅 1 个变更文件 |
| 关系清除 | 全部清空 | 只清除涉及变更表的 ~50 条 |
| 关系发现 | 全部列对比较 | 只比较涉及变更表的列对 |
| 保留关系 | 0 条 | ~31950 条直接保留 |

### 支持的变更类型

| 变更类型 | 检测方式 | 处理 |
|:--|:--|:--|
| **新增 Excel 文件** | 磁盘存在但图谱中无对应表 | 读取文件 → 提取 Schema → 发现与所有表的关系 |
| **修改 Excel 文件** | 文件 mtime 变化（1 秒容差） | 重新读取 → 更新 Schema → 重新发现涉及该表的关系 |
| **删除 Excel 文件** | 图谱中有但磁盘上已不存在 | 移除表 + 移除所有涉及该表的关系 |
| **表结构变更** | 列增减、类型变更 | 记录 changelog → 重新发现涉及该表的关系 |

### 变更日志

每次构建会在 `schema_graph.json` 的 `changelog` 字段记录变更历史（保留最近 200 条）：

```json
{
  "changelog": [
    {
      "timestamp": "2026-03-17T14:00:00",
      "table_name": "hero",
      "change_type": "added_columns",
      "details": "新增列: 英雄觉醒等级, 觉醒技能ID"
    },
    {
      "timestamp": "2026-03-17T14:00:00",
      "table_name": "new_activity",
      "change_type": "table_added",
      "details": "新增表 (25 列, 100 行)"
    }
  ]
}
```

变更类型包括：`table_added`、`table_removed`、`added_columns`、`removed_columns`、`type_changed`。

### 外部 RAG 系统更新

重建后 `<excel_dir>/graph/` 下的所有文件会自动更新。外部 RAG 系统需要：

1. **重新加载** `schema_graph.json`、`schema_summary.txt` 等文件
2. **增量更新向量库**：对比新旧 `llm_chunks.jsonl`，只 upsert 变化的 chunk

```python
def incremental_update_vectors(vector_db, old_chunks: dict, new_chunks: dict):
    """增量更新向量库：只处理变化的 chunk"""
    # 删除已移除的表
    removed = set(old_chunks.keys()) - set(new_chunks.keys())
    if removed:
        vector_db.delete(ids=list(removed))

    # 新增或变更的表
    changed = {
        k: v for k, v in new_chunks.items()
        if k not in old_chunks or old_chunks[k] != v
    }
    if changed:
        vector_db.upsert(
            ids=list(changed.keys()),
            documents=list(changed.values())
        )

    return len(removed), len(changed)
```
