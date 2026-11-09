"""Text cleaning shared by training and inference.

The same `clean_text` must be used everywhere: if training and serving clean text
differently, the models see a different distribution in production.
"""

import html
import re

_URL_RE = re.compile(r"(https?://\S+|www\.\S+)", re.IGNORECASE)
# @username (Twitter) and u/username, /u/username (Reddit)
_USER_RE = re.compile(r"(?<![\w/])(@\w+|/?u/[\w-]+)", re.IGNORECASE)
# [link text](http://...) -> link text
_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
# **bold**, __bold__, *italic*, _italic_, ~~strike~~, `code`, >! spoiler !<
_MD_EMPHASIS_RE = re.compile(r"(\*\*|__|~~|`|>!|!<)")
_MD_SINGLE_STAR_RE = re.compile(r"(?<!\w)[*_](\S[^*_]*?\S|\S)[*_](?!\w)")
# Markdown block markers at line start: quotes, headings, bullet points
_MD_LINE_PREFIX_RE = re.compile(r"^\s*(>+|#{1,6}|[-*+])\s+", re.MULTILINE)
# Only real tags (<b>, </p>, <br/>): "<3" or "a < b > c" must survive.
_HTML_TAG_RE = re.compile(r"</?[a-zA-Z][^<>]*>")
_WHITESPACE_RE = re.compile(r"\s+")
# Typographic quotes -> ASCII, so "don’t" and "don't" are the same token.
_QUOTES = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"'})


def clean_text(text: str) -> str:
    """Normalize a raw post/comment for the models.

    Lowercase, URLs -> "url", @user / u/user -> "user", markdown and HTML removed,
    HTML entities decoded, typographic quotes -> ASCII, whitespace collapsed.
    Emojis and punctuation are kept: both carry sentiment.
    """
    if not text:
        return ""

    text = html.unescape(text).translate(_QUOTES)
    text = _HTML_TAG_RE.sub(" ", text)
    text = _MD_LINK_RE.sub(r"\1", text)
    text = _URL_RE.sub(" url ", text)
    text = _USER_RE.sub(" user ", text)
    text = _MD_LINE_PREFIX_RE.sub("", text)
    text = _MD_EMPHASIS_RE.sub("", text)
    text = _MD_SINGLE_STAR_RE.sub(r"\1", text)
    text = text.lower()
    return _WHITESPACE_RE.sub(" ", text).strip()
