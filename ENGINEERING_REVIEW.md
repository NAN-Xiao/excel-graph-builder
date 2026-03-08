# 工程复盘与 RAG 可行性评估

> 基于 `excel-graph-builder` 真实数据运行结果（206 表 / 3833 关系），评估当前工程对"游戏策划配置图谱 + LLM 问答"需求的完成度。

---

## 一、需求回顾

| 维度       | 需求描述                                          | 关键难点              |
| ---------- | ------------------------------------------------- | --------------------- |
| **规模**   | 千级 Excel 文件，万行百列宽表                     | 内存/时间复杂度       |
| **准确性** | 字段外键关联不仅复杂而且模糊（无显式 FK）         | 噪声抑制 + 召回率     |
| **完整性** | 召回后要详细不遗漏                                | 关系链路完整遍历      |
| **可用性** | 数据作为 LLM 问答依据，辅助运营分析/数值分析/决策 | 结构化导出 + 语义可读 |

---

## 二、当前工程实测数据

### 2.1 构建产出

```
数据源:  113 个 Excel 文件（I:\slgconfiguration\excel）
产出:    206 张表, 3833 条关系
耗时:    扫描 0.8s + 发现 0.2s = 总计 1.0s
```

### 2.2 关系质量分布

| 置信度区间 | 数量 | 占比  | 质量判断                     |
| ---------- | ---- | ----- | ---------------------------- |
| >= 0.8     | 379  | 9.9%  | ✅ 高可信，可直接用于问答     |
| 0.6 ~ 0.8  | 2016 | 52.6% | ⚠️ 中等，大部分可用但有噪声   |
| 0.45 ~ 0.6 | 1438 | 37.5% | ❌ 噪声密集区，含大量巧合匹配 |

### 2.3 发现策略覆盖

| 策略                          | 发现数            | 说明                   |
| ----------------------------- | ----------------- | ---------------------- |
| containment（包含度检测）     | 3833              | 唯一有效策略           |
| naming_convention（命名约定） | **0**             | ⛔ 完全失效             |
| abbreviation（缩写推断）      | 0                 | 依赖 naming_convention |
| transitive（传递推断）        | 500 生成 → 0 存活 | 去重时被合并           |

### 2.4 业务域分布（domain_label）

```
other: 77    battle: 16   config: 19   skill: 21
building: 13  item: 18    quest: 8     hero: 7
alliance: 10  reward: 5   monster: 7   world: 3   social: 2
```

---

## 三、核心问题诊断

### 🔴 P-Critical: Excel 表头行被当作数据

```python
# hero 表第 0 列 "键值" 的 sample_values:
['id', 'int', 1, 2, 3]
#  ^      ^
#  字段英文名  类型标记    ← 这两行不是数据！
```

**原因**: 游戏配置 Excel 通常前 1-3 行是**字段英文名、类型定义、注释**，不是真实数据。当前 ExcelReader 把所有行都当数据读入。

**影响**:
- `'id'`, `'int'`, `'string'`, `'float'` 等元数据值被当作采样值
- 关系发现时 `'int'` 与 `'int'` 的匹配造成大量假阳性
- evidence 里出现 `shared(8): 2,6,3,4,int` — `int` 是类型标记被错误纳入
- **这是当前 37.5% 低置信度关系噪声的主要来源**

**修复方案**: 检测并跳过表头行 — 如果前 N 行的值全是 `(string/int/float/bool/...)` 或全是英文字段名，视为元数据行跳过。

### 🔴 P-Critical: 命名约定策略完全失效

```python
# hero 表有 4 个以 "ID" 结尾的列:
英雄主动技能ID    # → 应该关联 skill 表
英雄被动技能ID    # → 应该关联 skill 表
英雄觉醒技能ID    # → 应该关联 skill 表
英雄专属雕像物品ID # → 应该关联 item 表
```

**但 naming_convention 发现了 0 条关系。** 原因：

```python
# 当前逻辑: 去掉后缀 "id" → 前缀 "英雄主动技能" → 在表名中匹配
# 表名: hero, skill, item（全英文）
# "英雄主动技能" ≠ 任何表名 → 匹配失败
```

