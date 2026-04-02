# Excel 配置表构建服务

用于自动扫描游戏策划 Excel、生成 RAG / 分析所需数据资产，并按日定时构建。

这份 README 面向**部署和日常运维**，不介绍 RAG 接入细节。  
RAG 接入方法见 [RAG_USAGE.md](RAG_USAGE.md)。

如果你是下游问答 / RAG 系统接入方，建议优先关注：

- 始终读取 `graph\current\`
- 首轮问答使用 `EvidenceAssembler` 的摘要证据
- 若证据不足，再根据 `hidden_but_available` / `fetch_hints` 继续展开

也就是说，推荐接法不是“单次把完整大表塞给 LLM”，而是：

1. 先给模型受控摘要
2. 再按需回源补取完整行、完整分组、完整 schema 或完整 JOIN 路径

这样可以同时保证：

- 底层数据完整保留
- 首轮 prompt 不会因为宽表 / 大表失控
- `LiBao` 这类大表仍可做全量统计分析

边界说明：

- 本工程只负责**离线构建数据资产**（文件产物）。
- 本工程**不提供在线接口**（不提供 HTTP/RPC/SDK query API）。

## 目录结构

```text
excel_data\              ← 根目录
  dist\                  ← 部署包
    indexer.exe
    configs\settings.yml
    install.bat
    uninstall.bat
    excel_graph_builder\
  excel\                 ← Excel 数据文件（已有，构建和分析仍需要）
  graph\                 ← 构建产物（自动生成）
    current\             ← 当前已发布版本（RAG 应读取这里）
    latest_success\      ← 最近一次成功版本
    builds\              ← 每次构建的独立版本目录
    reports\             ← 每次构建的回归报表
    regression_queries.json  ← 默认回归样例
    alerts.log           ← 本地告警摘要
```

## 部署

### Step 1：复制文件

将 `dist\` 目录整个拷贝到数据根目录下，与 `excel\` 同级。

### Step 2：修改配置

用记事本打开 **`dist\configs\settings.yml`**：

```yaml
# Excel 数据根目录（默认 = dist 的上级目录）
data_root: ..

# 构建产出目录
graph_dir: ..\graph

# Windows 计划任务名称
task_name: ExcelGraphBuilder

# 每天自动执行时间（24h 格式）
schedule_time: 02:00
```

通常只需要关注：

| 场景 | 修改项 |
|------|--------|
| 改执行时间（如每天 06:00） | `schedule_time: 06:00` |
| Excel 目录不在上级 | `data_root: D:\other\path` |
| 产出想放到别的位置 | `graph_dir: D:\other\path\graph` |
| 同一台机器部署多个实例 | 改 `task_name` 避免冲突 |
| 启用 embedding 预构建 | `embedding_enabled: true`，填 `embedding_python`，`embedding_cache_folder` 指向 dist\models（构建时会拷贝） |

### Step 3：安装

双击 `dist\install.bat`（会自动请求管理员权限）。

脚本会自动执行：

1. 首次构建
2. 注册 Windows 计划任务
3. 之后每天按 `schedule_time` 自动构建

看到 `安装完成！` 即可关闭窗口。

### 卸载

双击 `dist\uninstall.bat`，删除计划任务。  
`graph\` 目录中的历史产物不会自动删除。

## 构建结果怎么看

构建成功后，`graph\` 目录里最重要的是这些位置：

| 路径 | 含义 | 运维建议 |
|------|------|----------|
| `graph\current\` | 当前已发布版本 | 在线系统应读取这里 |
| `graph\latest_success\` | 最近一次成功版本 | 出问题时用于回退/对账 |
| `graph\builds\<build_id>\` | 单次构建目录 | 排查单次构建问题 |
| `graph\reports\<build_id>.md` | 人可读回归报表 | 先看这个 |
| `graph\reports\<build_id>.json` | 机器可读回归报表 | 监控/自动化读取 |
| `graph\alerts.log` | 告警摘要 | 出现异常时查看 |

## 产出文件

每个已发布版本目录中会包含以下主要资产：

| 文件 | 说明 |
|------|------|
| `schema_summary.txt` | 表名摘要 |
| `llm_chunks.jsonl` | 向量化召回文本 |
| `column_index.json` | 列名 → 表名倒排索引 |
| `relation_graph.json` | 邻接表 + JOIN 条件 |
| `join_paths.json` | 预计算 1~2 跳 JOIN 路径 |
| `table_profiles.jsonl` | 每表富元数据 |
| `cell_locator.json` | 单元格定位索引 |
| `analysis.json` | 图分析结果 |
| `value_index.json` | 跨表值反查索引 |
| `domain_graph.json` | 域级关系图 |
| `rag_preview.json` | 供静态前端 / RAG 调试使用的轻量预览资产 |
| `enum_cross_ref.json` | 枚举值交叉索引 |
| `data_health.json` | 数据质量报告 |
| `pack_array_candidates.json` | pack 弱信号候选 |
| `evidence_config.json` | 证据组装入口配置 |

其中对下游 RAG 最重要的是：

- `table_profiles.jsonl`
- `relation_graph.json`
- `join_paths.json`
- `evidence_config.json`

推荐把 `evidence_config.json` 作为下游初始化入口：

- 用 `assembler_init` 直接实例化 `EvidenceAssembler`
- 不要自己硬编码 `profiles_path / join_paths_path / data_root`
- 在线系统优先读取 `graph\current\evidence_config.json`

如果要做大表分布分析，还应结合：

- `analysis.json`
- 原始 `excel\` 数据目录（供回源全量统计与行级取数）

## 发布与回退机制

当前版本不是“构建完直接覆盖”。

流程是：

1. 先写入 `graph\builds\<build_id>\`
2. 自动执行完整性检查和回归
3. 通过后才同步到 `graph\current\`
4. 如果出现 `P0`，继续保留上一版 `graph\current\`

这意味着：

- 构建失败时，线上不会自动切到坏版本
- `graph\latest_success\` 可作为最近一次成功快照

### 增量构建和时间戳目录的关系

这里很容易误解，单独说明一下：

- `增量构建` 指的是计算策略
- `graph\builds\<build_id>\` 指的是产物落盘方式

也就是说，即使是增量构建，系统也仍然会先生成一个新的时间戳目录，例如：

- `graph\builds\2026-04-02-115815\`

增量体现在：

- 扫描时只重读有变化的表
- 关系发现时只重算受影响表相关的关系

不变的是：

- 每次构建都会产出一个独立快照目录
- 只有校验通过后，才会把这次构建同步到 `graph\current\`

这样做的目的不是重复存数据，而是保证：

- 构建失败不会污染线上可读版本
- 可以保留单次构建快照，方便排查和回滚
- `current` 始终代表“当前可在线消费的稳定版本”

所以如果你看到：

- `builds\` 里有新的时间戳目录
- 同时本次又是“增量构建”

这是正常行为，不冲突。

## 日常运维

```bat
:: 开发模式：在项目根目录执行，需 Python 环境
python -m indexer --config configs\settings.yml --run-now

