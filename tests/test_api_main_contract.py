import ast
from pathlib import Path

import pytest


MAIN_MODULE = Path(__file__).parents[1] / "ops_agent" / "api" / "main.py"


def test_api_main_source_compiles():
    source = MAIN_MODULE.read_text(encoding="utf-8-sig")

    try:
        compile(source, str(MAIN_MODULE), "exec")
    except SyntaxError as exc:
        pytest.fail(f"ops_agent.api.main must compile: {exc}")


def _include_router_calls() -> list[ast.Call]:
    tree = ast.parse(MAIN_MODULE.read_text(encoding="utf-8-sig"))
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "app"
        and node.func.attr == "include_router"
    ]


def _router_name(call: ast.Call) -> str | None:
    if not call.args:
        return None
    router = call.args[0]
    if (
        isinstance(router, ast.Attribute)
        and router.attr == "router"
        and isinstance(router.value, ast.Name)
    ):
        return router.value.id
    return None


def _requires_current_user(call: ast.Call) -> bool:
    dependencies = next(
        (keyword.value for keyword in call.keywords if keyword.arg == "dependencies"),
        None,
    )
    if not isinstance(dependencies, ast.List):
        return False
    return any(
        isinstance(item, ast.Call)
        and isinstance(item.func, ast.Name)
        and item.func.id == "Depends"
        and item.args
        and isinstance(item.args[0], ast.Name)
        and item.args[0].id == "get_current_user"
        for item in dependencies.elts
    )


def test_api_main_mounts_public_auth_router():
    routers = {_router_name(call) for call in _include_router_calls()}

    assert "auth" in routers


def test_api_main_protects_business_routers():
    calls = {
        router_name: call
        for call in _include_router_calls()
        if (router_name := _router_name(call))
    }
    protected_routers = {
        "chat",
        "config",
        "uploads",
        "knowledge",
        "incidents",
        "diagnostics",
        "indexes",
    }

    assert protected_routers <= calls.keys()
    assert all(_requires_current_user(calls[name]) for name in protected_routers)