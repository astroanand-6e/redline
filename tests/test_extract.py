from pathlib import Path

import pytest

from redline.extract import ExtractionError, clean_pages, clean_text, extract_pages

FIXTURE_PDF = Path(__file__).resolve().parent.parent / "examples" / "gettysburg.pdf"


def make_pages(bodies):
    """Wrap page bodies in a repeated running header and a page-number footer."""
    return [f"Journal of Fast Reading Vol. 3\n{body}\n{i + 1}" for i, body in enumerate(bodies)]


def test_repeated_headers_and_page_numbers_are_removed():
    pages = make_pages(["Alpha beta.", "Gamma delta.", "Epsilon zeta."])
    text = clean_pages(pages)
    assert "Journal" not in text
    assert text.split() == ["Alpha", "beta.", "Gamma", "delta.", "Epsilon", "zeta."]


def test_line_hyphenation_is_rejoined():
    text = clean_pages(["The trans-\nformer model reads fast."])
    assert "transformer" in text


def test_real_hyphen_before_capital_is_kept():
    text = clean_pages(["Built on Pre-\nTraining tricks."])
    assert "Pre-Training" in text


def test_wrapped_lines_join_into_one_paragraph():
    text = clean_pages(["This line wraps\nonto the next one."])
    assert text == "This line wraps onto the next one."


def test_short_lines_followed_by_capitals_start_new_paragraphs():
    body = "This is a long line of body text that fills most of the column width"
    page = f"A Short Title\n{body}\n{body}\nend of para.\nNext paragraph and {body}"
    text = clean_pages([page])
    assert text.startswith("A Short Title\n\n")
    assert "end of para.\n\nNext paragraph" in text


def test_blank_lines_become_paragraph_breaks():
    text = clean_pages(["First paragraph.\n\nSecond paragraph."])
    assert text == "First paragraph.\n\nSecond paragraph."


def test_references_section_is_skipped_when_requested():
    pages = ["Body text here.", "More body.\nReferences\n[1] Someone. A paper. 2017."]
    assert "Someone" not in clean_pages(pages, skip_references=True)
    assert "Someone" in clean_pages(pages, skip_references=False)


def test_references_heading_early_in_document_is_not_treated_as_the_end():
    pages = ["Contents\nReferences\nIntro text.", "Body.", "More body.", "End."]
    assert "End." in clean_pages(pages, skip_references=True)


def test_numeric_and_author_year_citations_are_stripped():
    text = clean_pages(
        ["Attention works [12, 14] and scales (Vaswani et al., 2017; Lee, 2019)."],
        strip_citations=True,
    )
    assert text == "Attention works and scales."


def test_links_emails_arxiv_ids_and_footnote_marks_are_stripped_with_citations():
    raw = "Noam Shazeer∗ noam@google.com arXiv:1706.03762v7 see https://github.com/x/y now."
    assert clean_pages([raw], strip_citations=True) == "Noam Shazeer see now."


def test_citations_are_kept_by_default():
    assert "[3]" in clean_pages(["As shown [3]."])


def test_ligatures_are_normalised():
    assert clean_pages(["eﬃcient ﬁne"]) == "efficient fine"


def test_clean_text_normalises_pasted_text():
    assert clean_text("  Hello\r\nworld\n\n\n\nNext  ") == "Hello world\n\nNext"


def test_extract_pages_reads_a_real_pdf():
    pages = extract_pages(FIXTURE_PDF)
    assert len(pages) >= 1
    assert "Four score and seven years ago" in " ".join(" ".join(pages).split())


def test_extract_pages_respects_page_range():
    pages = extract_pages(FIXTURE_PDF, first_page=1, last_page=1)
    assert len(pages) == 1


def test_extract_pages_rejects_bad_range():
    with pytest.raises(ExtractionError):
        extract_pages(FIXTURE_PDF, first_page=5, last_page=2)


def test_extract_pages_rejects_non_pdf(tmp_path):
    bogus = tmp_path / "not.pdf"
    bogus.write_text("hello")
    with pytest.raises(ExtractionError):
        extract_pages(bogus)


def test_noise_patterns_stay_fast_on_huge_unbroken_tokens():
    import time

    start = time.perf_counter()
    clean_pages(["x" * 200_000 + " end."], strip_citations=True)
    assert time.perf_counter() - start < 2


def test_email_pattern_is_linear_on_adversarial_input():
    import time

    start = time.perf_counter()
    clean_pages(["x@" * 20_000], strip_citations=True)
    assert time.perf_counter() - start < 2


def test_read_errors_do_not_leak_paths(tmp_path):
    bogus = tmp_path / "secret-dir" / "not.pdf"
    bogus.parent.mkdir()
    bogus.write_text("hello")
    with pytest.raises(ExtractionError) as info:
        extract_pages(bogus)
    assert "secret-dir" not in str(info.value)


def test_double_hyphens_become_em_dashes_attached_to_the_previous_word():
    assert clean_text("we can not dedicate -- we can not") == "we can not dedicate— we can not"
