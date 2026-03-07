#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HTML 可视化报告生成器 - Indexer 独立模块

生成静态 HTML 文件展示图谱关系，使用 vis.js 力导向图
支持离线模式（内联 vis.js）
"""

import json
import base64
import urllib.request
from pathlib import Path
from datetime import datetime
from typing import Optional

from indexer.schema_graph import SchemaGraph, RelationEdge
from indexer import SimpleLogger


# vis.js CDN URL 和版本
VIS_JS_URL = "https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"
VIS_JS_VERSION = "9.1.2"


class HTMLReportGenerator:
    """生成静态 HTML 可视化报告"""
    
    def __init__(self, output_dir: str = "./html", offline: bool = True):
        """
        Args:
            output_dir: HTML 输出目录
            offline: 是否使用离线模式（内联 vis.js）
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.offline = offline
        self.logger = SimpleLogger()
        
        # 离线模式下，确保 vis.js 已下载
        if offline:
            self._ensure_vis_js()
    
    def _ensure_vis_js(self) -> str:
        """
        确保 vis.js 文件已下载到本地
        
        Returns:
            vis.js 文件内容
        """
        vis_js_path = self.output_dir / "vis-network.min.js"
        
        if vis_js_path.exists():
            with open(vis_js_path, 'r', encoding='utf-8') as f:
                return f.read()
        
        # 尝试下载
        try:
            self.logger.info(f"正在下载 vis.js ({VIS_JS_VERSION})...")
            with urllib.request.urlopen(VIS_JS_URL, timeout=30) as response:
                vis_js_content = response.read().decode('utf-8')
            
            # 保存到本地
            with open(vis_js_path, 'w', encoding='utf-8') as f:
                f.write(vis_js_content)
            
            self.logger.success(f"vis.js 已下载到: {vis_js_path}")
            return vis_js_content
        except Exception as e:
            self.logger.warning(f"下载 vis.js 失败: {e}")
            self.logger.warning("HTML 报告将使用 CDN 模式（需要联网查看）")
            return ""
    
    def generate(self, graph: SchemaGraph, build_result: Optional[dict] = None) -> str:
        """
        生成 HTML 报告
        
        Args:
            graph: 图谱数据
            build_result: 构建结果统计（可选）
        
        Returns:
            生成的 HTML 文件路径
        """
        # 准备数据
        nodes_data = []
        edges_data = []
        
        # 节点：表
        for name, table in graph.tables.items():
            col_count = len(table.columns)
            row_count = table.row_count
            
            # 节点大小根据行数动态调整
            size = min(30, max(15, row_count / 100)) if row_count else 20
            
            # 标题：显示表名和列数
            title = f"表: {name}\\n列数: {col_count}\\n行数: {row_count}"
            if table.primary_key:
                title += f"\\n主键: {table.primary_key}"
            
            # 列详情
            if table.columns:
                title += "\\n\\n列:"
                for col in table.columns[:10]:  # 最多显示10列
                    title += f"\\n  • {col['name']} ({col['dtype']})"
                if len(table.columns) > 10:
                    title += f"\\n  ... 还有 {len(table.columns)-10} 列"
            
            nodes_data.append({
                "id": name,
                "label": name,
                "title": title,
                "value": size,
                "group": self._get_group(table)
            })
        
        # 边：关系
        for rel in graph.relations:
            edges_data.append({
                "from": rel.from_table,
                "to": rel.to_table,
                "label": f"{rel.from_column} → {rel.to_column}",
                "title": f"{rel.from_column} → {rel.to_column}\\n类型: {rel.relation_type}\\n置信度: {rel.confidence}",
                "arrows": "to",
                "color": {"color": "#848484", "highlight": "#2B7CE9"}
            })
        
        # 构建统计
        stats = {
            "table_count": len(graph.tables),
            "relation_count": len(graph.relations),
            "build_time": graph.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
            "version": graph.version
        }
        if build_result:
            stats.update(build_result)
        
        # 生成 HTML
        html_content = self._generate_html(nodes_data, edges_data, stats)
        
        # 写入文件
        output_file = self.output_dir / "schema_graph.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        self.logger.success(f"HTML 报告已生成: {output_file}")
        if not self.offline:
            self.logger.info("提示: 报告使用 CDN 模式，需要联网才能查看可视化")
        return str(output_file)
    
    def _get_group(self, table) -> str:
        """根据表特征分组（影响颜色）"""
        name_lower = table.name.lower()
        if any(kw in name_lower for kw in ['config', 'setting', 'param']):
            return "config"
        elif any(kw in name_lower for kw in ['user', 'account', 'player', 'usr', 'cust', 'customer']):
            return "user"
        elif any(kw in name_lower for kw in ['item', 'goods', 'product', 'sku', 'merchandise']):
            return "item"
        elif any(kw in name_lower for kw in ['log', 'record', 'history', 'trace']):
            return "log"
        else:
            return "default"
    
    def _generate_html(self, nodes: list, edges: list, stats: dict) -> str:
        """生成完整的 HTML 内容"""
        
        nodes_json = json.dumps(nodes, ensure_ascii=False)
        edges_json = json.dumps(edges, ensure_ascii=False)
        
        # 确定 vis.js 的加载方式
        if self.offline:
            vis_js_content = self._ensure_vis_js()
            if vis_js_content:
                # 内联模式
                vis_js_script = f"<script type=\"text/javascript\">{vis_js_content}</script>"
            else:
                # 回退到 CDN
                vis_js_script = f'<script type="text/javascript" src="{VIS_JS_URL}"></script>'
        else:
            # CDN 模式
            vis_js_script = f'<script type="text/javascript" src="{VIS_JS_URL}"></script>'
        
        # 构建额外统计信息 HTML
        extra_stats_parts = []
        if stats.get('added', -1) >= 0:
            extra_stats_parts.append(f'<span>✨ 新增: <strong>{stats["added"]}</strong></span>')
        if stats.get('updated', -1) >= 0:
            extra_stats_parts.append(f'<span>📝 更新: <strong>{stats["updated"]}</strong></span>')
        if stats.get('deleted', -1) >= 0:
            extra_stats_parts.append(f'<span>🗑️ 删除: <strong>{stats["deleted"]}</strong></span>')
        extra_stats = '\n            '.join(extra_stats_parts)
        
        html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Schema Graph - 配置表图谱可视化</title>
    {vis_js_script}
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #f5f7fa;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 25px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header h1 {{
            font-size: 20px;
            font-weight: 500;
            margin-bottom: 5px;
        }}
        .header .stats {{
            font-size: 13px;
            opacity: 0.9;
        }}
        .header .stats span {{
            margin-right: 20px;
        }}
        .main {{
            flex: 1;
            display: flex;
            overflow: hidden;
        }}
        #graph-container {{
            flex: 1;
            background: white;
            position: relative;
        }}
        .sidebar {{
            width: 280px;
            background: white;
            border-left: 1px solid #e8e8e8;
            padding: 20px;
            overflow-y: auto;
        }}
        .sidebar h3 {{
            font-size: 14px;
            color: #333;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            margin-bottom: 10px;
            font-size: 13px;
            color: #555;
        }}
        .legend-color {{
            width: 16px;
            height: 16px;
            border-radius: 50%;
            margin-right: 10px;
        }}
        .controls {{
            margin-top: 25px;
            padding-top: 20px;
            border-top: 1px solid #e8e8e8;
        }}
        .controls h3 {{
            margin-bottom: 15px;
        }}
        .btn {{
            display: block;
            width: 100%;
            padding: 10px;
            margin-bottom: 10px;
            border: none;
            border-radius: 4px;
            background: #667eea;
            color: white;
            font-size: 13px;
            cursor: pointer;
            transition: background 0.2s;
        }}
        .btn:hover {{
            background: #5a6fd6;
        }}
        .btn.secondary {{
            background: #f0f0f0;
            color: #555;
        }}
        .btn.secondary:hover {{
            background: #e0e0e0;
        }}
        .info {{
            margin-top: 20px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 4px;
            font-size: 12px;
            color: #666;
            line-height: 1.6;
        }}
        .info p {{
            margin-bottom: 5px;
        }}
        .loading {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 16px;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔍 Schema Graph Visualization</h1>
        <div class="stats">
            <span>📊 表数量: <strong>{stats.get('table_count', 0)}</strong></span>
            <span>🔗 关系数量: <strong>{stats.get('relation_count', 0)}</strong></span>
            <span>🕐 构建时间: <strong>{stats.get('build_time', 'N/A')}</strong></span>
            {extra_stats}
        </div>
    </div>
    
    <div class="main">
        <div id="graph-container">
            <div class="loading">正在加载图谱...</div>
        </div>
        
        <div class="sidebar">
            <h3>📌 图例说明</h3>
            <div class="legend-item">
                <div class="legend-color" style="background: #97C2FC;"></div>
                <span>默认表</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: #FB7E81;"></div>
                <span>配置表 (config/setting)</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: #7BE141;"></div>
                <span>用户表 (user/account/cust)</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: #FFFF00;"></div>
                <span>物品表 (item/goods/sku)</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: #6E6EFD;"></div>
                <span>日志表 (log/record)</span>
            </div>
            
            <div class="controls">
                <h3>🎮 控制面板</h3>
                <button class="btn" onclick="fitGraph()">适应窗口大小</button>
                <button class="btn secondary" onclick="togglePhysics()">开启/关闭 物理模拟</button>
                <button class="btn secondary" onclick="resetLayout()">重置布局</button>
            </div>
            
            <div class="info">
                <p><strong>💡 操作提示：</strong></p>
                <p>• 滚轮缩放图谱</p>
                <p>• 拖拽移动节点</p>
                <p>• 悬停查看详情</p>
                <p>• 双击聚焦节点</p>
                <p>• 选中高亮关联</p>
            </div>
        </div>
    </div>

    <script type="text/javascript">
        // 等待 vis.js 加载完成
        function initGraph() {{
            if (typeof vis === 'undefined') {{
                setTimeout(initGraph, 100);
                return;
            }}
            
            // 移除 loading
            document.querySelector('.loading').style.display = 'none';
            
            // 图谱数据
            const nodesData = {nodes_json};
            const edgesData = {edges_json};
            
            // 创建数据集
            const nodes = new vis.DataSet(nodesData);
            const edges = new vis.DataSet(edgesData);
            
            // 配置选项
            const options = {{
                nodes: {{
                    shape: 'dot',
                    scaling: {{
                        min: 15,
                        max: 40,
                        label: {{
                            enabled: true,
                            min: 14,
                            max: 24,
                            maxVisible: 30,
                            drawThreshold: 5
                        }}
                    }},
                    font: {{
                        size: 14,
                        face: 'Arial'
                    }},
                    borderWidth: 2,
                    shadow: true
                }},
                edges: {{
                    width: 2,
                    smooth: {{
                        type: 'continuous',
                        roundness: 0.2
                    }},
                    font: {{
                        size: 11,
                        align: 'middle',
                        background: 'white'
                    }},
                    arrows: {{
                        to: {{ enabled: true, scaleFactor: 0.8 }}
                    }}
                }},
                groups: {{
                    default: {{ color: {{ background: '#97C2FC', border: '#2B7CE9' }} }},
                    config: {{ color: {{ background: '#FB7E81', border: '#FA0A10' }} }},
                    user: {{ color: {{ background: '#7BE141', border: '#4AD63A' }} }},
                    item: {{ color: {{ background: '#FFFF00', border: '#FFA500' }} }},
                    log: {{ color: {{ background: '#6E6EFD', border: '#0000FF' }} }}
                }},
                physics: {{
                    enabled: true,
                    barnesHut: {{
                        gravitationalConstant: -2000,
                        centralGravity: 0.3,
                        springLength: 150,
                        springConstant: 0.04,
                        damping: 0.09,
                        avoidOverlap: 0.5
                    }},
                    stabilization: {{
                        enabled: true,
                        iterations: 1000,
                        updateInterval: 50
                    }}
                }},
                interaction: {{
                    hover: true,
                    tooltipDelay: 200,
                    hideEdgesOnDrag: true,
                    navigationButtons: true,
                    keyboard: true
                }},
                layout: {{
                    randomSeed: 2
                }}
            }};
            
            // 初始化网络图
            const container = document.getElementById('graph-container');
            const data = {{ nodes: nodes, edges: edges }};
            window.network = new vis.Network(container, data, options);
            
            // 物理模拟开关
            let physicsEnabled = true;
            window.togglePhysics = function() {{
                physicsEnabled = !physicsEnabled;
                window.network.setOptions({{ physics: {{ enabled: physicsEnabled }} }});
            }};
            
            // 适应窗口
            window.fitGraph = function() {{
                window.network.fit({{ animation: {{ duration: 500, easingFunction: 'easeInOutQuad' }} }});
            }};
            
            // 重置布局
            window.resetLayout = function() {{
                window.network.setData({{ nodes: nodes, edges: edges }});
                setTimeout(window.fitGraph, 100);
            }};
            
            // 窗口大小改变时适应
            window.addEventListener('resize', () => {{
                window.network.redraw();
            }});
            
            // 双击节点聚焦
            window.network.on("doubleClick", function (params) {{
                if (params.nodes.length > 0) {{
                    const nodeId = params.nodes[0];
                    window.network.focus(nodeId, {{
                        scale: 1.2,
                        animation: {{ duration: 500, easingFunction: 'easeInOutQuad' }}
                    }});
                }}
            }});
            
            // 初始化完成后适应窗口
            window.network.once("stabilizationIterationsDone", function() {{
                window.fitGraph();
            }});
        }}
        
        // 启动
        initGraph();
    </script>
</body>
</html>'''
        return html
