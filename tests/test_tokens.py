import pytest

from redline.tokens import (
    COMMA_PAUSE,
    PARAGRAPH_PAUSE,
    SENTENCE_PAUSE,
    Token,
    tokenize,
)


def texts(tokens):
    return [t.text for t in tokens]


def test_empty_text_gives_no_tokens():
    assert tokenize("") == []
    assert tokenize("   \n\n  ") == []


def test_plain_words_have_unit_pause():
    tokens = tokenize("one two six")[:2]
    assert texts(tokens) == ["one", "two"]
    assert all(t.pause == pytest.approx(1.0) for t in tokens)


def test_sentence_end_gets_longer_pause_than_comma():
    tokens = tokenize("Hi, you. Ok")
    assert tokens[0].pause == pytest.approx(COMMA_PAUSE)
    assert tokens[1].pause == pytest.approx(SENTENCE_PAUSE)
    assert tokens[2].pause == pytest.approx(PARAGRAPH_PAUSE)  # last token ends the text


def test_sentence_end_detected_through_closing_quotes_and_brackets():
    tokens = tokenize('He said "stop." (Really.) then')
    assert tokens[2].pause == pytest.approx(SENTENCE_PAUSE)
    assert tokens[3].pause == pytest.approx(SENTENCE_PAUSE)


def test_paragraph_break_gets_paragraph_pause():
    tokens = tokenize("first para\n\nsecond para")
    assert tokens[1].pause == pytest.approx(PARAGRAPH_PAUSE)
    assert tokens[2].pause == pytest.approx(1.0)


def test_long_words_get_extra_time():
    short, long_ = tokenize("cat extraordinarily x")[:2]
    assert long_.pause > short.pause


def test_numbers_get_extra_time():
    word, number = tokenize("year 2017 x")[:2]
    assert number.pause > word.pause


def test_long_hyphenated_words_are_split_at_hyphens():
    assert texts(tokenize("a state-of-the-art-model b")) == [
        "a",
        "state-of-",
        "the-art-",
        "model",
        "b",
    ]


def test_short_hyphenated_words_are_kept_whole():
    assert texts(tokenize("self-attention")) == ["self-attention"]


def test_em_dash_splits_words():
    assert texts(tokenize("fast—really fast")) == ["fast—", "really", "fast"]


def test_tokens_are_immutable():
    token = Token("x", 1.0)
    with pytest.raises(AttributeError):
        token.text = "y"  # type: ignore[misc]
