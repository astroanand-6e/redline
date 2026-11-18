import numpy as np
import pytest

from redline.render import FrameRenderer
from redline.style import DEFAULT_STYLE, FORMATS, LIGHT_STYLE, Layout


def red_mask(image):
    arr = np.asarray(image.convert("RGB")).astype(int)
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    return (r > 150) & (g < 130) & (b < 130)


def ink_mask(image):
    arr = np.asarray(image.convert("RGB")).astype(int)
    return arr.mean(axis=2) > 120


@pytest.fixture(scope="module")
def renderer():
    return FrameRenderer(Layout.for_format(FORMATS["16:9"]), DEFAULT_STYLE)


def test_frame_has_requested_size(renderer):
    assert renderer.render("like").size == (1280, 720)


@pytest.mark.parametrize("word", ["a", "the", "like", "understanding", "(hello),"])
def test_red_letter_is_centred_on_the_fixation_tick(renderer, word):
    xs = np.nonzero(red_mask(renderer.render(word)))[1]
    assert xs.size > 0
    centre = (xs.min() + xs.max()) / 2
    assert abs(centre - renderer.layout.fixation_x) <= 4


def test_red_letter_sits_between_the_guide_rules(renderer):
    ys = np.nonzero(red_mask(renderer.render("like")))[0]
    assert renderer.layout.top_rule_y < ys.min() < ys.max() < renderer.layout.bottom_rule_y


def test_very_long_word_is_shrunk_to_fit(renderer):
    word = "pneumonoultramicroscopicsilicovolcanoconiosis"
    ink = ink_mask(renderer.render(word, wpm_label=None))
    xs = np.nonzero(ink)[1]
    assert xs.min() >= renderer.layout.margin_x - 1
    assert xs.max() <= renderer.layout.width - renderer.layout.margin_x + 1


def test_wpm_label_is_drawn_bottom_right(renderer):
    with_label = np.asarray(renderer.render("x", wpm_label="300 wpm").convert("L"))
    without = np.asarray(renderer.render("x", wpm_label=None).convert("L"))
    diff = np.nonzero(with_label.astype(int) - without.astype(int))
    assert diff[0].size > 0
    assert diff[1].min() > renderer.layout.width * 0.6
    assert diff[0].min() > renderer.layout.bottom_rule_y


@pytest.mark.parametrize("fmt", list(FORMATS))
def test_every_format_renders_centred_red_letter(fmt):
    r = FrameRenderer(Layout.for_format(FORMATS[fmt]), DEFAULT_STYLE)
    image = r.render("reading")
    assert image.size == FORMATS[fmt].size
    xs = np.nonzero(red_mask(image))[1]
    assert abs((xs.min() + xs.max()) / 2 - r.layout.fixation_x) <= 4


def test_social_formats_use_larger_text_than_landscape():
    wide = Layout.for_format(FORMATS["16:9"])
    for fmt in ("1:1", "9:16"):
        layout = Layout.for_format(FORMATS[fmt])
        # Relative to frame width, phone formats get noticeably bigger words.
        assert layout.font_size / layout.width > 1.2 * wide.font_size / wide.width
        assert 0 < layout.top_rule_y < layout.bottom_rule_y < layout.height


def test_light_theme_has_light_background():
    r = FrameRenderer(Layout.for_format(FORMATS["16:9"]), LIGHT_STYLE)
    corner = r.render("x").getpixel((5, 5))
    assert min(corner[:3]) > 200
