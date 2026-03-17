# RAG 数据资产优化待办清单

> **范围**：仅限 graph-builder 导出数据侧的改进。不涉及 RAG 使用侧的查询逻辑、向量化、prompt 组装等。
>
> **原则**：我们只提供更好的数据，让 RAG 系统有更多可用的信号来提高召回速度和准确度。

---

## 已完成

### ~~1. 导出 `analysis.json`~~ ✅

导出 centrality / modules / orphans / cycles / critical_path，RAG 侧可用于排序加权、同模块聚合、孤立表降权等。

### ~~2. `column_index.json` 增强子索引~~ ✅

`_cn_segments`（中文实体词→表名）和 `_normalized`（去 FK 后缀归一化列名→表名）已作为子索引自动导出。

### ~~3. `table_profiles.jsonl` 的 `searchable_text`~~ ✅

包含表名、域中文名、中文同义词、列名、枚举文本值、关联表名，供 RAG 侧向量化用。

### ~~4. `join_paths.json` 预计算~~ ✅

BFS 预计算的表间最短 JOIN 路径已导出，RAG 侧可 O(1) 查找两表间 JOIN 链。

---

## P0 — 必做（数据质量缺口明显，改动小） ✅ 全部完成

### ~~5. [准确度] 值反查索引 `value_index.json`~~ ✅ 已完成

已改动：
- `indexer/export/rag_assets.py` — 新增 `export_value_index()`，扫描 FK 候选列和枚举列的 sample_values，收集跨 ≥2 张表的共享值，导出为 `{值: [{table, column}, ...]}` 格式
- `indexer/export/__init__.py` — 注册导出
- `indexer/service.py` — 构建后自动导出 `value_index.json`（第 10 个资产）

---

### ~~6. [准确度] 关系证据增强~~ ✅ 已完成

已改动：
- `indexer/export/rag_assets.py` — `export_relation_graph()` 的每条邻居关系新增 `evidence` 字段（shared_values 样本、shared_count、from_total、to_total）和 `evidence_desc` 字段（来自 `RelationEdge.evidence` 的可读描述）
- 新增 helper `_compute_shared_values()` 计算两列 sample_values 交集

---

### ~~7. [准确度] 表自动描述~~ ✅ 已完成

已改动：
- `indexer/export/rag_assets.py` — `export_table_profiles()` 每条 profile 新增 `description` 字段，基于域中文名、列名、表规模、引用关系自动拼接中文描述
- 新增 helper `_generate_table_description()` 生成规则

---

### ~~8. [准确度] 域级关系图 `domain_graph.json`~~ ✅ 已完成

已改动：
- `indexer/export/rag_assets.py` — 新增 `export_domain_graph()`，聚合表级关系为域级，导出域列表（含表名和中文名）+ 跨域关系统计（relation_count / avg_confidence / max_confidence）
- `indexer/export/__init__.py` — 注册导出
- `indexer/service.py` — 构建后自动导出 `domain_graph.json`（第 11 个资产）
- `RAG_USAGE.md` — 数据资产表新增 `value_index.json` 和 `domain_graph.json` 条目

---

## P1 — 推荐做（显著提升数据丰富度） ✅ 全部完成

### ~~9. [准确度] 枚举值交叉索引 `enum_cross_ref.json`~~ ✅ 已完成

已改动：
- `indexer/export/rag_assets.py` — 新增 `export_enum_cross_ref()`，按列名分组比对枚举列，找出跨表共享枚举空间（overlap ≥ 50%）的列组，导出列名、表名、共享值、重叠率
- `indexer/export/__init__.py` — 注册导出
- `indexer/service.py` — 构建后自动导出 `enum_cross_ref.json`（第 12 个资产）
- `RAG_USAGE.md` — 数据资产表新增条目

---

### ~~10. [准确度] `searchable_text` 增加缩写展开词~~ ✅ 已完成

已改动：
- `indexer/export/rag_assets.py` — `export_table_profiles()` 的 searchable_parts 生成逻辑中，利用 `GAME_ABBREVIATIONS` 词典将列名缩写展开（如 `atk`→`attack`，`hp`→`hitpoint health`），加入 searchable_text

