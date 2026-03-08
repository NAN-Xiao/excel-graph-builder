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
    import tempfile
    import shutil
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
    import tempfile
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


if __name__ == "__main__":
    print("Running smoke tests...")
    test_normalize_value()
    test_normalize_value_set()
    test_expand_compound_values()
    test_schema_graph_model()
    test_json_serialization()
    test_llm_export()
    print("\nAll tests passed!")
