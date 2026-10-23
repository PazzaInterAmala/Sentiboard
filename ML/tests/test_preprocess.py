import pytest

from sentiboard_ml.preprocess import clean_text


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Great, another delay from this airline", "great, another delay from this airline"),
        ("Check https://example.com/x?y=1 now", "check url now"),
        ("see www.apple.com", "see url"),
        ("@delta you lost my bag", "user you lost my bag"),
        ("thanks u/some_guy and /u/Other-One", "thanks user and user"),
        ("r/apple is great", "r/apple is great"),
        ("email me at a@b.com", "email me at a@b.com"),
        ("[docs](https://x.org) are **really** bad", "docs are really bad"),
        ("this is *so* _good_", "this is so good"),
        ("> quoted line\n# Heading\n- item", "quoted line heading item"),
        ("Tom &amp; Jerry &gt; all", "tom & jerry > all"),
        ("<p>hello <b>world</b></p>", "hello world"),
        ("i <3 you > them", "i <3 you > them"),
        ("price < 5 and > 3", "price < 5 and > 3"),
        ("line<br/>break", "line break"),
        ("*sigh* ok", "sigh ok"),
        ("snake_case_name and 2*3*4", "snake_case_name and 2*3*4"),
        ("love it 😍🔥", "love it 😍🔥"),
        ("I don’t think “so”", 'i don\'t think "so"'),
        ("  lots   of\n\n\twhitespace  ", "lots of whitespace"),
        ("", ""),
    ],
)
def test_clean_text(raw, expected):
    assert clean_text(raw) == expected


def test_clean_text_is_idempotent():
    raw = "@user OMG **best** phone ever!!! https://t.co/abc 😍"
    once = clean_text(raw)
    assert clean_text(once) == once
