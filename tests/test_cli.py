from pathlib import Path

from redline.__main__ import _page_range, main

SAMPLE_PDF = Path(__file__).resolve().parent.parent / "examples" / "gettysburg.pdf"


def test_page_range_parsing():
    assert _page_range(None) == (None, None)
    assert _page_range("3") == (3, 3)
    assert _page_range("2-5") == (2, 5)


def test_cli_renders_pdf(tmp_path, capsys):
    out = tmp_path / "out" / "g.mp4"
    code = main([str(SAMPLE_PDF), "-o", str(out), "--start", "600", "--format", "1:1"])
    assert code == 0 and out.exists() and out.stat().st_size > 0
    assert "words" in capsys.readouterr().err


def test_cli_renders_text_file(tmp_path):
    src = tmp_path / "in.txt"
    src.write_text("Hello there. Fast reading works.", encoding="utf-8")
    out = tmp_path / "t.mp4"
    assert main([str(src), "-o", str(out), "--no-wpm", "--theme", "Light"]) == 0
    assert out.exists()


def test_cli_reports_errors(tmp_path, capsys):
    bogus = tmp_path / "bad.pdf"
    bogus.write_text("nope")
    assert main([str(bogus), "-o", str(tmp_path / "x.mp4")]) == 1
    assert "redline:" in capsys.readouterr().err


def test_open_ended_page_range_runs_to_the_end():
    assert _page_range("3-") == (3, None)


def test_invalid_page_range_and_speed_are_rejected(tmp_path, capsys):
    out = str(tmp_path / "x.mp4")
    assert main([str(SAMPLE_PDF), "-o", out, "--pages", "0-2"]) == 1
    assert main([str(SAMPLE_PDF), "-o", out, "--pages", "abc"]) == 1
    assert main([str(SAMPLE_PDF), "-o", out, "--end", "0"]) == 1
    assert capsys.readouterr().err.count("redline:") == 3
