"""Build a one-row-per-comment master Excel file from IIO_Research_Dataset.xlsx.

Usage: python -m src.build_master_excel [input.xlsx] [output.xlsx]
"""

import sys
from pathlib import Path

import pandas as pd

DEF_IN = Path("data/processed/IIO_Research_Dataset.xlsx")
DEF_OUT = Path("data/processed/IIO_Research_Dataset_Master.xlsx")
MIN_CONF = 0.5
DIM_ORDER = {"Issue": 0, "Intervention": 1, "Outcome": 2}


def main(src=DEF_IN, dst=DEF_OUT):
    x = pd.ExcelFile(src)
    sh = {n: x.parse(n) for n in x.sheet_names if n != "README"}
    com, vid, rel = sh["Comments"], sh["Videos"], sh["Relevance"]
    iio, wide, sen = sh["IIO_Long"], sh["IIO_Wide"], sh["Sentiment"]

    titles = vid.drop_duplicates("video_id")[["video_id", "title"]].rename(
        columns={"title": "video_title"}
    )
    m = com.merge(titles, on="video_id", how="left")
    m = m.merge(
        rel[
            [
                "comment_id",
                "is_english",
                "is_spam",
                "screen_label",
                "human_label",
                "final_label",
            ]
        ],
        on="comment_id",
        how="left",
    )
    m["relevance_label"] = m.pop("final_label")
    m["label_source"] = m.human_label.notna().map({True: "human", False: "rule_based"})
    emo = [c for c in sen.columns if c.startswith("emo_")]
    m = m.merge(
        sen[["comment_id", "compound", "sentiment"] + emo], on="comment_id", how="left"
    )

    keep = iio[iio.confidence >= MIN_CONF].copy()
    keep["dim_rank"] = keep.dimension.map(DIM_ORDER)
    keep = keep.sort_values(["comment_id", "dim_rank", "variable"])
    g = keep.groupby("comment_id")
    agg = pd.DataFrame(
        {
            "iio_dimensions": g.dimension.agg(lambda s: "; ".join(dict.fromkeys(s))),
            "iio_variables": g.variable.agg(lambda s: "; ".join(dict.fromkeys(s))),
            "iio_forms": g.apply(
                lambda d: "; ".join(f"{a} ({b})" for a, b in zip(d.form_code, d.form)),
                include_groups=False,
            ),
            "iio_evidence": g.evidence_text.agg(
                lambda s: " | ".join(dict.fromkeys(s.astype(str)))
            ),
            "iio_max_confidence": g.confidence.max(),
        }
    ).reset_index()
    m = m.merge(agg, on="comment_id", how="left")
    m.insert(
        m.columns.get_loc("iio_dimensions"),
        "iio_labelled",
        m.iio_dimensions.notna().astype(int),
    )
    w = wide.rename(columns={c: f"IIO_{c}" for c in wide.columns if c != "comment_id"})
    m = m.merge(w, on="comment_id", how="left")
    for c in w.columns:
        if c != "comment_id":
            m[c] = m[c].fillna(0).astype(int)

    cols = (
        [
            "comment_id",
            "video_id",
            "video_title",
            "parent_comment_id",
            "comment_type",
            "comment_text",
            "published_at",
            "updated_at",
            "like_count",
            "total_reply_count",
            "is_english",
            "is_spam",
            "relevance_label",
            "label_source",
            "screen_label",
            "human_label",
            "sentiment",
            "compound",
        ]
        + emo
        + [
            "iio_labelled",
            "iio_dimensions",
            "iio_variables",
            "iio_forms",
            "iio_evidence",
            "iio_max_confidence",
        ]
        + [c for c in w.columns if c != "comment_id"]
    )
    m = m[cols]
    assert len(m) == len(com) and m.comment_id.is_unique

    dictionary = pd.DataFrame(
        [
            ("comment_id", "Unique YouTube comment ID (join key across sheets)"),
            ("video_id / video_title", "Video the comment belongs to and its title"),
            (
                "parent_comment_id",
                "For replies: ID of the top-level comment (empty for top-level)",
            ),
            ("comment_type", "top_level or reply"),
            ("comment_text", "Comment text (plain text)"),
            ("published_at / updated_at", "Dates from the YouTube API"),
            (
                "like_count / total_reply_count",
                "Likes; number of replies (top-level comments)",
            ),
            ("is_english / is_spam", "Rule-based language and spam flags"),
            (
                "relevance_label",
                "Final label: human label if one exists, otherwise rule-based label",
            ),
            ("label_source", "human (249 hand-labelled comments) or rule_based"),
            (
                "screen_label / human_label",
                "Rule-based label; human label where available",
            ),
            (
                "sentiment / compound",
                "VADER sentiment label and compound score (-1 to +1)",
            ),
            ("emo_*", "Lexicon-based emotion flags (1 = present)"),
            (
                "iio_labelled",
                "1 if at least one IIO label at confidence >= 0.5 (relevant or partially relevant comments only)",
            ),
            (
                "iio_dimensions / iio_variables / iio_forms",
                "Issue/Intervention/Outcome labels; preliminary cue-matching, about 50% precision",
            ),
            (
                "iio_evidence / iio_max_confidence",
                "Text evidence for the labels; highest match confidence",
            ),
            (
                "IIO_<variable>",
                "1 if that IIO variable was labelled (confidence >= 0.5), else 0",
            ),
        ],
        columns=["Column", "Meaning"],
    )

    with pd.ExcelWriter(
        dst, engine="xlsxwriter", datetime_format="yyyy-mm-dd hh:mm:ss"
    ) as xw:
        wb = xw.book
        hdr = wb.add_format(
            {
                "bold": True,
                "font_color": "white",
                "bg_color": "#1F4E78",
                "valign": "top",
            }
        )
        wrap = wb.add_format({"text_wrap": True, "valign": "top"})

        def put(df, name, widths=None, wrapcols=()):
            df.to_excel(xw, sheet_name=name, index=False)
            ws = xw.sheets[name]
            for i, c in enumerate(df.columns):
                ws.write(0, i, c, hdr)
                w_ = (widths or {}).get(
                    c,
                    (
                        16
                        if c not in ("comment_id", "video_id", "parent_comment_id")
                        else 28
                    ),
                )
                ws.set_column(i, i, w_, wrap if c in wrapcols else None)
            ws.freeze_panes(1, 1)
            ws.autofilter(0, 0, len(df), len(df.columns) - 1)

        put(
            m,
            "Master",
            {
                "video_title": 34,
                "comment_text": 70,
                "iio_forms": 40,
                "iio_evidence": 50,
                "iio_variables": 30,
                "iio_dimensions": 22,
            },
            ("comment_text", "iio_evidence"),
        )
        put(dictionary, "Data_Dictionary", {"Column": 36, "Meaning": 100})
        for n, d in sh.items():
            put(
                d,
                n,
                {
                    "comment_text": 70,
                    "title": 50,
                    "matched_cues": 30,
                    "evidence_text": 50,
                },
                ("comment_text", "evidence_text"),
            )
    print("Master rows:", len(m), "| columns:", len(m.columns))
    print(
        m.relevance_label.value_counts().to_dict(),
        "| IIO-labelled:",
        int(m.iio_labelled.sum()),
    )
    print("Written:", dst)


if __name__ == "__main__":
    a = sys.argv[1:]
    main(Path(a[0]) if a else DEF_IN, Path(a[1]) if len(a) > 1 else DEF_OUT)
