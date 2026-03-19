# Excel 配置表构建服务

用于自动扫描游戏策划 Excel、生成 RAG / 分析所需数据资产，并按日定时构建。

这份 README 面向**部署和日常运维**，不介绍 RAG 接入细节。  
RAG 接入方法见 [RAG_USAGE.md](RAG_USAGE.md)。

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
| `enum_cross_ref.json` | 枚举值交叉索引 |
| `data_health.json` | 数据质量报告 |
| `pack_array_candidates.json` | pack 弱信号候选 |
| `evidence_config.json` | 证据组装入口配置 |

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

**Q: 构建产出放在哪？**  
A: 默认在 `dist\` 上级目录的 `graph\` 文件夹。可在 `configs\settings.yml` 中修改 `graph_dir`。

**Q: 如何确认定时任务在正常运行？**  
A: 打开“任务计划程序”搜索 `ExcelGraphBuilder`，查看“上次运行时间”和“上次运行结果”。

**Q: 为什么 `builds\` 里有新版本，但 `current\` 没更新？**  
A: 说明这次构建可能命中了 `P0`，没有通过发布门槛。先看 `reports\` 和 `alerts.log`。

**Q: 构建后 dist 里没有 embedding 模型？**  
A: 构建时会自动拷贝 `configs\` 和 `models\`（若存在于项目根或上级目录）到 dist。确保 `settings.yml` 中 `embedding_cache_folder` 指向相对路径 `models` 或部署后的实际模型目录。
