# Excel Graph Builder

Excel 配置表关系图谱构建工具。自动扫描 Excel、发现表间关联、导出 RAG 数据资产。

## 目录结构

```
excel_data\              ← 根目录
  dist\                  ← 部署包
    indexer.exe
    configs\settings.yml
    install.bat
    uninstall.bat
    excel_graph_builder\
  excel\                 ← Excel 数据文件（已有）
  graph\                 ← 构建产出（自动生成）
```

## 部署

### Step 1：复制文件

将 `dist\` 目录整个拷贝到数据根目录下（与 Excel 文件夹同级）。

### Step 2：修改配置

用记事本打开 **`dist\configs\settings.yml`**：

```yaml
# 路径相对于 dist/ 目录（即 indexer.exe 所在目录）

# Excel 数据根目录（默认 = dist 的上级目录）
data_root: ..

# 构建产出目录（默认 = 上级目录下的 graph 文件夹）
graph_dir: ..\graph

# Windows 计划任务名称
task_name: ExcelGraphBuilder

# 每天自动执行时间（24h 格式）
schedule_time: 02:00
```

**通常只需关注 `schedule_time`**，其他默认值在目录结构正确时无需修改。

常见修改场景：

| 场景 | 修改项 |
|------|--------|
| 改执行时间（如每天 06:00） | `schedule_time: 06:00` |
| Excel 目录不在上级 | `data_root: D:\other\path` |
| 产出想放到别的位置 | `graph_dir: D:\other\path\graph` |
| 同一台机器部署多个实例 | 改 `task_name` 避免冲突 |

### Step 3：安装

双击 `dist\install.bat`（会自动请求管理员权限）。

脚本自动执行：
1. 首次构建 → 产出写入根目录的 `graph\`
2. 注册 Windows 计划任务 → 之后每天自动构建

看到 `安装完成！` 即可关闭窗口。

### 卸载

双击 `dist\uninstall.bat`，删除计划任务。`graph\` 数据不受影响。

## 产出文件

构建完成后根目录的 `graph\` 包含以下文件，供 RAG 系统读取：

| 文件 | 说明 |
|------|------|
| `schema_summary.txt` | 表名摘要，注入 LLM prompt |
| `llm_chunks.jsonl` | 每表一行摘要，向量化召回 |
| `column_index.json` | 列名 → 表名倒排索引 |
| `relation_graph.json` | 邻接表 + JOIN 条件 |
| `join_paths.json` | 预计算表间 JOIN 路径 |
| `table_profiles.jsonl` | 每表富元数据 |
| `cell_locator.json` | 单元格定位索引 |
| `analysis.json` | 图算法分析结果 |
| `value_index.json` | 跨表值反查索引 |
| `domain_graph.json` | 域级关系图 |
| `enum_cross_ref.json` | 枚举值交叉索引 |

数据格式和 RAG 接入方法详见 [RAG_USAGE.md](RAG_USAGE.md)。

## 日常运维

```bash
# 手动触发一次构建（在 dist\ 目录下执行，无需管理员）
indexer.exe --config configs\settings.yml --run-now

# 通过系统命令触发计划任务
schtasks /Run /TN "ExcelGraphBuilder"

# 查看计划任务状态
schtasks /Query /TN "ExcelGraphBuilder"
```

## 常见问题

**Q: install.bat 弹出 UAC 提示框？**
A: 正常现象，注册计划任务需要管理员权限，点"是"即可。

**Q: 换了 Excel 目录位置怎么办？**
A: 先运行 `uninstall.bat` 卸载旧任务，修改 `configs\settings.yml` 中的 `data_root`，再重新运行 `install.bat`。

**Q: 构建产出放在哪？**
A: 默认在 `dist\` 上级目录的 `graph\` 文件夹。可在 `configs\settings.yml` 中修改 `graph_dir`。

**Q: 如何确认定时任务在正常运行？**
A: 打开「任务计划程序」搜索 `ExcelGraphBuilder`，查看"上次运行时间"和"上次运行结果"。
