"""The JS parity fixtures must match what the Python engine produces today."""

from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).parent / "web" / "make_fixtures.py"


def test_fixtures_are_current():
    spec = importlib.util.spec_from_file_location("make_fixtures", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.FIXTURES.read_text(encoding="utf-8") == module.render(), (
        "tests/web/fixtures.json is stale: run .venv/bin/python tests/web/make_fixtures.py"
    )
