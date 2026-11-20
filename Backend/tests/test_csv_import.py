import pytest

from app.services.csv_import import MAX_CSV_BYTES, parse_csv_upload


def test_parse_csv_upload_returns_text_dates_and_skipped_count():
    content = b"review,date\nGreat product,2026-11-01\n   ,2026-11-02\nWorks well,\n"

    rows, skipped_rows = parse_csv_upload(
        content=content,
        filename="reviews.csv",
        text_column="review",
        date_column="date",
    )

    assert rows == [
        {"text": "Great product", "date": "2026-11-01"},
        {"text": "Works well", "date": None},
    ]
    assert skipped_rows == 1


def test_parse_csv_upload_accepts_utf8_bom_and_latin1():
    utf8_rows, utf8_skipped = parse_csv_upload(
        content="\ufefftext\ncafé\n".encode("utf-8"),
        filename="utf8.csv",
        text_column="text",
    )
    latin1_rows, latin1_skipped = parse_csv_upload(
        content="text\ncafé\n".encode("latin-1"),
        filename="latin1.CSV",
        text_column="text",
    )

    assert utf8_rows == [{"text": "café", "date": None}]
    assert latin1_rows == [{"text": "café", "date": None}]
    assert utf8_skipped == latin1_skipped == 0


@pytest.mark.parametrize(
    ("content", "filename", "text_column", "date_column", "message"),
    [
        (b"text\nhello\n", "reviews.txt", "text", None, "Only .csv files"),
        (b"", "reviews.csv", "text", None, "header row"),
        (b"review\nhello\n", "reviews.csv", "text", None, "Text column"),
        (
            b"text\nhello\n",
            "reviews.csv",
            "text",
            "date",
            "Date column",
        ),
        (
            b"text,text\nhello,world\n",
            "reviews.csv",
            "text",
            None,
            "duplicate column names",
        ),
        (b'text\n"unterminated\n', "reviews.csv", "text", None, "malformed rows"),
    ],
)
def test_parse_csv_upload_rejects_invalid_file_or_columns(
    content: bytes,
    filename: str,
    text_column: str,
    date_column: str | None,
    message: str,
):
    with pytest.raises(ValueError, match=message):
        parse_csv_upload(
            content=content,
            filename=filename,
            text_column=text_column,
            date_column=date_column,
        )


def test_parse_csv_upload_rejects_file_larger_than_limit():
    with pytest.raises(ValueError, match="5 MB limit"):
        parse_csv_upload(
            content=b"x" * (MAX_CSV_BYTES + 1),
            filename="large.csv",
            text_column="text",
        )


def test_parse_csv_upload_rejects_more_than_5000_rows():
    content = ("text\n" + "row\n" * 5001).encode()

    with pytest.raises(ValueError, match="5000 row limit"):
        parse_csv_upload(
            content=content,
            filename="many.csv",
            text_column="text",
        )
