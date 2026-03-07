# 项目结构说明

重构后的分层架构：

```
excel-graph-builder/
├── main.py                 # 服务入口
├── schema_graph.py         # 数据模型（表、关系、图谱）
├── scheduler.py            # 定时调度
├── watcher.py              # 文件监控
├── __init__.py             # 包初始化
│
├── core/                   # 核心构建
│   ├── __init__.py
│   ├── config.py           # 配置集中管理
│   └── builder.py          # 构建流程编排
│
├── discovery/              # 关系发现（Phase 1-4）
│   ├── __init__.py
│   ├── base.py             # 发现策略基类
│   ├── containment.py      # Phase 1: 包含度检测
│   ├── abbreviation.py     # Phase 2: 缩写挖掘
│   ├── transitive.py       # Phase 3: 传递推断
│   └── feedback.py         # Phase 4: 反馈管理
│
├── analysis/               # 图分析
│   ├── __init__.py
│   └── analyzer.py         # 环检测、中心性、社区发现
│
├── report/                 # 报告生成
│   ├── __init__.py
│   └── html_generator.py   # HTML 可视化
│
└── storage/                # 持久化
    ├── __init__.py
    └── json_storage.py     # JSON 存储
```

## 使用方式

### 快速开始

```python
from core.builder import GraphBuilder
from core.config import BuildConfig

# 创建构建器
config = BuildConfig(data_root="./data")
builder = GraphBuilder(config)

# 构建图谱
graph = builder.build()

# 清理资源
builder.close()
```

### 增强已有图谱

```python
from core.builder import enhance_graph
from storage import JsonGraphStorage

# 加载已有图谱
storage = JsonGraphStorage("./data")
graph = storage.load()

# 增强（只执行关系发现）
enhanced = enhance_graph(graph)

# 保存
storage.save(enhanced)
```

### 人工反馈

```python
builder = GraphBuilder(config)
graph = builder.build()

# 确认/拒绝关系
builder.save_feedback(
    confirmed=[('hero', 'sid', 'skill', 'id')],
    rejected=[('table1', 'col', 'table2', 'col')]
)

builder.close()  # 自动保存反馈
```

## 特性

- **Phase 1**: 包含度检测（发现 sid -> skill 等混乱命名关系）
- **Phase 2**: 缩写自动挖掘（学习命名规律）
- **Phase 3**: 传递关系推断（A->B->C 则 A 关联 C）
- **Phase 4**: 反馈闭环（人工确认 + 持久化学习）

## 配置

```python
from core.config import BuildConfig

config = BuildConfig(
    data_root="./data",
    containment_threshold=0.85,    # 包含度阈值
    abbrev_confidence_threshold=0.8,  # 缩写置信度
    enable_perf_opt=True,           # 启用性能优化
    feedback_file="feedback.json"
)
```
