import csv
import io

MAX_CSV_BYTES = 5 * 1024 * 1024
MAX_CSV_ROWS = 5000


def parse_csv_upload(
    *,
    content: bytes,
    filename: str,
    text_column: str,
    date_column: str | None = None,
) -> tuple[list[dict[str, str | None]], int]:
    if not filename.lower().endswith(".csv"):
        raise ValueError("Only .csv files are supported")

    if len(content) > MAX_CSV_BYTES:
        raise ValueError("CSV file exceeds the 5 MB limit")

    try:
        decoded_content = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        decoded_content = content.decode("latin-1")

    try:
        reader = csv.DictReader(
            io.StringIO(decoded_content, newline=""),
            strict=True,
        )
        fieldnames = reader.fieldnames

        if not fieldnames or not any(name.strip() for name in fieldnames):
            raise ValueError("CSV file must contain a header row")

        if len(fieldnames) != len(set(fieldnames)):
            raise ValueError("CSV header contains duplicate column names")

        if text_column not in fieldnames:
            raise ValueError(f"Text column {text_column!r} was not found in the CSV")

        if date_column is not None and date_column not in fieldnames:
            raise ValueError(f"Date column {date_column!r} was not found in the CSV")

        rows: list[dict[str, str | None]] = []
        skipped_rows = 0

        for row_number, row in enumerate(reader, start=1):
            if row_number > MAX_CSV_ROWS:
                raise ValueError("CSV file exceeds the 5000 row limit")

            if None in row:
                skipped_rows += 1
                continue

            text = row.get(text_column)
            if text is None or not text.strip():
                skipped_rows += 1
                continue

            date = row.get(date_column) if date_column is not None else None
            rows.append(
                {
                    "text": text,
                    "date": date if date and date.strip() else None,
                }
            )

        return rows, skipped_rows
    except csv.Error as exc:
        raise ValueError("CSV file contains malformed rows") from exc
