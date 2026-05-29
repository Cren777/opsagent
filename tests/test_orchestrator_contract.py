import ast
from pathlib import Path


def test_data_analysis_handler_accepts_router_extra_kwargs():
    source = Path("ops_agent/core/orchestrator.py").read_text(encoding="utf-8")
    module = ast.parse(source)
    handler = next(
        node for node in ast.walk(module)
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "_handle_data_analysis"
    )

    assert handler.args.kwarg is not None
