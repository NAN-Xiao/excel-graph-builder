# Excel Graph Builder

游戏 Excel 配置表关系图谱构建工具。扫描 Excel 文件，自动发现表间关联关系，生成 3D 可视化报告。

## 项目结构

```
excel-graph-builder/
├── README.md               # 项目说明
├── requirements.txt        # Python 依赖
├── start.bat               # Windows 启动脚本
│
├── indexer/                 # 源码包
│   ├── __init__.py          # 包初始化 + SimpleLogger
│   ├── __main__.py          # python -m indexer 入口
│   ├── models.py            # 数据模型（TableSchema, RelationEdge, SchemaGraph）
│   ├── service.py           # IndexService 服务主类 + CLI
│   ├── scheduler.py         # 定时调度（daily / interval + 防抖）
│   ├── watcher.py           # 文件系统监控（watchdog）
│   │
│   ├── core/                # 核心构建
│   │   ├── config.py        # BuildConfig 配置集中管理
│   │   └── builder.py       # GraphBuilder 构建流程编排
│   │
│   ├── scanner/             # Excel 扫描
│   │   ├── directory_scanner.py  # 目录递归扫描（增量检测）
│   │   ├── excel_reader.py       # Excel/CSV 读取器
│   │   └── schema_extractor.py   # 表结构提取
│   │
│   ├── discovery/           # 关系发现
│   │   ├── base.py          # 发现策略基类
│   │   ├── containment.py   # Phase 1: 包含度检测
│   │   ├── abbreviation.py  # Phase 2: 缩写挖掘
│   │   ├── transitive.py    # Phase 3: 传递推断
│   │   ├── feedback.py      # Phase 4: 反馈管理
│   │   ├── naming_convention.py  # Phase 5: 命名约定
│   │   └── game_dictionary.py    # 游戏领域词典
│   │
│   ├── analysis/            # 图分析
│   │   └── analyzer.py      # 环检测、中心性、社区发现
│   │
│   ├── report/              # 报告生成
│   │   └── html_generator.py # 3D 力导向图可视化
│   │
│   └── storage/             # 持久化
│       └── json_storage.py  # JSON 原子读写 + 文件锁
│
└── graph/                   # 输出: 图谱数据 + HTML 报告（默认输出到 <data-root>/graph/）
```

## 快速开始

```bash
# 1. 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 一次性构建（产出到 path/to/excel/graph/）
python -m indexer --data-root "path/to/excel" --run-now

# 4. 守护进程模式（定时构建 + 文件监控）
python -m indexer --data-root "path/to/excel" --daemon --schedule daily:02:00

# 产出目录默认为 <data-root>/graph/，可通过 --storage-dir 自定义
```

## API 使用

```python
from indexer.core.builder import GraphBuilder
from indexer.core.config import BuildConfig

# 创建构建器（产出到 <data_root>/graph/）
config = BuildConfig(data_root="path/to/excel")
builder = GraphBuilder(config)

# 构建图谱
graph, result = builder.build_full_graph()

# 清理资源
builder.close()
```

### 增强已有图谱

```python
from indexer.storage import JsonGraphStorage

# 加载已有图谱
storage = JsonGraphStorage("path/to/excel/graph")
graph = storage.load()

# 增强（只执行关系发现）
from indexer.core.builder import GraphBuilder
builder = GraphBuilder(BuildConfig(data_root="path/to/excel"))
enhanced, result = builder.build_full_graph(existing_graph=graph, incremental=True)

# 保存
storage.save(enhanced)
```

## 特性

- **Phase 1**: 包含度检测（发现 sid → skill 等混乱命名关系）
- **Phase 2**: 缩写自动挖掘（学习命名规律）
- **Phase 3**: 传递关系推断（A→B→C 则 A 关联 C）
- **Phase 4**: 反馈闭环（人工确认 + 持久化学习）
- **Phase 5**: 命名约定发现（hero_id → hero 表）

## 配置

```python
from indexer.core.config import BuildConfig

config = BuildConfig(
    data_root="path/to/excel",
    containment_threshold=0.85,    # 包含度阈值
    abbrev_confidence_threshold=0.8,  # 缩写置信度
    enable_perf_opt=True,           # 启用性能优化
    feedback_file="feedback.json"
)
```
