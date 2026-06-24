from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOTS = (
    ROOT / "frontend" / "src",
    ROOT / "ops_agent",
    ROOT / "config",
    ROOT / "scripts",
    ROOT / "docs",
)
TEXT_SUFFIXES = {".css", ".html", ".js", ".json", ".md", ".py", ".scss", ".ts", ".tsx", ".vue", ".yaml", ".yml"}
MOJIBAKE_FRAGMENTS = tuple(
    "".join(chr(codepoint) for codepoint in fragment)
    for fragment in (
        (0x93C5, 0x9E3F, 0x5158),
        (0x7035, 0x7845, 0x763D),
        (0x7487, 0x5A43, 0x67C7),
        (0x7E31, 0x3220, 0x7D29),
        (0x6769, 0x612E, 0x6DEE),
        (0x7487, 0x950B, 0x7730, 0x6FB6, 0x8FAB, 0x89E6),
    )
)


def source_files():
    for source_root in SOURCE_ROOTS:
        for path in source_root.rglob("*"):
            if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
                if "static" not in path.parts and "__pycache__" not in path.parts:
                    yield path


def test_runtime_sources_are_clean_utf8_without_mojibake():
    issues = []
    for path in source_files():
        data = path.read_bytes()
        relative_path = path.relative_to(ROOT)
        if data.startswith(b"\xef\xbb\xbf"):
            issues.append(f"{relative_path}: UTF-8 BOM")
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            issues.append(f"{relative_path}: invalid UTF-8 ({exc})")
            continue
        if "\ufffd" in text:
            issues.append(f"{relative_path}: replacement character")
        if "???" in text:
            issues.append(f"{relative_path}: question-mark corruption")
        if any(0xE000 <= ord(character) <= 0xF8FF for character in text):
            issues.append(f"{relative_path}: private-use character")
        if any(fragment in text for fragment in MOJIBAKE_FRAGMENTS):
            issues.append(f"{relative_path}: mojibake fragment")

    assert not issues, "Encoding issues found:\n" + "\n".join(issues)


def test_sidebar_contains_expected_chinese_labels():
    sidebar = (ROOT / "frontend/src/components/layout/AppSidebar.vue").read_text(encoding="utf-8-sig")
    expected_labels = (
        "\u667a\u80fd\u5bf9\u8bdd",
        "\u77e5\u8bc6\u5e93\u7ba1\u7406",
        "\u65e5\u5fd7\u4e0e\u6848\u4f8b",
        "\u8bca\u65ad\u5de5\u5177",
        "\u7d22\u5f15\u7ba1\u7406",
        "\u6570\u636e\u6e90\u914d\u7f6e",
        "\u5927\u6a21\u578b\u914d\u7f6e",
        "\u8fd0\u7ef4\u5ba2\u670d",
    )
    for label in expected_labels:
        assert label in sidebar

def test_built_frontend_is_clean_and_contains_expected_labels():
    dist = ROOT / "ops_agent/api/static/dist"
    assets = [
        path
        for path in dist.rglob("*")
        if path.is_file() and path.suffix.lower() in {".css", ".html", ".js"}
    ]
    assert assets, "Frontend build output is missing"

    issues = []
    bundle_text = []
    for path in assets:
        data = path.read_bytes()
        relative_path = path.relative_to(ROOT)
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            issues.append(f"{relative_path}: invalid UTF-8 ({exc})")
            continue
        bundle_text.append(text)
        if "\ufffd" in text:
            issues.append(f"{relative_path}: replacement character")
        if "???" in text:
            issues.append(f"{relative_path}: question-mark corruption")
        if any(0xE000 <= ord(character) <= 0xF8FF for character in text):
            issues.append(f"{relative_path}: private-use character")
        if any(fragment in text for fragment in MOJIBAKE_FRAGMENTS):
            issues.append(f"{relative_path}: mojibake fragment")

    assert not issues, "Build encoding issues found:\n" + "\n".join(issues)
    combined = "\n".join(bundle_text)
    for label in ("\u667a\u80fd\u5bf9\u8bdd", "\u77e5\u8bc6\u5e93\u7ba1\u7406", "\u8fd0\u7ef4\u5ba2\u670d"):
        assert label in combined

def test_served_frontend_build_is_not_gitignored():
    ignored_lines = {
        line.strip()
        for line in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    assert "ops_agent/api/static/dist/" not in ignored_lines