:: 部署模式：在 dist\ 目录下执行，无需管理员
indexer.exe --config configs\settings.yml --run-now

:: 通过系统命令触发计划任务
schtasks /Run /TN "ExcelGraphBuilder"

:: 查看计划任务状态
schtasks /Query /TN "ExcelGraphBuilder"
```

## 出错时先看哪里

建议按这个顺序看：

1. `graph\reports\<build_id>.md`
2. `graph\alerts.log`
3. `graph\builds\<build_id>\` 下的产物是否齐全
4. `graph\current\` 是否仍保持上一版

告警级别说明：

| 级别 | 含义 | 处理方式 |
|------|------|----------|
| `P0` | 阻断错误，当前构建不可用 | 不发布，继续沿用上一版 |
| `P1` | 高风险退化 | 已生成报表，建议人工复核 |
| `P2` | 提示性异常 | 记录到报表，通常不阻断发布 |

## 常见问题

**Q: install.bat 弹出 UAC 提示框？**  
A: 正常现象，注册计划任务需要管理员权限，点“是”即可。

**Q: 接入方还需要原始 Excel 吗？**  
A: 需要。当前系统除导出索引资产外，还支持按需回源读取 Excel 做行级取数和全量统计分析，所以 `excel\` 目录不能删。

**Q: 下游 RAG 应该一次性把完整数据给 LLM 吗？**  
A: 不建议。推荐做法是“摘要 + drill-down”两段式：首轮只给裁剪后的 schema / join / key_rows / stat_summary / 可见分析摘要；如果模型需要更多细节，再按 `fetch_hints` 继续拉取完整数据。

**Q: 构建产出放在哪？**  
A: 默认在 `dist\` 上级目录的 `graph\` 文件夹。可在 `configs\settings.yml` 中修改 `graph_dir`。

**Q: 如何确认定时任务在正常运行？**  
A: 打开“任务计划程序”搜索 `ExcelGraphBuilder`，查看“上次运行时间”和“上次运行结果”。

**Q: 为什么 `builds\` 里有新版本，但 `current\` 没更新？**  
A: 说明这次构建可能命中了 `P0`，没有通过发布门槛。先看 `reports\` 和 `alerts.log`。

**Q: 为什么明明是增量构建，`builds\` 下面还是会有时间戳目录？**  
A: 因为“增量”描述的是重读和重算范围，不是产物写盘方式。系统仍会先把这次结果写到 `graph\builds\<build_id>\`，通过校验后再同步到 `graph\current\`。线上接入方始终只应读取 `graph\current\`。

**Q: 构建后 dist 里没有 embedding 模型？**  
A: 构建时会自动拷贝 `configs\` 和 `models\`（若存在于项目根或上级目录）到 dist。确保 `settings.yml` 中 `embedding_cache_folder` 指向相对路径 `models` 或部署后的实际模型目录。
