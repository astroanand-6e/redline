import re
import subprocess

import pytest

from redline.pipeline import RenderOptions, plan_render, render_video
from redline.video import ffmpeg_exe


def probe(path):
    result = subprocess.run(
        [ffmpeg_exe(), "-hide_banner", "-i", str(path)],
        capture_output=True,
        check=False,
        text=True,
    )
    return result.stderr


def probe_duration(path):
    match = re.search(r"Duration: (\d+):(\d+):([\d.]+)", probe(path))
    assert match
    h, m, s = match.groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def test_plan_render_reports_words_and_duration():
    plan = plan_render("one two three four", RenderOptions(start_wpm=240, end_wpm=240))
    assert plan.word_count == 4
    # 3 plain words + 1 final word with paragraph pause (2.5x) at 0.25 s/word.
    assert plan.seconds == pytest.approx(0.25 * 3 + 0.25 * 2.5)


def test_plan_render_rejects_empty_text():
    with pytest.raises(ValueError):
        plan_render("   ", RenderOptions())


def test_render_video_produces_mp4_with_expected_duration(tmp_path):
    text = "Read this fast. Then read it faster, please."
    options = RenderOptions(start_wpm=300, end_wpm=300, fmt="16:9")
    progress = []
    out = render_video(text, options, tmp_path, on_progress=progress.append)
    assert out.exists() and out.suffix == ".mp4"
    expected = plan_render(text, options).seconds
    assert probe_duration(out) == pytest.approx(expected, abs=0.15)
    assert progress and progress[-1] == pytest.approx(1.0)
    assert not list(tmp_path.glob("**/*.png")), "frame cache should be cleaned up"


def test_render_video_vertical_format(tmp_path):
    out = render_video("Up and down.", RenderOptions(fmt="9:16"), tmp_path)
    assert "1080x1920" in probe(out)


def test_render_video_rejects_too_many_words(tmp_path):
    with pytest.raises(ValueError, match="words"):
        render_video("word " * 50, RenderOptions(max_words=10), tmp_path)


def test_render_options_validate_format():
    with pytest.raises(ValueError):
        RenderOptions(fmt="4:3")


def test_encode_handles_apostrophes_in_paths(tmp_path):
    from redline.render import FrameRenderer
    from redline.style import DEFAULT_STYLE, FORMATS, Layout
    from redline.video import encode

    odd = tmp_path / "it's here"
    odd.mkdir()
    frame = odd / "f.png"
    FrameRenderer(Layout.for_format(FORMATS["16:9"]), DEFAULT_STYLE).render("ok").save(frame)
    out = encode([(frame, 3), (frame, 3)], 30, odd / "out.mp4")
    assert out.exists() and not list(odd.glob("*.txt"))


@pytest.mark.parametrize("wpm", [1, 10, 5000])
def test_render_options_reject_out_of_range_wpm(wpm):
    with pytest.raises(ValueError, match="wpm"):
        RenderOptions(start_wpm=wpm)
    with pytest.raises(ValueError, match="wpm"):
        RenderOptions(end_wpm=wpm)


def test_render_video_rejects_videos_over_the_duration_cap(tmp_path):
    with pytest.raises(ValueError, match="minutes"):
        render_video(
            "word " * 100, RenderOptions(start_wpm=60, end_wpm=60, max_seconds=30), tmp_path
        )
