import os
import time

import gradio as gr
import pytest

import app


def no_progress(*_args, **_kwargs):
    return None


def test_extract_text_from_sample_pdf():
    text = app.extract_text(str(app.SAMPLE_PDF), 1, None, True, True)
    assert text.startswith("The Gettysburg Address")
    assert "shall not perish from the earth." in text


def test_extract_text_treats_zero_last_page_as_end_of_document():
    # The "To page" box defaults to 0, meaning "through the last page".
    assert "perish from the earth." in app.extract_text(str(app.SAMPLE_PDF), 1, 0, True, True)


def test_extract_text_without_file_leaves_textbox_alone():
    assert app.extract_text(None, 1, None, True, True) == gr.update()


def test_extract_text_reports_bad_page_range():
    with pytest.raises(gr.Error):
        app.extract_text(str(app.SAMPLE_PDF), 9, 3, True, True)


def test_describe_summarises_words_and_speed():
    summary = app.describe("one two three", 300, 600)
    assert "3 words" in summary and "300→600 wpm" in summary


def test_describe_constant_speed_and_empty_text():
    assert "300 wpm" in app.describe("one two", 300, 300)
    assert "Upload a PDF" in app.describe("  ", 300, 300)


def test_describe_warns_over_word_limit(monkeypatch):
    monkeypatch.setattr(app, "MAX_WORDS", 2)
    assert "limit" in app.describe("a b c d", 300, 300)


def test_render_returns_video_path(tmp_path, monkeypatch):
    monkeypatch.setattr(app, "OUTPUT_DIR", tmp_path)
    path = app.render("Fast words here.", 300, 300, "1:1", "Light", False, progress=no_progress)
    assert path.endswith(".mp4") and os.path.exists(path)


def test_render_rejects_empty_text():
    with pytest.raises(gr.Error):
        app.render("", 300, 300, "16:9", "Dark", True, progress=no_progress)


def test_render_surfaces_word_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(app, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(app, "MAX_WORDS", 2)
    with pytest.raises(gr.Error, match="limit"):
        app.render("a b c d", 300, 300, "16:9", "Dark", True, progress=no_progress)


def test_prune_old_outputs_removes_only_stale_files(tmp_path, monkeypatch):
    monkeypatch.setattr(app, "OUTPUT_DIR", tmp_path)
    old, fresh = tmp_path / "redline-old.mp4", tmp_path / "redline-new.mp4"
    old.write_bytes(b"x")
    fresh.write_bytes(b"x")
    stale = time.time() - app.OUTPUT_TTL_SECONDS - 10
    os.utime(old, (stale, stale))
    app._prune_old_outputs()
    assert not old.exists() and fresh.exists()


def test_build_demo_constructs_blocks():
    assert isinstance(app.build_demo(), gr.Blocks)
    assert isinstance(app._theme(), gr.themes.Base)


def test_prune_also_removes_stale_frame_dirs_and_lists(tmp_path, monkeypatch):
    monkeypatch.setattr(app, "OUTPUT_DIR", tmp_path)
    frames = tmp_path / "frames-abc"
    frames.mkdir()
    (frames / "000000.png").write_bytes(b"x")
    listing = tmp_path / "redline-x.txt"
    listing.write_text("file 'a'")
    stale = time.time() - app.OUTPUT_TTL_SECONDS - 10
    for p in (frames, listing):
        os.utime(p, (stale, stale))
    app._prune_old_outputs()
    assert not frames.exists() and not listing.exists()


@pytest.mark.parametrize("wpm", [1, 50, 99_999])
def test_render_rejects_speeds_outside_the_slider_range(wpm):
    with pytest.raises(gr.Error, match="wpm"):
        app.render("hello there", wpm, 300, "16:9", "Dark", True, progress=no_progress)


def test_render_and_describe_reject_oversized_text(monkeypatch):
    monkeypatch.setattr(app, "MAX_CHARS", 10)
    assert "characters" in app.describe("x" * 50, 300, 300)
    with pytest.raises(gr.Error, match="characters"):
        app.render("x" * 50, 300, 300, "16:9", "Dark", True, progress=no_progress)


def test_extract_text_gives_up_on_slow_pdfs(monkeypatch):
    monkeypatch.setattr(app, "EXTRACT_TIMEOUT_SECONDS", 0.001)
    with pytest.raises(gr.Error, match="too long"):
        app.extract_text(str(app.SAMPLE_PDF), 1, 0, True, True)
