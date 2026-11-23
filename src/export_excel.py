"""Export the processed IIO research data as a structured Excel workbook."""

from pathlib import Path
from typing import Iterable

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_PATH = DATA_DIR / "processed" / "IIO_Research_Dataset.xlsx"
EXCEL_TEXT_LIMIT = 32_000

FILES = {
    "Comments": DATA_DIR / "raw" / "collected_comments.csv",
    "Videos": DATA_DIR / "processed" / "validated_pilot1.csv",
    "Relevance": DATA_DIR / "processed" / "relevance_screened.csv",
    "IIO_Long": DATA_DIR / "processed" / "iio_annotations_long.csv",
    "IIO_Wide": DATA_DIR / "processed" / "iio_annotations_wide.csv",
    "Sentiment": DATA_DIR / "processed" / "sentiment_emotion.csv",
}

COLUMNS = {
    "Comments": [
        "comment_id",
        "video_id",
        "parent_comment_id",
        "comment_type",
        "comment_text",
        "published_at",
        "updated_at",
        "like_count",
        "total_reply_count",
    ],
    "Videos": ["video_id", "title", "view_count", "comment_count", "duration"],
    "Relevance": [
        "comment_id",
        "video_id",
        "is_english",
        "is_spam",
        "screen_label",
        "human_label",
        "final_label",
    ],
    "IIO_Long": [
        "comment_id",
        "dimension",
        "variable",
        "form_code",
        "form",
        "matched_cues",
        "evidence_text",
        "confidence",
    ],
    "Sentiment": [
        "comment_id",
        "video_id",
        "compound",
        "sentiment",
    ],
}

COLUMN_MEANINGS = {
    "comment_id": "Unique YouTube comment identifier",
    "video_id": "Unique YouTube video identifier",
    "parent_comment_id": "Parent comment identifier for replies",
    "comment_type": "Top-level comment or reply",
    "comment_text": "Comment text",
    "published_at": "Original comment publication date",
    "updated_at": "Last comment update date",
    "like_count": "Number of likes",
    "total_reply_count": "Number of replies",
    "title": "Video title",
    "view_count": "YouTube view count",
    "comment_count": "YouTube reported comment count",
    "duration": "YouTube video duration",
    "is_english": "English-language screening result",
    "is_spam": "Spam screening result",
    "screen_label": "Rule-based relevance label",
    "human_label": "Human relevance label, if available",
    "final_label": "Human label if present, otherwise screen label",
    "dimension": "IIO dimension",
    "variable": "IIO variable",
    "form_code": "IIO form code",
    "form": "IIO form name",
    "matched_cues": "Cue phrases matched in the comment",
    "evidence_text": "Text evidence for the IIO match",
    "confidence": "Automatic IIO match confidence",
    "compound": "VADER compound sentiment score",
    "sentiment": "Sentiment label: negative, neutral, or positive",
}


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Required input file not found: {path}")
    return pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False)


def clean_value(value):
    if pd.isna(value) or value == "":
        return None
    if isinstance(value, str):
        return value[:EXCEL_TEXT_LIMIT]
    return value


