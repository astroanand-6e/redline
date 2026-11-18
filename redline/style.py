"""Visual style and frame geometry.

Proportions were measured from the reference RSVP video (1280x720): guide
rules at 23% and 78% of the height, fixation tick at 37.6% of the width,
text baseline at 55%, wpm label bottom-right in grey italic.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

FONT_DIR = Path(__file__).resolve().parent.parent / "fonts"

Color = tuple[int, int, int]

# Geometry as fractions of the 16:9 "stage" (see Layout.for_format).
TOP_RULE = 0.231
BOTTOM_RULE = 0.784
TICK_LENGTH = 0.094
FIXATION_X = 0.376
BASELINE = 0.551
FONT_SIZE = 0.152
LABEL_RIGHT = 0.916
LABEL_BASELINE = 0.857
LABEL_SIZE = 0.058
LINE_WIDTH = 0.0045
MARGIN_X = 0.04


@dataclass(frozen=True)
class VideoFormat:
    label: str
    size: tuple[int, int]
    stage_scale: float = 1.0  # >1 enlarges the stage for phone-first formats


FORMATS: dict[str, VideoFormat] = {
    "16:9": VideoFormat("Landscape 16:9 (1280×720)", (1280, 720)),
    "9:16": VideoFormat("Vertical 9:16 (1080×1920) for Reels/Shorts", (1080, 1920), 1.5),
    "1:1": VideoFormat("Square 1:1 (1080×1080) for LinkedIn/X", (1080, 1080), 1.35),
}


@dataclass(frozen=True)
class Style:
    background: Color
    text: Color
    highlight: Color
    rule: Color
    label: Color
    font_path: Path = FONT_DIR / "STIXTwoText.ttf"
    label_font_path: Path = FONT_DIR / "STIXTwoText-Italic.ttf"


DEFAULT_STYLE = Style(
    background=(0, 0, 0),
    text=(242, 242, 242),
    highlight=(222, 68, 76),
    rule=(40, 40, 40),
    label=(72, 72, 72),
)

LIGHT_STYLE = Style(
    background=(250, 248, 243),
    text=(24, 24, 24),
    highlight=(214, 52, 60),
    rule=(214, 210, 202),
    label=(150, 146, 140),
)

THEMES: dict[str, Style] = {"Dark": DEFAULT_STYLE, "Light": LIGHT_STYLE}


@dataclass(frozen=True)
class Layout:
    """Pixel geometry for one output size."""

    width: int
    height: int
    top_rule_y: int
    bottom_rule_y: int
    tick_length: int
    fixation_x: int
    baseline_y: int
    font_size: int
    label_right: int
    label_baseline: int
    label_size: int
    line_width: int
    margin_x: int

    @classmethod
    def for_format(cls, fmt: VideoFormat) -> Layout:
        """Fit a 16:9 stage across the frame width (scaled per format), centred vertically."""
        width, height = fmt.size
        stage_h = min(height, width * 9 / 16 * fmt.stage_scale)
        stage_top = (height - stage_h) / 2

        def sy(fraction: float) -> int:
            return round(stage_top + stage_h * fraction)

        return cls(
            width=width,
            height=height,
            top_rule_y=sy(TOP_RULE),
            bottom_rule_y=sy(BOTTOM_RULE),
            tick_length=round(stage_h * TICK_LENGTH),
            fixation_x=round(width * FIXATION_X),
            baseline_y=sy(BASELINE),
            font_size=round(stage_h * FONT_SIZE),
            label_right=round(width * LABEL_RIGHT),
            label_baseline=sy(LABEL_BASELINE),
            label_size=round(stage_h * LABEL_SIZE),
            line_width=max(2, round(stage_h * LINE_WIDTH)),
            margin_x=round(width * MARGIN_X),
        )
