#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基础冒烟测试

覆盖核心模块的基本功能：
- 值标准化
- 复合值展开
- 模型序列化
- 包含度计算
- 构建流程（mock 数据）
"""

from indexer.storage.json_storage import JsonGraphStorage
from indexer.models import SchemaGraph, TableSchema, RelationEdge
from indexer.discovery.value_utils import (
    normalize_value, normalize_value_set, expand_compound_values
)
import json
import tempfile
import shutil
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_normalize_value():
    """值标准化"""
    assert normalize_value(1) == "1"
    assert normalize_value(1.0) == "1"
    assert normalize_value("001") == "1"
    assert normalize_value(" 1 ") == "1"
    assert normalize_value("1.0") == "1"
    assert normalize_value(3.14) == "3.14"
    assert normalize_value(None) is None
    assert normalize_value("nan") is None
    assert normalize_value("hello") == "hello"
    assert normalize_value("") is None
    print("  [OK] test_normalize_value")


def test_normalize_value_set():
    """值集合标准化"""
    result = normalize_value_set([1, 1.0, "001", " 1 ", None, "nan"])
    assert result == {"1"}, f"Expected {{'1'}}, got {result}"
    print("  [OK] test_normalize_value_set")


def test_expand_compound_values():
    """复合值展开"""
    result = expand_compound_values(["101|102|103", "200", None])
    assert "101" in result
    assert "102" in result
    assert "103" in result
    assert "200" in result
    assert len(result) == 4, f"Expected 4 values, got {len(result)}: {result}"

    # 逗号分隔
    result2 = expand_compound_values(["1,2,3"])
    assert result2 == {"1", "2", "3"}

    # 非复合值不展开
    result3 = expand_compound_values(["hello"])
    assert result3 == {"hello"}

    print("  [OK] test_expand_compound_values")


def test_schema_graph_model():
    """模型基本操作"""
    graph = SchemaGraph()
    t1 = TableSchema(
        name="hero", file_path="hero.xlsx",
        columns=[{"name": "id", "dtype": "int"},
                 {"name": "name", "dtype": "str"}],
        primary_key="id", row_count=100, domain_label="hero"
    )
    t2 = TableSchema(
        name="skill", file_path="skill.xlsx",
        columns=[{"name": "id", "dtype": "int"},
                 {"name": "hero_id", "dtype": "int"}],
        primary_key="id", row_count=50, domain_label="skill"
    )
    graph.add_table(t1)
    graph.add_table(t2)
    assert len(graph.tables) == 2
    assert "hero" in graph._column_index.get("id", set())

    rel = RelationEdge(
        from_table="skill", from_column="hero_id",
        to_table="hero", to_column="id",
        relation_type="fk_naming_convention", confidence=0.85,
        discovery_method="naming_convention",
        evidence="col 'hero_id' matches table 'hero'"
    )
    graph.relations.append(rel)
    assert len(graph.relations) == 1
    assert graph.relations[0].evidence != ""
    assert graph.relations[0].discovery_method == "naming_convention"

    # 删除表
    graph.remove_table("hero")
    assert "hero" not in graph.tables
    print("  [OK] test_schema_graph_model")


def test_json_serialization():
    """JSON 序列化往返"""
    tmp_dir = tempfile.mkdtemp()
    try:
        storage = JsonGraphStorage(tmp_dir)
        graph = SchemaGraph()
        t = TableSchema(
            name="test_table", file_path="test.xlsx",
            columns=[{"name": "id", "dtype": "int"}],
            primary_key="id", row_count=10,
            domain_label="config"
        )
        graph.add_table(t)
        graph.relations.append(RelationEdge(
            from_table="a", from_column="b_id",
            to_table="b", to_column="id",
            relation_type="fk", confidence=0.9,
            discovery_method="containment",
            evidence="shared(5): 1,2,3,4,5"
        ))

        assert storage.save(graph)

        loaded = storage.load()
        assert loaded is not None
        assert "test_table" in loaded.tables
        assert loaded.tables["test_table"].domain_label == "config"
        assert len(loaded.relations) == 1
        assert loaded.relations[0].evidence == "shared(5): 1,2,3,4,5"
        assert loaded.relations[0].discovery_method == "containment"
        print("  [OK] test_json_serialization")
    finally:
        shutil.rmtree(tmp_dir)


def test_llm_export():
    """LLM 紧凑导出"""
    from indexer.export.llm_chunks import export_llm_chunks

    graph = SchemaGraph()
    graph.add_table(TableSchema(
        name="hero", file_path="hero.xlsx",
        columns=[{"name": "id", "dtype": "int"},
                 {"name": "name", "dtype": "str"}],
        primary_key="id", row_count=100, domain_label="hero"
    ))
    graph.relations.append(RelationEdge(
        from_table="skill", from_column="hero_id",
        to_table="hero", to_column="id",
        relation_type="fk", confidence=0.85,
        discovery_method="naming_convention"
    ))

    chunks = export_llm_chunks(graph)
    assert len(chunks) == 1
    assert "hero" in chunks[0]
    assert "hero_id" in chunks[0]

    # 测试文件输出
    tmp = tempfile.NamedTemporaryFile(suffix=".md", delete=False)
    tmp.close()
    try:
        export_llm_chunks(graph, tmp.name)
        with open(tmp.name, 'r', encoding='utf-8') as f:
            content = f.read()
        assert "hero" in content
        print("  [OK] test_llm_export")
    finally:
        os.unlink(tmp.name)


def test_incremental_relation_preservation():
    """增量构建只清除受影响表的关系，保留其他"""
    graph = SchemaGraph()
    # 三张表：hero, skill, item
    for name, domain in [("hero", "hero"), ("skill", "skill"), ("item", "item")]:
        graph.add_table(TableSchema(
            name=name, file_path=f"{name}.xlsx",
            columns=[{"name": "id", "dtype": "int", "sample_values": [1, 2, 3],
                      "unique_count": 3, "null_count": 0, "total_count": 3}],
            primary_key="id", row_count=100, domain_label=domain
        ))

    # 三条关系
    graph.relations = [
        RelationEdge(from_table="hero", from_column="skill_id",
                     to_table="skill", to_column="id",
                     relation_type="fk", confidence=0.9,
                     discovery_method="naming_convention"),
        RelationEdge(from_table="hero", from_column="item_id",
                     to_table="item", to_column="id",
                     relation_type="fk", confidence=0.85,
                     discovery_method="naming_convention"),
        RelationEdge(from_table="skill", from_column="item_id",
                     to_table="item", to_column="id",
                     relation_type="fk", confidence=0.8,
                     discovery_method="containment"),
    ]

    # 模拟增量：只有 hero 表变更
    affected = {"hero"}
    before_count = len(graph.relations)
    assert before_count == 3

    # 只清除涉及 hero 的关系
    graph.relations = [
        r for r in graph.relations
        if r.from_table not in affected and r.to_table not in affected
    ]

    # skill→item 的关系应该被保留（两端都不是 hero）
    assert len(graph.relations) == 1
    assert graph.relations[0].from_table == "skill"
    assert graph.relations[0].to_table == "item"
    print("  [OK] test_incremental_relation_preservation")


def test_scanner_deletion_detection():
    """Scanner 应能检测删除的表"""
    from indexer.scanner.directory_scanner import DirectoryScanner

    tmp_dir = tempfile.mkdtemp()
    try:
        # 创建一个 CSV 文件
        csv_path = os.path.join(tmp_dir, "test_table.csv")
        with open(csv_path, 'w') as f:
            f.write("id,name\n1,a\n2,b\n")

        scanner = DirectoryScanner(data_root=tmp_dir)

        # 首次扫描
        result1 = scanner.scan()
        assert len(result1['new']) == 1
        assert result1['new'][0].name == "test_table"

        # 构建图谱
        graph = SchemaGraph()
        for t in result1['new']:
            graph.add_table(t)

        # 删除文件
        os.unlink(csv_path)

        # 增量扫描应检测到删除
        result2 = scanner.scan(existing_graph=graph)
        assert "test_table" in result2.get('deleted', []), \
            f"Expected 'test_table' in deleted, got {result2.get('deleted', [])}"
        print("  [OK] test_scanner_deletion_detection")
    finally:
        shutil.rmtree(tmp_dir)


def test_row_retriever_predicate_filtering():
    """行级取数应真正按谓词过滤，而不是退化成前几行样本。"""
    from indexer.retrieval.row_retriever import RowRetriever, Predicate

    tmp_dir = tempfile.mkdtemp()
    try:
        csv_path = os.path.join(tmp_dir, "hero.csv")
        with open(csv_path, 'w', encoding='utf-8') as f:
            f.write("id,quality,atk,name\n")
            f.write("1,1,80,a\n")
            f.write("2,5,120,b\n")
            f.write("3,5,160,c\n")

        retriever = RowRetriever(data_root=tmp_dir)
        table_schema = {
            "table_name": "hero",
            "file": "hero.csv",
            "sheet": 0,
            "header_offset": 0,
        }
        predicates = [
            Predicate("quality", "eq", 5, "test"),
            Predicate("atk", "gte", 150, "test"),
        ]
        block = retriever.fetch_rows(table_schema, predicates, max_rows=10)

        assert block.total_matched == 1, block
        assert len(block.rows) == 1, block.rows
        assert block.rows[0]["id"] == "3", block.rows
        print("  [OK] test_row_retriever_predicate_filtering")
    finally:
        shutil.rmtree(tmp_dir)


def test_join_paths_two_hops():
    """JOIN 路径导出应覆盖 2 跳链路。"""
    from indexer.export.rag_assets import export_join_paths

    graph = SchemaGraph()
    for name in ("hero", "hero_skill", "skill"):
        graph.add_table(TableSchema(
            name=name, file_path=f"{name}.xlsx",
            columns=[{"name": "id", "dtype": "int"}],
            primary_key="id", row_count=10, domain_label="test"
        ))

    graph.relations = [
        RelationEdge(
            from_table="hero", from_column="skill_group_id",
            to_table="hero_skill", to_column="id",
            relation_type="fk", confidence=0.9,
            discovery_method="naming_convention"
        ),
        RelationEdge(
            from_table="hero_skill", from_column="skill_id",
            to_table="skill", to_column="id",
            relation_type="fk", confidence=0.88,
            discovery_method="naming_convention"
        ),
    ]

    paths = export_join_paths(graph, max_hops=2)
    info = paths["paths"].get("hero -> skill")
    assert info is not None, paths
    assert info["hops"] == 2, info
    assert info["path"] == ["hero", "hero_skill", "skill"], info
    print("  [OK] test_join_paths_two_hops")


def test_evidence_assembler_auto_analysis_mode():
    """分析型 query 应自动走全量统计模式，避免行采样丢数。"""
    from indexer.export.evidence_assembler import EvidenceAssembler

    tmp_dir = tempfile.mkdtemp()
    try:
        data_dir = os.path.join(tmp_dir, "data")
        os.makedirs(data_dir, exist_ok=True)
        csv_path = os.path.join(data_dir, "hero.csv")
        with open(csv_path, 'w', encoding='utf-8') as f:
            f.write("id,quality,atk,name\n")
            f.write("1,1,80,a\n")
            f.write("2,5,120,b\n")
            f.write("3,5,160,c\n")

        profiles_path = os.path.join(tmp_dir, "table_profiles.jsonl")
        join_paths_path = os.path.join(tmp_dir, "join_paths.json")

        profile = {
            "table_name": "hero",
            "file": "hero.csv",
            "sheet": 0,
            "header_offset": 0,
            "domain": "hero",
            "row_count": 3,
            "primary_key": "id",
            "description": "hero table",
            "columns": [
                {"name": "id", "dtype": "int", "semantic_type": "identifier", "is_pk": True},
                {"name": "quality", "dtype": "int", "semantic_type": "enum", "is_enum": True, "enum_values": [1, 5]},
                {"name": "atk", "dtype": "int", "semantic_type": "metric", "metric_tag": "attack",
                 "stats": {"min": 80, "max": 160, "mean": 120}},
                {"name": "name", "dtype": "str", "semantic_type": "descriptor"},
            ],
        }
        with open(profiles_path, 'w', encoding='utf-8') as f:
            f.write(json.dumps(profile, ensure_ascii=False) + "\n")
        with open(join_paths_path, 'w', encoding='utf-8') as f:
            json.dump({"paths": {}}, f, ensure_ascii=False)

        assembler = EvidenceAssembler(
            profiles_path=profiles_path,
            join_paths_path=join_paths_path,
            data_root=data_dir,
        )
        evidence = assembler.assemble(
            query="分析英雄攻击力分布",
            table_names=["hero"],
        )

        assert evidence["_meta"]["analysis_mode"] is True, evidence["_meta"]
        assert evidence["key_rows"] == [], evidence["key_rows"]
        assert len(evidence.get("analytical_result", [])) == 1, evidence
        assert evidence["analytical_result"][0]["table"] == "hero", evidence
        print("  [OK] test_evidence_assembler_auto_analysis_mode")
    finally:
        shutil.rmtree(tmp_dir)


def test_build_validator_missing_artifacts_and_regression():
    """构建后校验应能识别缺失产物并输出 P0。"""
    from indexer.validation import BuildValidator

    tmp_dir = tempfile.mkdtemp()
    try:
        build_dir = os.path.join(tmp_dir, "build")
        os.makedirs(build_dir, exist_ok=True)
        with open(os.path.join(build_dir, "meta.json"), "w", encoding="utf-8") as f:
            json.dump({"table_count": 1, "relation_count": 5}, f)
        with open(os.path.join(build_dir, "analysis.json"), "w", encoding="utf-8") as f:
            json.dump({"modules": [], "orphans": []}, f)
        with open(os.path.join(build_dir, "join_paths.json"), "w", encoding="utf-8") as f:
            json.dump({"_meta": {"total_paths": 3, "max_hops": 2}, "paths": {}}, f)

        validator = BuildValidator(data_root=tmp_dir)
        report = validator.validate(build_dir=build_dir, build_id="t1")

        assert report.status == "P0", report
        assert report.publish_allowed is False, report
        assert any(a.code == "missing_artifacts" for a in report.alerts), report.alerts
        print("  [OK] test_build_validator_missing_artifacts_and_regression")
    finally:
        shutil.rmtree(tmp_dir)


if __name__ == "__main__":
    print("Running smoke tests...")
    test_normalize_value()
    test_normalize_value_set()
    test_expand_compound_values()
    test_schema_graph_model()
    test_json_serialization()
    test_llm_export()
    test_incremental_relation_preservation()
    test_scanner_deletion_detection()
    test_row_retriever_predicate_filtering()
    test_join_paths_two_hops()
    test_evidence_assembler_auto_analysis_mode()
    test_build_validator_missing_artifacts_and_regression()
    print("\nAll tests passed!")