def parse_real_dates(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for column in out.columns:
        if column in {"published_at", "updated_at"} or column.endswith("_at"):
            parsed = pd.to_datetime(out[column], errors="coerce", utc=True)
            out[column] = parsed.dt.tz_localize(None)
    return out


def style_sheet(ws, wrap_columns: Iterable[str] = (), date_columns: Iterable[str] = (), freeze: str = "A2"):
    header_fill = PatternFill("solid", fgColor="1F4E78")
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = header_fill

    ws.freeze_panes = freeze
    ws.auto_filter.ref = ws.dimensions

    wrap_set = set(wrap_columns)
    date_set = set(date_columns)
    for cell in ws[1]:
        column_name = cell.value
        if column_name in wrap_set:
            width = 60
        elif column_name in {"comment_id", "video_id", "parent_comment_id"}:
            width = 28
        elif column_name in date_set:
            width = 22
        else:
            width = min(max(len(str(column_name)) + 2, 12), 32)
        ws.column_dimensions[get_column_letter(cell.column)].width = width

    for column_name in wrap_set:
        if column_name in ws.auto_filter.ref:
            pass
        for col_idx, cell in enumerate(ws[1], start=1):
            if cell.value == column_name:
                for row_idx in range(2, ws.max_row + 1):
                    ws.cell(row_idx, col_idx).alignment = Alignment(wrap_text=True, vertical="top")

    for column_name in date_set:
        for col_idx, cell in enumerate(ws[1], start=1):
            if cell.value == column_name:
                for row_idx in range(2, ws.max_row + 1):
                    ws.cell(row_idx, col_idx).number_format = "yyyy-mm-dd hh:mm:ss"


def write_dataframe(ws, df: pd.DataFrame, wrap_columns: Iterable[str] = (), date_columns: Iterable[str] = (), freeze: str = "A2"):
    for col_idx, column in enumerate(df.columns, start=1):
        ws.cell(row=1, column=col_idx, value=str(column))

    for row_idx, row in enumerate(df.itertuples(index=False, name=None), start=2):
        for col_idx, value in enumerate(row, start=1):
            ws.cell(row=row_idx, column=col_idx, value=clean_value(value))

    style_sheet(ws, wrap_columns=wrap_columns, date_columns=date_columns, freeze=freeze)


def write_summary(ws, summaries):
    ws.freeze_panes = "A1"
    row = 1
    for title, df in summaries:
        ws.cell(row=row, column=1, value=title)
        ws.cell(row=row, column=1).font = Font(bold=True, color="FFFFFF")
        ws.cell(row=row, column=1).fill = PatternFill("solid", fgColor="1F4E78")
        row += 1
        for col_idx, column in enumerate(df.columns, start=1):
            ws.cell(row=row, column=col_idx, value=str(column))
            ws.cell(row=row, column=col_idx).font = Font(bold=True)
        row += 1
        for values in df.itertuples(index=False, name=None):
            for col_idx, value in enumerate(values, start=1):
                ws.cell(row=row, column=col_idx, value=clean_value(value))
            row += 1
        row += 2

    for col_idx in range(1, ws.max_column + 1):
        ws.column_dimensions[get_column_letter(col_idx)].width = 28


def main():
    frames = {}
    for sheet_name, path in FILES.items():
        frames[sheet_name] = read_csv(path)

    frames["Comments"] = frames["Comments"][COLUMNS["Comments"]]
    frames["Videos"] = frames["Videos"][COLUMNS["Videos"]]
    frames["Relevance"] = frames["Relevance"][COLUMNS["Relevance"]]
    frames["IIO_Long"] = frames["IIO_Long"][COLUMNS["IIO_Long"]]

    sentiment_emotion_flags = [
        column for column in frames["Sentiment"].columns
        if column.startswith("emo_")
    ]
    sentiment_columns = COLUMNS["Sentiment"] + sentiment_emotion_flags
    missing_sentiment = [column for column in sentiment_columns if column not in frames["Sentiment"].columns]
    if missing_sentiment:
        raise KeyError(f"Missing Sentiment columns: {missing_sentiment}")
    frames["Sentiment"] = frames["Sentiment"][sentiment_columns]

    wide_variable_columns = [
        column for column in frames["IIO_Wide"].columns
        if column != "comment_id"
    ]
    for column in wide_variable_columns:
        frames["IIO_Wide"][column] = pd.to_numeric(
            frames["IIO_Wide"][column], errors="coerce"
        ).fillna(0).astype("int64")

    for sheet_name in ("Comments", "Videos", "Relevance", "IIO_Long", "Sentiment"):
        frames[sheet_name] = parse_real_dates(frames[sheet_name])

    comment_count = len(frames["Comments"])
    if comment_count != 32_000:
        raise ValueError(f"Comments sheet has {comment_count} rows; expected exactly 32,000")

    wb = Workbook()
    wb.remove(wb.active)

    README = wb.create_sheet("README")
    README.append(["Sheet", "Columns", "Meaning", "Row Count"])
    sheet_details = {
        "Comments": "Collected YouTube comments",
        "Videos": "Validated Pilot 1 video metadata",
        "Relevance": "English, spam, and relevance screening results",
        "IIO_Long": "IIO annotations in long format",
        "IIO_Wide": "IIO binary indicators in wide format",
        "Sentiment": "VADER sentiment and emotion flags",
        "Summary": "Pandas-generated descriptive counts",
    }
    for sheet_name in ("Comments", "Videos", "Relevance", "IIO_Long", "IIO_Wide", "Sentiment", "Summary"):
        columns = list(frames[sheet_name].columns) if sheet_name in frames else "Small summary tables"
        column_text = ", ".join(columns) if isinstance(columns, list) else columns
        README.append([sheet_name, column_text, sheet_details[sheet_name], len(frames[sheet_name]) if sheet_name in frames else "See tables"])
    style_sheet(README, freeze="A2")
    README.column_dimensions["A"].width = 16
    README.column_dimensions["B"].width = 80
    README.column_dimensions["C"].width = 48
    README.column_dimensions["D"].width = 16

    ws = wb.create_sheet("Comments")
    write_dataframe(ws, frames["Comments"], wrap_columns={"comment_text"}, date_columns={"published_at", "updated_at"})

    ws = wb.create_sheet("Videos")
    write_dataframe(ws, frames["Videos"], date_columns={"published_at"})

    ws = wb.create_sheet("Relevance")
    write_dataframe(ws, frames["Relevance"])

    ws = wb.create_sheet("IIO_Long")
    write_dataframe(ws, frames["IIO_Long"], wrap_columns={"matched_cues", "evidence_text"})

    ws = wb.create_sheet("IIO_Wide")
    write_dataframe(ws, frames["IIO_Wide"])

    ws = wb.create_sheet("Sentiment")
    write_dataframe(ws, frames["Sentiment"])

    comments_per_video = (
        frames["Comments"]["video_id"]
        .value_counts(dropna=False)
        .rename_axis("video_id")
        .reset_index(name="comment_count")
        .sort_values(["comment_count", "video_id"], ascending=[False, True])
    )
    relevance_counts = (
        frames["Relevance"]["final_label"]
        .value_counts(dropna=False)
        .rename_axis("final_label")
        .reset_index(name="count")
    )
    iio_counts = (
        frames["IIO_Long"]["variable"]
        .value_counts(dropna=False)
        .rename_axis("variable")
        .reset_index(name="annotation_count")
        .sort_values(["annotation_count", "variable"], ascending=[False, True])
    )
    sentiment_counts = (
        frames["Sentiment"]["sentiment"]
        .value_counts(dropna=False)
        .rename_axis("sentiment")
        .reset_index(name="count")
    )

    ws = wb.create_sheet("Summary")
    write_summary(ws, [
        ("Comments per video", comments_per_video),
        ("Relevance label counts", relevance_counts),
        ("IIO variable counts", iio_counts),
        ("Sentiment counts", sentiment_counts),
    ])

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUTPUT_PATH)

    print(f"Comments sheet: {comment_count} rows")
    for sheet_name in ("Videos", "Relevance", "IIO_Long", "IIO_Wide", "Sentiment"):
        print(f"{sheet_name} sheet: {len(frames[sheet_name])} rows")
    print(f"Workbook created: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
