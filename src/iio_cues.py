"""Preliminary IIO annotation by codebook cue-phrase matching (multi-label).

Usage (project root):
  python -m src.iio_cues config/codebook.json data/processed/relevance_screened.csv
Reads comments with final_label in {relevant, partially_relevant}; writes
data/processed/iio_annotations_long.csv (one row per comment x form) and iio_annotations_wide.csv.
These are automatic, preliminary labels: they must be human-validated before analysis.
"""
import json
import re
import sys
from pathlib import Path

import pandas as pd

STOP = set("the a an to of it i my me he she was is and or in on at by for that this but so you your we our they them his her "
           "be been had has have with as from not no".split())


def stem(w):
    for suf in ("ing", "ed", "es", "s"):
        if len(w) > 4 and w.endswith(suf):
            return w[: -len(suf)]
    return w


def toks(text):
    text = text.lower().replace("’", "'")
    return [stem(t.strip("'")) for t in re.findall(r"[a-z0-9']+", text)]


def load_cues(path):
    cb = json.load(open(path, encoding="utf-8"))
    rows = []
    for dim, variables in cb.items():
        for v in variables:
            for f in v["forms"]:
                for cue in f.get("cue_phrases") or []:
                    ct = [t for t in toks(cue) if t not in STOP]
                    rows.append(dict(dimension=dim, variable=v["element"], form_code=f["code"], form=f["form"],
                                     cue=cue, ctoks=ct, ctoks_all=toks(cue)))
    return rows


def match_conf(cue, tokens):
    """0 = no match; 0.8 exact phrase; 0.5 content words within a window; 0.3 single generic word."""
    ct, ca = cue["ctoks"], cue["ctoks_all"]
    if not ct:
        return 0.0
    if len(ct) == 1:
        return 0.3 if ct[0] in tokens else 0.0
    n = len(ca)
    if any(tokens[i:i + n] == ca for i in range(len(tokens) - n + 1)):
        return 0.8
    pos = [[i for i, t in enumerate(tokens) if t == c] for c in ct]
    if any(not p for p in pos):
        return 0.0
    window = len(ct) + 4
    for start in pos[0]:
        if all(any(abs(i - start) <= window for i in p) for p in pos[1:]):
            return 0.5
    return 0.0


def evidence(text, cue):
    sents = re.split(r"(?<=[.!?\n])\s+", " ".join(text.split()))
    keys = set(cue["ctoks"])
    best = max(sents, key=lambda s: len(keys & set(toks(s))))
    return best[:200]


def annotate(comments, cues):
    out = []
    for _, r in comments.iterrows():
        tokens = toks(r.comment_text)
        found = {}
        for cue in cues:
            c = match_conf(cue, tokens)
            if c:
                found.setdefault(cue["form_code"], []).append((c, cue))
        for code, hits in found.items():
            conf = min(0.95, max(h[0] for h in hits) + 0.1 * (len({h[1]["cue"] for h in hits}) - 1))
            top = max(hits, key=lambda h: h[0])[1]
            out.append(dict(comment_id=r.comment_id, video_id=r.video_id, dimension=top["dimension"],
                            variable=top["variable"], form_code=code, form=top["form"],
                            matched_cues="; ".join(sorted({h[1]["cue"] for h in hits})),
                            evidence_text=evidence(r.comment_text, top), confidence=round(conf, 2),
                            method="cue_match", reviewer_decision=""))
    return pd.DataFrame(out)


def main(codebook, screened_csv):
    s = pd.read_csv(screened_csv, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    s = s[s.final_label.isin(["relevant", "partially_relevant"])]
    long = annotate(s, load_cues(codebook))
    out = Path("data/processed")
    long.to_csv(out / "iio_annotations_long.csv", index=False, encoding="utf-8-sig")
    keep = long[long.confidence >= 0.5]
    wide = keep.pivot_table(index="comment_id", columns="variable", values="confidence", aggfunc="max").notna().astype(int)
    wide.to_csv(out / "iio_annotations_wide.csv", encoding="utf-8-sig")
    print(f"comments screened: {len(s)} | with any cue: {long.comment_id.nunique()} | with conf>=0.5: {keep.comment_id.nunique()}")
    print(keep.groupby(["dimension", "variable"]).comment_id.nunique().to_string())


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