---

### ~~11. [准确度] `llm_chunks.jsonl` 增加 sample_values 摘要~~ ✅ 已完成

已改动：
- `indexer/export/llm_chunks.py` — `export_llm_chunks()` 列摘要增加值域信息：
  - PK 列：`id(int)[1~320,共320]`
  - 枚举列（文本值）：`quality(int)[普通,精英,传说]`
  - 枚举列（数值）：`type(int)[1,2,3,4]`
  - FK 列和普通列保持不变

---

## P2 — 可选做（锦上添花）

### 12. [准确度] 导出列语义类型标注

- **现状**：列信息只有 name + dtype（`int`/`str`/`float`），缺少语义层面的类型标注
- **做法**：基于列名模式和 `game_dictionary` 推断语义类型，在 `table_profiles.jsonl` 的列信息中增加 `semantic_type` 字段
- **类型示例**：`currency`、`timestamp`、`count`、`reference_id`、`enum_quality`、`name_text`、`percentage`
- **效果**：RAG 侧可以按语义类型过滤列（"所有货币相关的列"）
- **改动范围**：新增 `_infer_semantic_type()` + `export_table_profiles()` 集成

---

### 13. [数据完整性] `schema_summary.txt` 增加域间关系概述

- **现状**：`schema_summary.txt` 只列出了域名和表名，缺少域间关系信息。RAG 侧 LLM 在意图提取时不知道"hero 域和 skill 域有什么关系"
- **做法**：在 `export_schema_summary()` 末尾追加域间关系概述（依赖 #8 的 domain_graph 数据，或直接在此函数内聚合）
- **示例**：
  ```
  ## 域间关系
  hero ↔ skill: 5条关系 | hero ↔ item: 3条关系 | quest ↔ reward: 4条关系
  ```
- **效果**：LLM 做意图提取时能看到域间的关联强度，更准确地选择相关域
- **改动范围**：`export_schema_summary()` 追加聚合逻辑

---

## 已归档（不在本工程范围 / 不推荐）

| 编号 | 原方案 | 结论 |
|:-----|:-------|:-----|
| - | 规则引擎替代首次 LLM 调用 | ❌ 不推荐：LLM 语义理解不可替代，780 tokens 成本极低 |
| - | Intent-aware 图遍历方向 | ❌ 不推荐：FK 方向≠影响方向，砍方向导致漏召回，噪音交给排序处理 |
| - | `searchable_text` 替代 `llm_chunks` 做向量化 | ⏭️ RAG 侧选择，数据已就绪 |
| - | `rank_and_prune()` centrality 加权排序 | ⏭️ RAG 侧逻辑，已在 `RAG_RECALL_DESIGN.md` 中示范 |
| - | 同模块表优先排序 | ⏭️ RAG 侧逻辑，`analysis.json` 的 modules 数据已就绪 |
| - | 预构建邻接索引 | ⏭️ RAG 侧逻辑，已在 `RAG_RECALL_DESIGN.md` 中示范 |
| - | entity→seeds 预缓存 | ⏭️ RAG 侧逻辑 |
| - | Prefix Caching | ⏭️ RAG 侧 LLM 调用优化 |

---

## 总结

| 级别 | 数量 | 状态 | 核心收益 |
|:-----|:-----|:-----|:---------|
| 已完成（早期） | 4 项 | ✅ | analysis.json + column_index 增强 + searchable_text + join_paths |
| P0 | 4 项 | ✅ | 值反查索引 + 关系证据增强 + 表中文描述 + 域级关系图 |
| P1 | 3 项 | ✅ | 枚举交叉索引 + searchable_text 缩写展开 + llm_chunks 值域信息 |
| P2 | 2 项 | 待做 | 列语义类型 + schema_summary 域间关系 |

当前共导出 **12 个数据资产文件**。RAG 侧优化建议已写入 `RAG_USAGE.md` 第八章（9 条，含代码示例和避坑说明）。