**修复方案**: 需要**中文列名 → 英文表名的语义桥接**：
1. 列描述行（row 0）可能有英文名 `hero_activeSkill` — 利用它
2. 扩展 game_dictionary 增加中文→英文映射（技能→skill, 物品→item）
3. 子串匹配：列名含"技能" → 匹配包含 `skill` 的表

### 🟡 P-High: 小整数碰撞导致大量虚假关系

hero 表 `键值` 范围 1-15，与几乎所有含小整数的列产生包含匹配：

```
hero.键值 → activity.活动参数      (conf=0.83)  ← 巧合，不是真 FK
hero.键值 → vip.编号              (conf=0.76)  ← 巧合
hero.键值 → unlock.主键           (conf=0.67)  ← 巧合
hero.键值 → baseLevel.ID          (conf=0.65)  ← 巧合
```

34 条 hero outgoing 中，真正有意义的 FK 约 5-8 条，其余是数值巧合。

**现有惩罚** (`_is_small_int_range` + `_is_generic_name`) 不够 — 当一方是 PK 列时需要额外宽松检查，但当双方都是小值域 PK 时（hero 19行 vs 某表 30 行），仍会产生高置信度匹配。

### 🟡 P-High: 被引用方向噪声

hero 有 **59 条 incoming 关系**，大量是无意义的反向匹配：

```
← science.显示层级【只需配置第1级】 → 键值 (conf=0.91)  ← 显示层级恰好是 1-15
← hud_config_bookmark_config.关键值 → 键值 (conf=0.92)  ← 小值域碰撞
```

---

## 四、"英雄怎么配置的" — 当前能力评估

### 4.1 召回链路模拟

用 `--query hero` 命令模拟，当前系统返回：

| 表                               | domain  | 关系数    | 判定           |
| -------------------------------- | ------- | --------- | -------------- |
| hero                             | hero    | 34出+59入 | ✅ 核心表命中   |
| hero_hero_level                  | hero    | 1关系     | ✅ 等级子表     |
| hero_hero_star                   | hero    | 1关系     | ✅ 星级子表     |
| hero_hero_offices                | hero    | 1关系     | ✅ 官职子表     |
| monsterTroop_monsterHero         | monster | 关联hero  | ✅ 怪物英雄引用 |
| instanceTroop_instancePlayerHero | quest   | 关联hero  | ✅ 副本英雄引用 |
| pve_hero_heroSkin                | hero    | 无关系    | ⚠️ 只靠表名命中 |

**结论: 种子表召回 ✅ 完整**（7/7 hero 相关表全部命中）

### 4.2 关系链路质量

| 关系                                | 置信度 | 真实性                             |
| ----------------------------------- | ------ | ---------------------------------- |
| hero.英雄主动技能ID → skill.键值    | 0.89   | ✅ 真 FK                            |
| hero.英雄专属雕像物品ID → item.编号 | 0.72   | ✅ 真 FK                            |
| hero.键值 → hero_hero_star.键值     | 0.75   | ✅ 真 FK                            |
| hero.英雄主动技能ID → buff.键值     | 0.84   | ⚠️ 可能正确（技能ID范围与buff重叠） |
| hero.键值 → activity.活动参数       | 0.83   | ❌ 假阳性（小整数碰撞）             |
| hero.键值 → vip.编号                | 0.76   | ❌ 假阳性                           |
| hero.键值 → unlock.主键             | 0.67   | ❌ 假阳性                           |

**hero 的 34 条 outgoing 关系中，真正有效的 FK 约 5-8 条，噪声约 70%**。

### 4.3 能否生成正确的 LLM 回答？

**当前 LLM chunk 导出效果**（摘自真实 `data/llm_chunks.md`）：

```
## 表: hero [hero]
- 文件: hero.xlsx | sheet: hero
- 行数: 19 | 列数: 39 | 主键: 键值
- 列: 键值(float), #策划备注(str), 英雄名字(str), ... 英雄主动技能ID(float)→skill.键值, ...
- 关联: → skill(英雄主动技能ID→键值 @0.89), → buff(英雄主动技能ID→键值 @0.84),
         → activity(键值→活动参数 @0.83), ... [共 93 条关联]
```

