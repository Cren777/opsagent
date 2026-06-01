from pathlib import Path

from ops_agent.models.category_registry import CategoryRegistry


def test_category_registry_creates_renames_pins_and_deletes(tmp_path: Path):
    registry = CategoryRegistry(tmp_path / "categories.json")

    created = registry.create("MySQL/连接")
    registry.create("Nginx/错误日志")
    renamed = registry.rename("MySQL/连接", "MySQL/连接池")
    pinned = registry.set_pinned("MySQL/连接池", True)
    deleted = registry.delete("Nginx/错误日志")

    categories = registry.list_categories()

    assert created["name"] == "MySQL/连接"
    assert renamed["name"] == "MySQL/连接池"
    assert pinned["pinned"] is True
    assert deleted is True
    assert [item["name"] for item in categories] == ["MySQL/连接池"]
