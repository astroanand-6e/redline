"""Draw single RSVP frames with Pillow."""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

from redline.orp import split_at_orp
from redline.style import Layout, Style

MIN_FONT_SCALE = 0.35  # never shrink a word below this share of the base size
SHRINK_STEP = 0.92


class FrameRenderer:
    """Renders one word per frame with its fixation letter on the tick."""

    def __init__(self, layout: Layout, style: Style) -> None:
        self.layout = layout
        self.style = style
        self._fonts: dict[int, ImageFont.FreeTypeFont] = {}
        self._label_font = ImageFont.truetype(str(style.label_font_path), layout.label_size)
        self._base = self._draw_base()

    def _font(self, size: int) -> ImageFont.FreeTypeFont:
        if size not in self._fonts:
            self._fonts[size] = ImageFont.truetype(str(self.style.font_path), size)
        return self._fonts[size]

    def _draw_base(self) -> Image.Image:
        lay, st = self.layout, self.style
        image = Image.new("RGB", (lay.width, lay.height), st.background)
        draw = ImageDraw.Draw(image)
        half = lay.line_width / 2
        for y in (lay.top_rule_y, lay.bottom_rule_y):
            draw.rectangle((0, y - half, lay.width, y + half), fill=st.rule)
        x0, x1 = lay.fixation_x - half, lay.fixation_x + half
        draw.rectangle((x0, lay.top_rule_y, x1, lay.top_rule_y + lay.tick_length), fill=st.rule)
        draw.rectangle(
            (x0, lay.bottom_rule_y - lay.tick_length, x1, lay.bottom_rule_y), fill=st.rule
        )
        return image

    def _fit(self, before: str, pivot: str, after: str) -> tuple[ImageFont.FreeTypeFont, float]:
        """Pick the largest font that keeps the word inside the margins."""
        lay = self.layout
        size = lay.font_size
        min_size = max(8, round(lay.font_size * MIN_FONT_SCALE))
        while True:
            font = self._font(size)
            lead = font.getlength(before + pivot) - font.getlength(pivot) / 2
            x0 = lay.fixation_x - lead
            x1 = x0 + font.getlength(before + pivot + after)
            fits = x0 >= lay.margin_x and x1 <= lay.width - lay.margin_x
            if fits or size <= min_size:
                return font, x0
            size = max(min_size, int(size * SHRINK_STEP))

    def render(self, word: str, wpm_label: str | None = None) -> Image.Image:
        image = self._base.copy()
        draw = ImageDraw.Draw(image)
        before, pivot, after = split_at_orp(word)
        if pivot:
            font, x0 = self._fit(before, pivot, after)
            y = self.layout.baseline_y
            pivot_x = x0 + font.getlength(before + pivot) - font.getlength(pivot)
            after_x = x0 + font.getlength(before + pivot + after) - font.getlength(after)
            draw.text((x0, y), before, font=font, fill=self.style.text, anchor="ls")
            draw.text((pivot_x, y), pivot, font=font, fill=self.style.highlight, anchor="ls")
            draw.text((after_x, y), after, font=font, fill=self.style.text, anchor="ls")
        if wpm_label:
            draw.text(
                (self.layout.label_right, self.layout.label_baseline),
                wpm_label,
                font=self._label_font,
                fill=self.style.label,
                anchor="rs",
            )
        return image