**问题**: 
1. 93 条关联灌入 prompt = **约 3000 tokens 仅一张表** — 远超 300 token/表的设计目标
2. 70% 是噪声关联 → LLM 会被噪声关系误导
3. sample_values 含元数据行 `['id', 'int', 1, 2, 3]` → LLM 可能误读
4. 枚举值缺失（英雄品质 `[2,3,4,5]` 未解读为绿/蓝/紫/橙）

**结论: 当前直接作为 LLM 问答依据，回答会包含大量错误关联**。

---

## 五、能力矩阵 — 做到了什么/还差什么

### ✅ 已完成且可用

| 能力                | 状态 | 说明                                      |
| ------------------- | ---- | ----------------------------------------- |
| 多格式读取          | ✅    | xlsx/xls/csv，多 sheet，编码检测          |
| 增量构建            | ✅    | mtime+hash 变更检测，秒级增量             |
| 包含度 FK 发现      | ✅    | 倒排索引 + 值标准化，0.2s 发现 4500+ 关系 |
| 关系去重 + 表对限流 | ✅    | 方向无关去重 + top-3 per pair             |
| 结构化日志          | ✅    | 控制台 + 文件双输出                       |
| 业务域标签          | ✅    | 206/206 表分 12 个域                      |
| 证据字段            | ✅    | 3833/3833 关系有 evidence                 |
| LLM chunk 导出      | ✅    | `--export-llm` 输出 .md 或 .jsonl         |
| 命令行查询          | ✅    | `--query hero` 快速查看表结构+关系        |
| HTML 3D 可视化      | ✅    | 交互式力导向图                            |
| 反馈机制            | ✅    | confirm/reject 持久化，重建时自动应用     |
| 冒烟测试            | ✅    | 6 个基础测试覆盖核心模块                  |

### ❌ 关键缺失

| 缺失项                    | 对 RAG 的影响                               | 优先级 |
| ------------------------- | ------------------------------------------- | ------ |
| **表头行检测**            | 元数据污染采样值→假阳性+证据脏              | 🔴 P0   |
| **中文列名→表名桥接**     | 命名约定 0 召回→最强 FK 信号丢失            | 🔴 P0   |
| **小整数 PK 碰撞压制**    | 37% 关系是噪声→LLM 被误导                   | 🔴 P0   |
| **chunk token 压缩**      | 93 条关系/表→prompt 爆炸                    | 🟡 P1   |
| **RAG 召回管线**          | 无意图解析→多路召回→排序→prompt             | 🟡 P1   |
| **语义搜索（embedding）** | 仅支持精确关键词匹配，无模糊语义召回        | 🟡 P1   |
| **枚举值语义标注**        | 品质 5 不知道是"橙色"                       | 🟢 P2   |
| **多轮 Agent 推理**       | 无法做链式追踪（改品质影响什么→接着问细节） | 🟢 P2   |

---

## 六、修复路线图

### Phase 1: 数据质量（让图谱可信）

#### 1.1 表头行检测与跳过

```python
def _detect_header_rows(self, df: pd.DataFrame) -> int:
    """
    检测游戏配置 Excel 的元数据表头行数。
    
    常见模式:
      row 0: 中文列名 (已被 pandas 读为 column header)
      row 1: 英文字段名 (hero_name, hero_quality, ...)
      row 2: 类型标记 (string, int, float, int[], ...)
      row 3+: 真实数据
    
    判定: 如果某行 >80% 的非空值落在 TYPE_KEYWORDS 中，视为类型行。
    """
    TYPE_KEYWORDS = {'int', 'float', 'string', 'str', 'bool', 'int[]', 
                     'float[]', 'string[]', 'json', 'long', 'double'}
    skip = 0
    for i in range(min(3, len(df))):
        row = df.iloc[i]
        non_null = [str(v).strip().lower() for v in row if pd.notna(v)]
        if not non_null:
            continue
        type_hits = sum(1 for v in non_null if v in TYPE_KEYWORDS)
        # 也检测是否全是英文标识符（camelCase / snake_case）
        ident_hits = sum(1 for v in non_null if re.match(r'^[a-zA-Z_]\w*$', v))
        if type_hits / len(non_null) > 0.7 or ident_hits / len(non_null) > 0.8:
            skip = i + 1
    return skip
```

