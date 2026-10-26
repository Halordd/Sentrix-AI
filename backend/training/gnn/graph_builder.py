"""Minimal C AST graph builder for the GNN scaffold.

AST edges are real; CFG/PDG edges are a later ablation. This module is useful
only after a labelled dataset is available.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Graph:
    nodes: list[dict]
    edges: list[tuple[int, int]]
    function_name: str


def _parser():
    try:
        from tree_sitter import Language, Parser
        import tree_sitter_c
    except ImportError as exc:
        raise RuntimeError("install tree-sitter and tree-sitter-c") from exc
    return Parser(Language(tree_sitter_c.language()))


def build_ast_graph(
    source: str, function_name: str | None = None, with_cfg: bool = False
) -> Graph:
    parser = _parser()
    tree = parser.parse(source.encode())
    root = tree.root_node

    functions = []

    def find(node):
        if node.type == "function_definition":
            name_node = node.child_by_field_name("declarator")
            text = name_node.text.decode() if name_node else "anonymous"
            functions.append((node, text))
        for child in node.children:
            find(child)

    find(root)
    if not functions:
        raise ValueError("no function_definition found")
    chosen = functions[0]
    if function_name:
        matches = [item for item in functions if function_name in item[1]]
        if not matches:
            raise ValueError(f"function not found: {function_name}")
        chosen = matches[0]
    function_node, name = chosen

    nodes: list[dict] = []
    edges: list[tuple[int, int]] = []
    index: dict[int, int] = {}
    node_objects = []

    def walk(node, parent: int | None = None):
        if not node.is_named:
            return
        current = len(nodes)
        index[node.id] = current
        node_objects.append(node)
        nodes.append(
            {
                "type": node.type,
                "text": node.text.decode(errors="replace")[:120],
                "start": node.start_byte,
                "end": node.end_byte,
            }
        )
        if parent is not None:
            edges.append((parent, current))
        for child in node.children:
            walk(child, current)

    walk(function_node)

    if with_cfg:
        # Approximate CFG: sequential edges between named siblings inside a
        # compound statement, plus control -> body edges.
        for node in node_objects:
            if node.type == "compound_statement":
                children = [child for child in node.children if child.is_named]
                for left, right in zip(children, children[1:]):
                    if left.id in index and right.id in index:
                        edges.append((index[left.id], index[right.id]))
            if node.type in {
                "if_statement",
                "for_statement",
                "while_statement",
                "switch_statement",
            }:
                body = node.child_by_field_name("body")
                if body is not None and body.id in index:
                    edges.append((index[node.id], index[body.id]))

    deduped = list(dict.fromkeys(edges))
    degree = [0] * len(nodes)
    for left, right in deduped:
        degree[left] += 1
        degree[right] += 1
    for node, value in zip(nodes, degree):
        node["degree"] = value
    return Graph(nodes=nodes, edges=deduped, function_name=name)
