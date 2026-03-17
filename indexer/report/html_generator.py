#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HTML 可视化报告生成器

生成静态 HTML 文件展示图谱关系，使用 3d-force-graph 3D 力导向图
支持离线模式（内联 JS）
"""

import json
import urllib.request
from pathlib import Path
from typing import Optional

from indexer.models import SchemaGraph, RelationEdge
from indexer import SimpleLogger
from indexer.discovery.game_dictionary import classify_domain

# 3d-force-graph CDN URL
FORCE_GRAPH_JS_URL = "https://unpkg.com/3d-force-graph"


class HTMLReportGenerator:
    """生成静态 HTML 可视化报告"""

    def __init__(self, output_dir: str = "./html", offline: bool = True):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.offline = offline
        self.logger = SimpleLogger()
        if offline:
            self._ensure_force_graph_js()

    def _ensure_force_graph_js(self) -> dict:
        """确保 3d-force-graph JS 文件已下载到本地"""
        files = {"3d-force-graph.min.js": FORCE_GRAPH_JS_URL}
        result = {}
        for fname, url in files.items():
            fpath = self.output_dir / fname
            if fpath.exists():
                with open(fpath, 'r', encoding='utf-8') as f:
                    result[fname] = f.read()
                continue
            try:
                self.logger.info(f"正在下载 {fname}...")
                req = urllib.request.Request(
                    url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=30) as response:
                    content = response.read().decode('utf-8')
                with open(fpath, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.logger.success(f"{fname} 已下载到: {fpath}")
                result[fname] = content
            except Exception as e:
                self.logger.warning(f"下载 {fname} 失败: {e}")
                self.logger.warning("HTML 报告将使用 CDN 模式（需要联网查看）")
        return result

    def generate(self, graph: SchemaGraph, build_result: Optional[dict] = None,
                 analysis=None) -> str:
        """生成 HTML 报告

        Args:
            graph: 完整图谱
            build_result: 构建统计（added/updated/deleted）
            analysis: GraphAnalyzer 的 AnalysisResult（可选）
        """
        nodes_data = []
        edges_data = []

        # 计算节点度数（连接数）— 影响节点大小
        degree = {}
        for rel in graph.relations:
            degree[rel.from_table] = degree.get(rel.from_table, 0) + 1
            degree[rel.to_table] = degree.get(rel.to_table, 0) + 1

        for name, table in graph.tables.items():
            col_count = len(table.columns)
            row_count = table.row_count
            deg = degree.get(name, 0)
            size = max(2, min(8, 2 + (deg / 10)))

            title = f"表: {name}\\n列数: {col_count}\\n行数: {row_count}"
            if table.primary_key:
                title += f"\\n主键: {table.primary_key}"
            if table.columns:
                title += "\\n\\n列:"
                for col in table.columns[:10]:
                    title += f"\\n  • {col['name']} ({col['dtype']})"
                if len(table.columns) > 10:
                    title += f"\\n  ... 还有 {len(table.columns) - 10} 列"

            nodes_data.append({
                "id": name, "label": name, "title": title,
                "value": size, "group": self._get_group(table)
            })

        for rel in graph.relations:
            edges_data.append({
                "source": rel.from_table, "target": rel.to_table,
                "label": f"{rel.from_column} → {rel.to_column}",
                "relType": rel.relation_type, "confidence": rel.confidence,
            })

        stats = {
            "table_count": len(graph.tables),
            "relation_count": len(graph.relations),
            "build_time": graph.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
            "version": graph.version
        }
        if build_result:
            stats.update(build_result)

        tables_meta = {}
        for name, table in graph.tables.items():
            tables_meta[name] = {
                'columns': table.columns,
                'primary_key': table.primary_key,
                'row_count': table.row_count,
                'file_path': table.file_path,
                'enum_columns': {k: v[:20] for k, v in table.enum_columns.items()} if table.enum_columns else {},
                'numeric_columns': table.numeric_columns
            }

        # 构建分析数据（供前端展示）
        analysis_data = self._build_analysis_data(analysis)

        html_content = self._build_html(
            nodes_data, edges_data, stats, tables_meta, analysis_data)

        output_file = self.output_dir / "schema_graph.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        self.logger.success(f"HTML 报告已生成: {output_file}")
        return str(output_file)

    @staticmethod
    def _build_analysis_data(analysis) -> dict:
        """将 AnalysisResult 转换为前端可用的 JSON 数据"""
        if analysis is None:
            return {}
        return {
            'cycles': [list(c) for c in (analysis.cycles or [])[:20]],
            'centrality_top': sorted(
                analysis.centrality.items(),
                key=lambda x: x[1], reverse=True
            )[:15] if analysis.centrality else [],
            'modules': [
                sorted(list(m))[:20] for m in (analysis.modules or [])[:20]
            ],
            'orphans': sorted(analysis.orphans or [])[:50],
            'critical_path': list(analysis.critical_path or []),
        }

    def _get_group(self, table) -> str:
        """根据表名特征分组（影响节点颜色），使用统一业务域规则"""
        return classify_domain(table.name)

    def _build_html(self, nodes, edges, stats, tables_meta=None,
                     analysis_data=None):
        """生成完整 HTML"""
        nodes_json = json.dumps(nodes, ensure_ascii=False, default=str)
        edges_json = json.dumps(edges, ensure_ascii=False, default=str)
        tables_meta_json = json.dumps(tables_meta or {}, ensure_ascii=False, default=str)
        analysis_json = json.dumps(analysis_data or {}, ensure_ascii=False, default=str)
        total_edges = len(edges)

        if self.offline:
            fg_path = self.output_dir / "3d-force-graph.min.js"
            if fg_path.exists():
                with open(fg_path, 'r', encoding='utf-8') as f:
                    fg_content = f.read()
                fg_script = f'<script>{fg_content}</script>'
            else:
                fg_script = f'<script src="{FORCE_GRAPH_JS_URL}"></script>'
        else:
            fg_script = f'<script src="{FORCE_GRAPH_JS_URL}"></script>'

        extra_parts = []
        if stats.get('added', -1) >= 0:
            extra_parts.append(
                f'<span>新增 <strong>{stats["added"]}</strong></span>')
        if stats.get('updated', -1) >= 0:
            extra_parts.append(
                f'<span>更新 <strong>{stats["updated"]}</strong></span>')
        if stats.get('deleted', -1) >= 0:
            extra_parts.append(
                f'<span>删除 <strong>{stats["deleted"]}</strong></span>')
        extra_stats = ' '.join(extra_parts)

        return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Schema Graph 3D</title>
{fg_script}
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#080c24;height:100vh;display:flex;flex-direction:column;color:#e2e8f0}}
.hdr{{background:linear-gradient(135deg,#4f46e5,#7c3aed);color:#fff;padding:10px 22px;display:flex;align-items:center;justify-content:space-between;z-index:10;box-shadow:0 2px 12px rgba(0,0,0,.5)}}
.hdr h1{{font-size:17px;font-weight:600;letter-spacing:.5px}}
.hdr .st{{font-size:11px;opacity:.85;margin-top:2px}}
.hdr .st span{{margin-right:14px}}
.main{{flex:1;display:flex;overflow:hidden;position:relative}}
#graph-container{{flex:1;position:relative;overflow:hidden}}
#fps-hud{{position:absolute;top:10px;left:12px;z-index:5;font:11px/1 'Consolas',monospace;color:#4ade80;background:rgba(0,0,0,.55);padding:4px 8px;border-radius:4px;pointer-events:none}}
#edge-hud{{position:absolute;top:10px;right:392px;z-index:5;font:11px/1 'Consolas',monospace;color:#94a3b8;background:rgba(0,0,0,.55);padding:4px 8px;border-radius:4px;pointer-events:none}}
.sidebar{{width:370px;background:#111827;border-left:1px solid #1e293b;display:flex;flex-direction:column;overflow:hidden;z-index:10}}
.tab-bar{{display:flex;border-bottom:1px solid #1e293b;flex-shrink:0}}
.tab-btn{{flex:1;padding:10px 6px;border:none;background:#1f2937;font-size:12px;font-weight:500;cursor:pointer;color:#64748b;transition:all .2s;border-bottom:2px solid transparent}}
.tab-btn.active{{background:#111827;color:#818cf8;border-bottom-color:#818cf8}}
.tab-btn:hover:not(.active){{background:#1a2332}}
.tab-content{{flex:1;overflow-y:auto;padding:14px;display:none}}
.tab-content.active{{display:block}}
.tab-content::-webkit-scrollbar{{width:5px}}
.tab-content::-webkit-scrollbar-track{{background:#111827}}
.tab-content::-webkit-scrollbar-thumb{{background:#334155;border-radius:3px}}
.lgd{{display:flex;align-items:center;margin-bottom:5px;font-size:11px;color:#94a3b8}}
.lgd i{{width:10px;height:10px;border-radius:50%;margin-right:8px;flex-shrink:0;display:inline-block}}
.ctrl{{margin-top:14px;padding-top:12px;border-top:1px solid #1e293b}}
.ctrl h3{{font-size:12px;color:#cbd5e1;margin-bottom:8px}}
.btn{{display:block;width:100%;padding:7px;margin-bottom:5px;border:none;border-radius:4px;background:#4f46e5;color:#fff;font-size:12px;cursor:pointer;transition:background .2s}}
.btn:hover{{background:#4338ca}}
.btn.sec{{background:#1e293b;color:#94a3b8}}
.btn.sec:hover{{background:#334155}}
.conf-sec{{margin-top:12px;padding-top:12px;border-top:1px solid #1e293b}}
.conf-sec label{{font-size:11px;color:#94a3b8;display:flex;justify-content:space-between;margin-bottom:5px}}
.conf-sec label b{{color:#818cf8}}
.conf-slider{{width:100%;-webkit-appearance:none;height:4px;border-radius:2px;background:#1e293b;outline:none}}
.conf-slider::-webkit-slider-thumb{{-webkit-appearance:none;width:14px;height:14px;border-radius:50%;background:#818cf8;cursor:pointer}}
.conf-info{{font-size:10px;color:#475569;margin-top:5px}}
.tips{{margin-top:12px;padding:9px;background:#1a2332;border-radius:4px;font-size:10px;color:#475569;line-height:1.6}}
.tips b{{color:#64748b}}
.loading{{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);font-size:14px;color:#475569;z-index:5}}
.recall-search{{margin-bottom:14px}}
.recall-input{{width:100%;padding:8px 10px;border:1px solid #334155;border-radius:5px;font-size:13px;outline:none;background:#1a2332;color:#e5e7eb;transition:border .2s}}
.recall-input:focus{{border-color:#818cf8}}
.recall-input::placeholder{{color:#475569}}
.recall-opts{{display:flex;gap:6px;margin-top:6px}}
.recall-opts select{{flex:1;padding:5px 7px;border:1px solid #334155;border-radius:4px;font-size:11px;background:#1a2332;color:#94a3b8}}
.recall-btn{{padding:5px 14px;border:none;border-radius:4px;background:#4f46e5;color:#fff;font-size:12px;cursor:pointer}}
.recall-btn:hover{{background:#4338ca}}
.recall-summary{{padding:8px 10px;background:#1a2332;border-radius:5px;margin-bottom:10px;font-size:11px;color:#94a3b8;line-height:1.5;display:none}}
.recall-summary strong{{color:#818cf8}}
.recall-card{{background:#1a2332;border:1px solid #1e293b;border-radius:6px;padding:10px;margin-bottom:7px;cursor:pointer;transition:all .2s}}
.recall-card:hover{{border-color:#4f46e5}}
.recall-card.active{{border-color:#818cf8;background:#1e2d41}}
.recall-card-header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:4px}}
.recall-card-title{{font-size:12px;font-weight:600;color:#e5e7eb}}
.recall-card-badge{{padding:2px 7px;border-radius:10px;font-size:10px;font-weight:500}}
.badge-table{{background:#1e3a5f;color:#60a5fa}}
.badge-column{{background:#14532d;color:#4ade80}}
.badge-relation{{background:#4c1d2a;color:#f87171}}
.recall-card-meta{{font-size:10px;color:#475569;margin-bottom:4px}}
.recall-card-detail{{font-size:11px;color:#94a3b8;line-height:1.4}}
.recall-card-detail .match{{background:rgba(133,77,14,.25);padding:1px 3px;border-radius:2px;color:#fbbf24;font-weight:500}}
.recall-card-cols{{display:flex;flex-wrap:wrap;gap:3px;margin-top:4px}}
.col-tag{{padding:2px 6px;background:#1e293b;border-radius:3px;font-size:10px;color:#64748b}}
.col-tag.highlight{{background:rgba(133,77,14,.25);color:#fbbf24;font-weight:500}}
.rel-item{{font-size:10px;color:#818cf8;padding:1px 0}}
.rel-item .arrow{{color:#475569}}
.rel-link:hover{{background:#1e293b;border-radius:3px;padding-left:4px}}
.recall-score{{font-size:10px;color:#475569}}
.recall-empty{{text-align:center;padding:24px 10px;color:#475569;font-size:12px}}
.recall-feedback{{display:flex;gap:4px;margin-top:5px;justify-content:flex-end}}
.fb-btn{{padding:2px 8px;border:1px solid #334155;border-radius:3px;font-size:10px;cursor:pointer;background:transparent;color:#64748b;transition:all .15s}}
.fb-btn.good:hover,.fb-btn.good.selected{{background:#14532d;border-color:#22c55e;color:#4ade80}}
.fb-btn.bad:hover,.fb-btn.bad.selected{{background:#4c1d2a;border-color:#ef4444;color:#f87171}}
.recall-export{{margin-top:8px;padding-top:8px;border-top:1px solid #1e293b}}
#tab-analysis .recall-card{{cursor:pointer}}
.node-tooltip{{background:rgba(15,23,42,.95);color:#e2e8f0;padding:8px 12px;border-radius:6px;font-size:12px;line-height:1.5;max-width:300px;pointer-events:none;border:1px solid rgba(129,140,248,.3);backdrop-filter:blur(8px)}}
.node-tooltip strong{{color:#a5b4fc}}
#detail-content table{{width:100%;font-size:11px;border-collapse:collapse;margin-bottom:10px}}
#detail-content th{{text-align:left;padding:4px 6px;background:#1e293b;color:#94a3b8;font-weight:500}}
#detail-content td{{padding:4px 6px;border-bottom:1px solid #1e293b;color:#cbd5e1}}
.cam-bar{{position:absolute;top:10px;right:382px;z-index:200;display:flex;gap:4px;align-items:center;pointer-events:auto}}
.cam-btn{{width:32px;height:28px;border:1px solid #334155;border-radius:4px;background:rgba(17,24,39,0.85);color:#94a3b8;font-size:11px;font-weight:600;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:all .15s;backdrop-filter:blur(6px)}}
.cam-btn:hover{{background:#1e293b;color:#e2e8f0;border-color:#818cf8}}
.cam-btn.active{{background:#4f46e5;color:#fff;border-color:#4f46e5}}
.cam-sep{{width:1px;height:20px;background:#334155;margin:0 2px}}
</style>
</head>
<body>
<div class="hdr">
    <div>
        <h1>Schema Graph 3D</h1>
        <div class="st">
            <span>表 <strong>{stats.get('table_count', 0)}</strong></span>
            <span>关系 <strong>{stats.get('relation_count', 0)}</strong></span>
            <span>{stats.get('build_time', '')}</span>
            {extra_stats}
        </div>
    </div>
</div>
<div class="main">
    <div id="graph-container">
        <div id="fps-hud">-- FPS</div>
        <div id="edge-hud"></div>
        <div class="loading" id="loading-msg">加载中...</div>
    </div>
    <div class="cam-bar">
        <button class="cam-btn" onclick="setCamView('top')" title="俯视">T</button>
        <button class="cam-btn" onclick="setCamView('front')" title="正前">F</button>
        <button class="cam-btn" onclick="setCamView('back')" title="背面">B</button>
        <button class="cam-btn" onclick="setCamView('left')" title="左侧">L</button>
        <button class="cam-btn" onclick="setCamView('right')" title="右侧">R</button>
        <div class="cam-sep"></div>
        <button class="cam-btn" id="persp-btn" onclick="togglePersp()" title="透视/正交">P</button>
    </div>
    <div class="sidebar">
        <div class="tab-bar">
            <button class="tab-btn active" onclick="switchTab('legend')">图例</button>
            <button class="tab-btn" onclick="switchTab('analysis')">分析</button>
            <button class="tab-btn" onclick="switchTab('recall')">召回</button>
            <button class="tab-btn" onclick="switchTab('detail')">详情</button>
        </div>
        <div id="tab-legend" class="tab-content active">
            <div class="lgd"><i style="background:#ff6b6b"></i>英雄/角色</div>
            <div class="lgd"><i style="background:#feca57"></i>技能</div>
            <div class="lgd"><i style="background:#ff9ff3"></i>战斗</div>
            <div class="lgd"><i style="background:#55efc4"></i>物品/装备</div>
            <div class="lgd"><i style="background:#74b9ff"></i>建筑</div>
            <div class="lgd"><i style="background:#a29bfe"></i>任务</div>
            <div class="lgd"><i style="background:#00cec9"></i>联盟</div>
            <div class="lgd"><i style="background:#e17055"></i>怪物/NPC</div>
            <div class="lgd"><i style="background:#fdcb6e"></i>奖励</div>
            <div class="lgd"><i style="background:#81ecec"></i>地图/世界</div>
            <div class="lgd"><i style="background:#fd79a8"></i>社交</div>
            <div class="lgd"><i style="background:#636e72"></i>配置/系统</div>
            <div class="lgd"><i style="background:#b2bec3"></i>其他</div>
            <div style="margin-top:12px;padding-top:10px;border-top:1px solid #1e293b">
                <div style="font-size:11px;color:#64748b;margin-bottom:6px;font-weight:500">连线颜色 — 关系类型</div>
                <div class="lgd"><i style="background:rgb(96,165,250)"></i>命名约定</div>
                <div class="lgd"><i style="background:rgb(74,222,128)"></i>值包含</div>
                <div class="lgd"><i style="background:rgb(251,191,36)"></i>值重叠</div>
                <div class="lgd"><i style="background:rgb(251,146,36)"></i>缩写匹配</div>
                <div class="lgd"><i style="background:rgb(167,139,250)"></i>传递推断</div>
                <div class="lgd"><i style="background:rgb(148,163,184)"></i>其他</div>
            </div>
            <div class="ctrl">
                <h3>控制</h3>
                <button class="btn" onclick="resetCamera()">适应窗口</button>
                <button class="btn sec" id="dag-btn" onclick="toggleDagMode()">DAG 布局</button>
                <button class="btn sec" onclick="toggleLinks()">连线 开/关</button>
            </div>
            <div class="conf-sec">
                <label>置信度阈值 <b id="conf-val">0.70</b></label>
                <input type="range" class="conf-slider" min="0" max="1" step="0.05" value="0.70" oninput="updateConf(this.value)">
                <div class="conf-info">显示 <b id="vis-edges">--</b> / {total_edges} 条关系</div>
            </div>
            <div class="tips">
                <p><b>操作</b></p>
                <p>拖拽旋转 · 滚轮缩放 · 右键平移</p>
                <p>点击节点聚焦 · 背景点击重置</p>
            </div>
        </div>
        <div id="tab-analysis" class="tab-content">
            <div id="analysis-content" style="font-size:12px;line-height:1.6">
                <div style="color:#475569;text-align:center;padding:20px">分析数据加载中...</div>
            </div>
        </div>
        <div id="tab-recall" class="tab-content">
            <div class="recall-search">
                <input class="recall-input" id="recall-input" type="text"
                    placeholder="查询: hero, skill_id, reward..."
                    onkeydown="if(event.key==='Enter')doRecall()">
                <div class="recall-opts">
                    <select id="recall-type">
                        <option value="all">全部</option>
                        <option value="table">按表名</option>
                        <option value="column">按列名</option>
                        <option value="relation">按关系</option>
                        <option value="path">路径查找</option>
                    </select>
                    <select id="recall-confidence">
                        <option value="0">不限置信度</option>
                        <option value="0.5">≥ 0.5</option>
                        <option value="0.7" selected>≥ 0.7</option>
                        <option value="0.9">≥ 0.9</option>
                    </select>
                    <button class="recall-btn" onclick="doRecall()">召回</button>
                </div>
            </div>
            <div class="recall-summary" id="recall-summary"></div>
            <div class="recall-results" id="recall-results">
                <div class="recall-empty">输入关键词开始召回测试</div>
            </div>
            <div class="recall-export" id="recall-export" style="display:none">
                <button class="btn sec" onclick="exportRecallReport()">导出召回报告</button>
            </div>
        </div>
        <div id="tab-detail" class="tab-content">
            <div class="recall-empty" id="detail-placeholder">点击节点查看详情</div>
            <div id="detail-content" style="display:none"></div>
        </div>
    </div>
</div>
<script>
// ===== DATA =====
const nodesData = {nodes_json};
const edgesData = {edges_json};
const tablesMeta = {tables_meta_json};
const analysisData = {analysis_json};

const groupColors = {{
    hero:'#ff6b6b', skill:'#feca57', battle:'#ff9ff3',
    item:'#55efc4', building:'#74b9ff', quest:'#a29bfe',
    alliance:'#00cec9', monster:'#e17055', reward:'#fdcb6e',
    world:'#81ecec', social:'#fd79a8', config:'#636e72',
    other:'#b2bec3'
}};
// 关系类型颜色 (RGB for rgba)
const relRgb = {{
    fk_naming_convention:'96,165,250', fk_content_subset:'74,222,128',
    fk_content_overlap:'251,191,36', inferred_transitive:'167,139,250',
    fk_abbreviation_pattern:'251,146,36'
}};
const defRelRgb = '148,163,184';

// ===== STATE =====
let G = null;
let linksOn = true, dagMode = null, minConf = 0.7;
let hlNodes = new Set(), hlLinks = new Set();
let focusedNid = null;
let recallHistory = [];

// ===== TABS =====
function switchTab(t) {{
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    document.getElementById('tab-'+t).classList.add('active');
    document.querySelector('[onclick*="'+t+'"]').classList.add('active');
}}

// ===== FPS =====
let _fc = 0, _ft = performance.now();
function fpsLoop() {{
    _fc++;
    const now = performance.now();
    if (now - _ft >= 1000) {{
        const el = document.getElementById('fps-hud');
        if (el) el.textContent = _fc + ' FPS';
        _fc = 0; _ft = now;
    }}
    requestAnimationFrame(fpsLoop);
}}

// ===== INIT =====
let dagMinConf = 0.85; // DAG 模式用更高阈值保留核心边
function filteredGraphData() {{
    const effectiveConf = dagMode ? Math.max(minConf, dagMinConf) : minConf;
    let links = edgesData.filter(e => {{
        if (e.confidence >= effectiveConf) return true;
        if (focusedNid) {{
            const s = typeof e.source==='object'?e.source.id:e.source;
            const t = typeof e.target==='object'?e.target.id:e.target;
            if (s===focusedNid||t===focusedNid) return true;
        }}
        return false;
    }}).map(e => ({{ ...e }}));
    // DAG 模式去环
    if (dagMode) {{
        // 1) 双向边只保留置信度高的
        const pairBest = {{}};
        links.forEach(e => {{
            const s = typeof e.source==='object'?e.source.id:e.source;
            const t = typeof e.target==='object'?e.target.id:e.target;
            const key = [s,t].sort().join('|');
            if (!pairBest[key] || e.confidence > pairBest[key].confidence) pairBest[key] = e;
        }});
        links = Object.values(pairBest);
        // 2) DFS 移除回边破环
        const adj = {{}};
        links.forEach(e => {{
            const s = typeof e.source==='object'?e.source.id:e.source;
            if (!adj[s]) adj[s] = [];
            adj[s].push(e);
        }});
        const WHITE=0, GRAY=1, BLACK=2;
        const color = {{}};
        const backEdges = new Set();
        function dfs(u) {{
            color[u] = GRAY;
            for (const e of (adj[u]||[])) {{
                const v = typeof e.target==='object'?e.target.id:e.target;
                if (color[v] === GRAY) backEdges.add(e);
                else if (!color[v]) dfs(v);
            }}
            color[u] = BLACK;
        }}
        nodesData.forEach(n => {{ if (!color[n.id]) dfs(n.id); }});
        links = links.filter(e => !backEdges.has(e));
    }}
    return {{
        nodes: nodesData.map(n => ({{ ...n, name: n.label }})),
        links
    }};
}}

function initGraph() {{
    if (typeof ForceGraph3D === 'undefined') {{ setTimeout(initGraph, 100); return; }}
    document.getElementById('loading-msg').style.display = 'none';
    const el = document.getElementById('graph-container');
    const gData = filteredGraphData();

    G = ForceGraph3D({{ rendererConfig: {{ antialias: false, powerPreference: 'high-performance' }} }})(el)
        .width(el.clientWidth)
        .height(el.clientHeight)
        .graphData(gData)
        .backgroundColor('#080c24')
        // --- 性能关键 ---
        .nodeResolution(6)
        .warmupTicks(0)
        .cooldownTicks(60)
        .d3AlphaDecay(0.06)
        .d3VelocityDecay(0.4)
        // --- 节点 ---
        .nodeLabel(node => {{
            const m = tablesMeta[node.id];
            if (!m) return node.name;
            return '<div class="node-tooltip"><strong>'+node.name+'</strong><br>'
                + '行 '+m.row_count+' | 列 '+(m.columns||[]).length
                + '<br>PK: '+(m.primary_key||'-')+'</div>';
        }})
        .nodeColor(node => {{
            if (hlNodes.size > 0) return hlNodes.has(node.id) ? (groupColors[node.group]||'#b2bec3') : 'rgba(40,50,70,0.25)';
            return groupColors[node.group] || '#b2bec3';
        }})
        .nodeVal(n => n.value || 3)
        .nodeOpacity(0.92)
        // --- 连线 ---
        .linkColor(link => {{
            const rgb = relRgb[link.relType] || defRelRgb;
            if (hlLinks.size > 0) {{
                if (hlLinks.has(link)) return 'rgba('+rgb+',0.9)';
                return 'rgba(30,40,60,0.04)';
            }}
            const a = 0.15 + link.confidence * 0.55;
            return 'rgba('+rgb+','+a+')';
        }})
        .linkWidth(link => {{
            if (hlLinks.size > 0) return hlLinks.has(link) ? 2.0 : 0.15;
            return 0.3 + link.confidence * 0.7;
        }})
        .linkVisibility(link => linksOn)
        .linkDirectionalArrowLength(link => link.confidence >= 0.7 ? 3 : 0)
        .linkLabel(link => link.label)
        // --- 交互 ---
        .onNodeClick(node => {{
            focusNode(node.id);
        }})
        .onNodeHover(node => {{ el.style.cursor = node ? 'pointer' : 'default'; }})
        .onBackgroundClick(() => resetHL())
        .onDagError(e => console.warn('DAG cycle skipped:', e));

    // 增强斥力让节点更分散
    G.d3Force('charge').strength(-300);
    // 减弱连线拉力
    G.d3Force('link').distance(80);
    updateEdgeHud();
    window.addEventListener('resize', () => {{ G.width(el.clientWidth); G.height(el.clientHeight); }});
}}

// ===== CAMERA =====
let camDist = 600;
let isOrtho = false;

function getCamDist() {{
    const cp = G.cameraPosition();
    return Math.sqrt(cp.x*cp.x + cp.y*cp.y + cp.z*cp.z) || camDist;
}}

function setCamView(view) {{
    const d = getCamDist();
    const pos = {{
        top:   {{ x: 0, y: d, z: 0.1 }},
        front: {{ x: 0, y: 0, z: d }},
        back:  {{ x: 0, y: 0, z: -d }},
        left:  {{ x: -d, y: 0, z: 0.1 }},
        right: {{ x: d, y: 0, z: 0.1 }}
    }};
    G.cameraPosition(pos[view], {{ x: 0, y: 0, z: 0 }}, 600);
    // 动画结束后重置相机 up 向量和控制器状态，消除摇移累积
    setTimeout(() => {{
        const camera = G.camera();
        const ctrl = G.controls();
        // 俯视时 up 朝 -Z，其余朝 +Y
        if (view === 'top') {{
            camera.up.set(0, 0, -1);
        }} else {{
            camera.up.set(0, 1, 0);
        }}
        ctrl.target.set(0, 0, 0);
        if (ctrl._eye) ctrl._eye.subVectors(camera.position, ctrl.target);
        if (ctrl._up0) ctrl._up0.copy(camera.up);
        camera.lookAt(0, 0, 0);
    }}, 650);
}}

function togglePersp() {{
    isOrtho = !isOrtho;
    const camera = G.camera();
    const btn = document.getElementById('persp-btn');
    if (isOrtho) {{
        // 切换到正交
        const d = getCamDist();
        camera.fov = 1;
        camera.zoom = 600 / d;
        btn.classList.add('active');
        btn.textContent = 'O';
        btn.title = '正交模式 (点击切换透视)';
    }} else {{
        // 切换到透视
        camera.fov = 75;
        camera.zoom = 1;
        btn.classList.remove('active');
        btn.textContent = 'P';
        btn.title = '透视模式 (点击切换正交)';
    }}
    camera.updateProjectionMatrix();
    // 切换后自动适配视图
    setTimeout(() => G.zoomToFit(400, 40), 100);
}}

// ===== CONTROLS =====
function resetCamera() {{ G.zoomToFit(400, 40); }}

function toggleDagMode() {{
    const modes = [null,'td','lr','radialout'];
    dagMode = modes[(modes.indexOf(dagMode)+1) % modes.length];

    // 每次切换都完全重置力参数，避免状态残留
    G.dagMode(null).graphData({{nodes:[],links:[]}});

    const gData = filteredGraphData();
    if (dagMode) {{
        G.warmupTicks(200).cooldownTicks(150).d3AlphaDecay(0.05).d3VelocityDecay(0.6);
        const isRadial = dagMode === 'radialout';
        G.d3Force('charge').strength(isRadial ? -200 : -600);
        G.d3Force('link').distance(isRadial ? 30 : 40);
    }} else {{
        G.warmupTicks(0).cooldownTicks(80).d3AlphaDecay(0.06).d3VelocityDecay(0.4);
        G.d3Force('charge').strength(-300);
        G.d3Force('link').distance(80);
    }}
    const lvlDist = dagMode === 'radialout' ? 35 : (dagMode ? 50 : undefined);
    G.dagMode(dagMode).dagLevelDistance(lvlDist).graphData(gData);

    // 根据布局方向调整相机
    const setCamera = () => {{
        if (dagMode === 'td' || dagMode === 'lr') {{
            G.cameraPosition({{ x: 0, y: 0, z: 800 }}, {{ x: 0, y: 0, z: 0 }}, 600);
            setTimeout(() => G.zoomToFit(400, 60), 700);
        }} else if (dagMode === 'radialout') {{
            // radial 布局在 XZ 平面展开，从上方俯视最佳
            G.cameraPosition({{ x: 0, y: 800, z: 0.1 }}, {{ x: 0, y: 0, z: 0 }}, 600);
            setTimeout(() => G.zoomToFit(400, 60), 700);
        }} else {{
            G.zoomToFit(400, 60);
        }}
    }};
    setTimeout(setCamera, dagMode ? 600 : 100);

    updateEdgeHud();
    document.getElementById('dag-btn').textContent = dagMode ? 'DAG: '+dagMode : 'DAG 布局';
}}

function toggleLinks() {{
    linksOn = !linksOn;
    G.linkVisibility(link => linksOn);
    updateEdgeHud();
}}

function updateConf(v) {{
    minConf = parseFloat(v);
    document.getElementById('conf-val').textContent = minConf.toFixed(2);
    // rebuild graph data with new confidence filter
    hlNodes = new Set(); hlLinks = new Set();
    const oldNodes = G.graphData().nodes;
    const posMap = {{}};
    oldNodes.forEach(n => {{ posMap[n.id] = {{x:n.x, y:n.y, z:n.z}}; }});
    const gData = filteredGraphData();
    gData.nodes.forEach(n => {{ if(posMap[n.id]) Object.assign(n, posMap[n.id]); }});
    G.graphData(gData);
    updateEdgeHud();
}}

function updateEdgeHud() {{
    const vis = edgesData.filter(e => e.confidence >= minConf).length;
    const ve = document.getElementById('vis-edges');
    const eh = document.getElementById('edge-hud');
    if (ve) ve.textContent = vis;
    if (eh) eh.textContent = vis + ' / ' + edgesData.length + ' edges';
}}

// ===== DETAIL =====
function showNodeDetail(nid) {{
    const m = tablesMeta[nid];
    if (!m) return;
    switchTab('detail');
    document.getElementById('detail-placeholder').style.display = 'none';
    const dc = document.getElementById('detail-content');
    dc.style.display = 'block';

    const outRels = [], inRels = [];
    edgesData.forEach(e => {{
        const s = typeof e.source==='object'?e.source.id:e.source;
        const t = typeof e.target==='object'?e.target.id:e.target;
        if (s===nid) outRels.push(e);
        else if (t===nid) inRels.push(e);
    }});
    const colsHtml = (m.columns||[]).map(c =>
        '<tr><td style="font-weight:500">'+c.name+'</td><td>'+c.dtype+'</td><td>'+(c.samples||[]).slice(0,3).join(', ')+'</td></tr>'
    ).join('');
    function relCard(r, dir) {{
        const s = typeof r.source==='object'?r.source.id:r.source;
        const t = typeof r.target==='object'?r.target.id:r.target;
        const other = dir==='out' ? t : s;
        const dirColor = dir==='out' ? '#60a5fa' : '#4ade80';
        const arrowSym = dir==='out' ? '→' : '←';
        const confPct = (r.confidence*100).toFixed(0);
        const confBg = r.confidence>=0.8 ? 'rgba(74,222,128,0.15)' : r.confidence>=0.5 ? 'rgba(251,191,36,0.15)' : 'rgba(248,113,113,0.15)';
        const confColor = r.confidence>=0.8 ? '#4ade80' : r.confidence>=0.5 ? '#fbbf24' : '#f87171';
        return '<div onclick="focusNode(\\\''+other+'\\\')" style="cursor:pointer;display:flex;align-items:center;padding:4px 6px;margin:2px 0;border-radius:4px;border-left:3px solid '+dirColor+';background:rgba(30,41,59,0.5);transition:background .15s" onmouseover="this.style.background=\\'rgba(30,41,59,0.9)\\'" onmouseout="this.style.background=\\'rgba(30,41,59,0.5)\\'">'
            +'<span style="color:'+dirColor+';font-size:12px;margin-right:6px;flex-shrink:0">'+arrowSym+'</span>'
            +'<span style="flex:1;min-width:0">'
            +'<span style="color:#e2e8f0;font-size:11px;font-weight:500">'+other+'</span>'
            +'<span style="color:#64748b;font-size:10px;margin-left:6px">'+r.label+'</span>'
            +'</span>'
            +'<span style="font-size:10px;padding:1px 6px;border-radius:8px;background:'+confBg+';color:'+confColor+';flex-shrink:0;margin-left:6px">'+confPct+'%</span>'
            +'</div>';
    }}
    const outHtml = outRels.length ? outRels.sort((a,b)=>b.confidence-a.confidence).map(r=>relCard(r,'out')).join('') : '<div style="color:#475569;font-size:11px;padding:4px">无</div>';
    const inHtml = inRels.length ? inRels.sort((a,b)=>b.confidence-a.confidence).map(r=>relCard(r,'in')).join('') : '<div style="color:#475569;font-size:11px;padding:4px">无</div>';

    dc.innerHTML =
        '<h3 style="font-size:15px;margin-bottom:6px;color:#e2e8f0">'+nid+'</h3>'
        + '<div style="font-size:11px;color:#64748b;margin-bottom:10px">'
        + '行 '+m.row_count+' | 列 '+(m.columns||[]).length+' | PK: '+(m.primary_key||'-')
        + '<br>'+m.file_path+'</div>'
        + '<div style="font-size:12px;font-weight:500;color:#94a3b8;margin-bottom:4px">列结构</div>'
        + '<table><tr><th>列名</th><th>类型</th><th>示例</th></tr>'+colsHtml+'</table>'
        + '<div style="font-size:12px;font-weight:500;color:#60a5fa;margin:10px 0 4px;border-top:1px solid #1e293b;padding-top:10px">引用了 → ('+outRels.length+')</div>'
        + outHtml
        + '<div style="font-size:12px;font-weight:500;color:#4ade80;margin:10px 0 4px;border-top:1px solid #1e293b;padding-top:10px">← 被引用 ('+inRels.length+')</div>'
        + inHtml;
}}

// ===== RECALL =====
function eid(e) {{ return typeof e.source==='object'?e.source.id:e.source; }}
function etid(e) {{ return typeof e.target==='object'?e.target.id:e.target; }}

function doRecall() {{
    const q = document.getElementById('recall-input').value.trim();
    if (!q) return;
    const sType = document.getElementById('recall-type').value;
    const mc = parseFloat(document.getElementById('recall-confidence').value);
    const results = [];
    const qL = q.toLowerCase();
    const qP = qL.split(/[\\s,，.。→\\->]+/).filter(Boolean);

    if (sType==='path' && qP.length>=2) {{
        findPaths(qP[0], qP[qP.length-1], 4).forEach((path,i) => {{
            results.push({{ type:'path', title:path.map(p=>p.table).join(' → '), score:1-i*.1, detail:path, tables:path.map(p=>p.table) }});
        }});
    }}
    if (sType==='all'||sType==='table') {{
        Object.keys(tablesMeta).forEach(tn => {{
            let sc=0; const tl=tn.toLowerCase();
            qP.forEach(q => {{ if(tl===q)sc+=1; else if(tl.includes(q))sc+=.7; else if(q.length>=3&&tl.includes(q.substring(0,3)))sc+=.3; }});
            if(sc>0) results.push({{ type:'table', title:tn, score:Math.min(sc,1), meta:tablesMeta[tn], tables:[tn] }});
        }});
    }}
    if (sType==='all'||sType==='column') {{
        Object.entries(tablesMeta).forEach(([tn,meta]) => {{
            const mc2=[];
            (meta.columns||[]).forEach(c => {{ const cl=c.name.toLowerCase(); qP.forEach(q => {{ if(cl===q||cl.includes(q))mc2.push(c); }}); }});
            if(mc2.length>0) {{
                const cs = mc2.some(c=>qP.some(q=>c.name.toLowerCase()===q)) ? 1 : .6;
                results.push({{ type:'column', title:tn+' → '+mc2.map(c=>c.name).join(', '), score:cs, meta, matchedCols:mc2, tables:[tn] }});
            }}
        }});
    }}
    if (sType==='all'||sType==='relation') {{
        edgesData.forEach(edge => {{
            let sc=0; const lb=edge.label.toLowerCase();
            const s=eid(edge), t=etid(edge), ft=(s+' '+t).toLowerCase();
            qP.forEach(q => {{ if(lb.includes(q))sc+=.8; if(ft.includes(q))sc+=.6; }});
            if(sc>0&&sc>=mc) results.push({{ type:'relation', title:s+' → '+t, detail:edge.label, score:Math.min(sc,1), tables:[s,t] }});
        }});
    }}
    results.sort((a,b) => b.score-a.score);
    recallHistory.push({{ query:q, type:sType, minConf:mc, resultCount:results.length, timestamp:new Date().toISOString(), results:results.map(r=>({{ type:r.type,title:r.title,score:r.score }})) }});
    renderRecall(q, results);
}}

function findPaths(fQ, tQ, maxD) {{
    const from = Object.keys(tablesMeta).filter(t=>t.toLowerCase().includes(fQ));
    const to = Object.keys(tablesMeta).filter(t=>t.toLowerCase().includes(tQ));
    if(!from.length||!to.length) return [];
    const adj={{}};
    edgesData.forEach(e => {{
        const s=eid(e), t=etid(e);
        if(!adj[s])adj[s]=[]; if(!adj[t])adj[t]=[];
        adj[s].push({{table:t,label:e.label}}); adj[t].push({{table:s,label:e.label}});
    }});
    const paths=[], toSet=new Set(to);
    for(const st of from) {{
        const queue=[[{{table:st,label:''}}]]; const vis=new Set([st]);
        while(queue.length&&paths.length<5) {{
            const p=queue.shift(); const cur=p[p.length-1].table;
            if(p.length>1&&toSet.has(cur)){{ paths.push(p); continue; }}
            if(p.length>=maxD) continue;
            for(const nb of (adj[cur]||[])) {{ if(!vis.has(nb.table)){{ vis.add(nb.table); queue.push([...p,nb]); }} }}
        }}
    }}
    return paths;
}}

function renderRecall(query, results) {{
    const box = document.getElementById('recall-results');
    const sum = document.getElementById('recall-summary');
    const exp = document.getElementById('recall-export');
    sum.style.display='block';
    sum.innerHTML = '查询 <strong>"'+query+'"</strong> | 召回 <strong>'+results.length+'</strong> 条 | <strong>'+new Set(results.flatMap(r=>r.tables||[])).size+'</strong> 张表';
    if(!results.length) {{ box.innerHTML='<div class="recall-empty">未找到匹配</div>'; exp.style.display='none'; return; }}
    exp.style.display='block';
    box.innerHTML = results.map((r,i) => {{
        let badge='', body='';
        if(r.type==='table') {{
            badge='<span class="recall-card-badge badge-table">表</span>';
            const cols=(r.meta.columns||[]).slice(0,12);
            body='<div class="recall-card-meta">行 '+r.meta.row_count+' | PK: '+(r.meta.primary_key||'-')+' | 列 '+(r.meta.columns||[]).length+'</div>'
                +'<div class="recall-card-cols">'+cols.map(c=>'<span class="col-tag">'+c.name+'</span>').join('')+((r.meta.columns||[]).length>12?'<span class="col-tag">...</span>':'')+'</div>';
        }} else if(r.type==='column') {{
            badge='<span class="recall-card-badge badge-column">列</span>';
            body='<div class="recall-card-meta">表 '+r.tables[0]+' | 行 '+r.meta.row_count+'</div>'
                +'<div class="recall-card-cols">'+r.matchedCols.map(c=>'<span class="col-tag highlight">'+c.name+' ('+c.dtype+')</span>').join('')+'</div>';
        }} else if(r.type==='relation') {{
            badge='<span class="recall-card-badge badge-relation">关系</span>';
            body='<div class="recall-card-detail">'+r.detail+'</div>';
        }} else if(r.type==='path') {{
            badge='<span class="recall-card-badge" style="background:#854d0e44;color:#fbbf24">路径</span>';
            body='<div class="recall-card-detail">'+r.detail.map(p=>p.table).join(' <span class="arrow">→</span> ')+'</div>';
        }}
        return '<div class="recall-card" onclick="hlRecall('+i+',this)" data-tables=\\''+JSON.stringify(r.tables||[])+'\\'>'+
            '<div class="recall-card-header"><span class="recall-card-title">'+r.title+'</span>'+badge+'</div>'+
            '<div class="recall-card-meta"><span class="recall-score">'+r.score.toFixed(2)+'</span></div>'+
            body+
            '<div class="recall-feedback">'+
            '<button class="fb-btn good" onclick="event.stopPropagation();markFB('+i+',\\'good\\',this)">✓</button>'+
            '<button class="fb-btn bad" onclick="event.stopPropagation();markFB('+i+',\\'bad\\',this)">✗</button>'+
            '</div></div>';
    }}).join('');
}}

function hlRecall(idx, el) {{
    document.querySelectorAll('.recall-card').forEach(c=>c.classList.remove('active'));
    el.classList.add('active');
    const tables = JSON.parse(el.dataset.tables||'[]');
    if(!tables.length) return;
    hlNodes = new Set(tables);
    hlLinks = new Set();
    G.graphData().links.forEach(lk => {{
        const s = typeof lk.source==='object'?lk.source.id:lk.source;
        const t = typeof lk.target==='object'?lk.target.id:lk.target;
        if(hlNodes.has(s)||hlNodes.has(t)) hlLinks.add(lk);
    }});
    refreshHL();
    if(tables.length===1) {{
        const nd = G.graphData().nodes.find(n=>n.id===tables[0]);
        if(nd) {{ const r=1+120/Math.hypot(nd.x,nd.y,nd.z); G.cameraPosition({{x:nd.x*r,y:nd.y*r,z:nd.z*r}},nd,800); }}
    }} else G.zoomToFit(400,40,n=>hlNodes.has(n.id));
}}

function focusNode(nid) {{
    showNodeDetail(nid);
    // inject ALL edges for this node into graph (bypass confidence filter)
    focusedNid = nid;
    const oldNodes = G.graphData().nodes;
    const posMap = {{}};
    oldNodes.forEach(n => {{ posMap[n.id] = {{x:n.x, y:n.y, z:n.z}}; }});
    // 提前保存目标节点位置（graphData 重建后位置可能被引擎重置）
    const tgt = posMap[nid] || {{x:0, y:0, z:0}};
    const gData = filteredGraphData();
    gData.nodes.forEach(n => {{ if(posMap[n.id]) Object.assign(n, posMap[n.id]); }});
    G.graphData(gData);
    // highlight this node + direct neighbors
    hlNodes = new Set([nid]);
    hlLinks = new Set();
    G.graphData().links.forEach(lk => {{
        const s = typeof lk.source==='object'?lk.source.id:lk.source;
        const t = typeof lk.target==='object'?lk.target.id:lk.target;
        if (s===nid||t===nid) {{ hlLinks.add(lk); hlNodes.add(s); hlNodes.add(t); }}
    }});
    refreshHL();
    updateEdgeHud();
    // fly camera — 沿当前视线方向在节点前方固定距离，确保节点居中
    setTimeout(() => {{
        // 优先用实时位置，兜底用保存位置
        const nd = G.graphData().nodes.find(n=>n.id===nid);
        const px = (nd && nd.x != null) ? nd.x : tgt.x;
        const py = (nd && nd.y != null) ? nd.y : tgt.y;
        const pz = (nd && nd.z != null) ? nd.z : tgt.z;
        const cam = G.cameraPosition();
        let dx = cam.x - px, dy = cam.y - py, dz = cam.z - pz;
        const len = Math.sqrt(dx*dx + dy*dy + dz*dz) || 1;
        const dist = 150;
        dx = dx/len*dist; dy = dy/len*dist; dz = dz/len*dist;
        G.cameraPosition(
            {{ x: px+dx, y: py+dy, z: pz+dz }},
            {{ x: px, y: py, z: pz }},
            800
        );
    }}, 300);
}}

function resetHL() {{
    hlNodes=new Set(); hlLinks=new Set();
    if (focusedNid) {{
        focusedNid = null;
        const oldNodes = G.graphData().nodes;
        const posMap = {{}};
        oldNodes.forEach(n => {{ posMap[n.id] = {{x:n.x, y:n.y, z:n.z}}; }});
        const gData = filteredGraphData();
        gData.nodes.forEach(n => {{ if(posMap[n.id]) Object.assign(n, posMap[n.id]); }});
        G.graphData(gData);
        updateEdgeHud();
    }}
    refreshHL();
}}

function refreshHL() {{
    G.nodeColor(G.nodeColor()).linkColor(G.linkColor()).linkWidth(G.linkWidth());
}}

function markFB(idx,type,btn) {{
    btn.closest('.recall-card').querySelectorAll('.fb-btn').forEach(b=>b.classList.remove('selected'));
    btn.classList.add('selected');
    if(recallHistory.length) {{ const last=recallHistory[recallHistory.length-1]; if(last.results[idx]) last.results[idx].feedback=type; }}
}}

function exportRecallReport() {{
    const rpt = {{ exportTime:new Date().toISOString(), totalQueries:recallHistory.length, queries:recallHistory }};
    const blob = new Blob([JSON.stringify(rpt,null,2)], {{type:'application/json'}});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href=url; a.download='recall_'+new Date().toISOString().slice(0,10)+'.json'; a.click();
    URL.revokeObjectURL(url);
}}

// ===== ANALYSIS =====
function renderAnalysis() {{
    const box = document.getElementById('analysis-content');
    if (!analysisData || !Object.keys(analysisData).length) {{
        box.innerHTML = '<div style="color:#475569;text-align:center;padding:20px">无分析数据（表数量不足）</div>';
        return;
    }}
    let html = '';
    // 核心表 Top
    if (analysisData.centrality_top && analysisData.centrality_top.length) {{
        html += '<div style="margin-bottom:14px"><div style="font-size:12px;font-weight:600;color:#818cf8;margin-bottom:6px">核心表 Top '+analysisData.centrality_top.length+'</div>';
        analysisData.centrality_top.forEach(([name, score], i) => {{
            const w = Math.max(8, score);
            html += '<div style="display:flex;align-items:center;margin:3px 0;cursor:pointer" onclick="focusNode(\\''+name+'\\')"><span style="color:#94a3b8;font-size:10px;width:18px">'+(i+1)+'</span><span style="flex:1;font-size:11px;color:#e2e8f0">'+name+'</span><div style="width:'+w+'%;height:4px;background:#4f46e5;border-radius:2px;min-width:6px;max-width:60%"></div><span style="font-size:10px;color:#64748b;margin-left:6px;min-width:30px;text-align:right">'+score.toFixed(1)+'</span></div>';
        }});
        html += '</div>';
    }}
    // 业务模块
    if (analysisData.modules && analysisData.modules.length) {{
        html += '<div style="margin-bottom:14px;padding-top:10px;border-top:1px solid #1e293b"><div style="font-size:12px;font-weight:600;color:#818cf8;margin-bottom:6px">业务模块 ('+analysisData.modules.length+')</div>';
        analysisData.modules.forEach((mod, i) => {{
            const preview = mod.slice(0,5).join(', ') + (mod.length>5 ? ' ...+' + (mod.length-5) : '');
            html += '<div style="padding:6px 8px;margin:3px 0;background:#1a2332;border-radius:4px;font-size:11px"><span style="color:#64748b">模块'+(i+1)+' ('+mod.length+'表)</span><br><span style="color:#94a3b8">'+preview+'</span></div>';
        }});
        html += '</div>';
    }}
    // 循环依赖
    if (analysisData.cycles && analysisData.cycles.length) {{
        html += '<div style="margin-bottom:14px;padding-top:10px;border-top:1px solid #1e293b"><div style="font-size:12px;font-weight:600;color:#f87171;margin-bottom:6px">循环依赖 ('+analysisData.cycles.length+')</div>';
        analysisData.cycles.slice(0,10).forEach(cycle => {{
            html += '<div style="padding:4px 8px;margin:2px 0;background:rgba(248,113,113,0.08);border-radius:4px;font-size:10px;color:#fca5a5">'+cycle.join(' → ')+' → '+cycle[0]+'</div>';
        }});
        if (analysisData.cycles.length > 10) html += '<div style="font-size:10px;color:#475569;padding:2px 8px">...还有 '+(analysisData.cycles.length-10)+' 个</div>';
        html += '</div>';
    }} else {{
        html += '<div style="margin-bottom:14px;padding-top:10px;border-top:1px solid #1e293b"><div style="font-size:12px;font-weight:600;color:#4ade80;margin-bottom:4px">循环依赖</div><div style="font-size:11px;color:#475569">无循环依赖</div></div>';
    }}
    // 孤立表
    if (analysisData.orphans && analysisData.orphans.length) {{
        html += '<div style="margin-bottom:14px;padding-top:10px;border-top:1px solid #1e293b"><div style="font-size:12px;font-weight:600;color:#fbbf24;margin-bottom:6px">孤立表 ('+analysisData.orphans.length+')</div>';
        html += '<div style="display:flex;flex-wrap:wrap;gap:3px">';
        analysisData.orphans.slice(0,30).forEach(name => {{
            html += '<span style="padding:2px 6px;background:#1e293b;border-radius:3px;font-size:10px;color:#94a3b8;cursor:pointer" onclick="focusNode(\\''+name+'\\')">'+name+'</span>';
        }});
        if (analysisData.orphans.length > 30) html += '<span style="padding:2px 6px;font-size:10px;color:#475569">...+' + (analysisData.orphans.length-30) + '</span>';
        html += '</div></div>';
    }}
    // 关键路径
    if (analysisData.critical_path && analysisData.critical_path.length > 1) {{
        html += '<div style="padding-top:10px;border-top:1px solid #1e293b"><div style="font-size:12px;font-weight:600;color:#818cf8;margin-bottom:6px">最长依赖链 ('+analysisData.critical_path.length+')</div>';
        html += '<div style="font-size:10px;color:#94a3b8;line-height:1.6;word-break:break-all">'+analysisData.critical_path.join(' → ')+'</div></div>';
    }}
    box.innerHTML = html || '<div style="color:#475569;text-align:center;padding:20px">无分析数据</div>';
}}

// ===== START =====
renderAnalysis();
requestAnimationFrame(fpsLoop);
initGraph();
</script>
</body>
</html>'''