**预期效果**: 消除 `'int'`, `'string'` 等污染值 → 假阳性减少 30%+

#### 1.2 中文列名→表名桥接

```python
# 扩展 game_dictionary 或新建 entity_table_map
CN_ENTITY_MAP = {
    '技能': 'skill',    '英雄': 'hero',     '物品': 'item',
    '道具': 'item',     '装备': 'equip',    '活动': 'activity',
    '怪物': 'monster',  '建筑': 'building', '兵种': 'army',
    '科技': 'science',  'buff': 'buff',     '武器': 'weapon',
}

def _extract_cn_reference(self, col_name: str, table_map: dict):
    """从中文列名中提取引用目标"""
    # "英雄主动技能ID" → 找"技能" → skill
    for cn, en_prefix in CN_ENTITY_MAP.items():
        if cn in col_name and col_name.endswith(('ID', 'Id', 'id', '编号')):
            return en_prefix  # → 去表名中匹配 skill*
```

**预期效果**: naming_convention 从 0 → 估计 20-50 条高质关系

#### 1.3 PK 碰撞压制增强

```python
# 当 from_column 是 PK 且值域 < 50 时，额外惩罚
if col_a['column'] == table_a_pk and col_a['unique_count'] < 50:
    penalty += 0.25  # PK 列引用别人→高度可疑（通常是别人引用 PK）
```

### Phase 2: 召回管线（让 LLM 能用）

```
用户提问 "英雄怎么配置的"
    │
    ▼
[意图解析] LLM 提取实体 + 意图
    │ entities=["英雄"], intent="schema_exploration"
    ▼
[多路召回]
    ├─ 表名匹配: hero, hero_hero_level, hero_hero_star, ...
    ├─ domain 匹配: domain_label == "hero" 的 7 张表
    ├─ 列名搜索: 含"英雄"的列 → 所在表
    └─ 关系遍历: confidence >= 0.7 的 1-2 跳邻居
    │
    ▼
[排序剪枝] 按 score 取 Top-10 表，每表只保留 conf>=0.7 的关系
    │
    ▼
[chunk 组装] 每表 ~300 token 紧凑格式
    │
    ▼
[LLM 生成] system prompt + context + 用户问题
```

### Phase 3: 高阶能力（让分析更深）

- **数值追踪**: 从 sample_values 提取区间/公式模式
- **变更影响分析**: 反向 BFS + 影响传播权重
- **配置校验**: FK 完整性检查 → 孤立值报告

---

## 七、结论

### 对"英雄怎么配置的"这个问题：

| 维度                      | 评价  | 能力                                          |
| ------------------------- | ----- | --------------------------------------------- |
| **找到相关表**            | ⭐⭐⭐⭐⭐ | 7/7 hero 相关表全部命中                       |
| **识别表间关系**          | ⭐⭐⭐   | 真 FK 被发现（skill/item/star），但噪声关系多 |
| **给 LLM 提供可用上下文** | ⭐⭐    | 关联太多/太脏，直接注入会误导 LLM             |
| **端到端问答**            | ⭐     | RAG 管线不存在，无法自动回答                  |

### 总体判断

> **图谱构建引擎已基本可用**，但有两个阻塞项让它还不能直接用于 LLM 问答：
> 1. **数据质量** — 表头行污染 + 小整数碰撞 → 37% 关系是噪声
> 2. **RAG 管线** — 从"图谱数据"到"LLM 能回答"之间缺少召回→排序→prompt 组装的完整链路
>
> 修复 Phase 1（约 3 个核心改动）后，图谱精度预计从当前 ~60% 提升到 ~85%，此时配合 Top-K 剪枝的 LLM chunk 就可以产生有价值的问答结果。
>
> **建议投入顺序**: 表头检测 → 中文桥接 → PK 碰撞压制 → 召回管线 → chunk 压缩
