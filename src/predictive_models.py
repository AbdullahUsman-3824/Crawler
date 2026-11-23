"""Relationship analysis and (data permitting) predictive models for the IIO dimensions.

Usage: python -m src.predictive_models [min_conf]   (default 0.5)
Tasks: Issue+Intervention->Outcome, Issue+Outcome->Intervention, Intervention+Outcome->Issue.
Models run only when there are enough comments carrying BOTH the predictor and the target dimension
(>= MIN_N comments, >= MIN_POS positives per target variable). Evaluation: logistic regression with
video-grouped cross-validation (comments from one video never appear in both train and test).
"""
import sys
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

MIN_N, MIN_POS = 60, 10
TASKS = [(("Issue", "Intervention"), "Outcome"), (("Issue", "Outcome"), "Intervention"), (("Intervention", "Outcome"), "Issue")]


def main(min_conf=0.5):
    l = pd.read_csv("data/processed/iio_annotations_long.csv", encoding="utf-8-sig", dtype=str, keep_default_na=False)
    l["confidence"] = l.confidence.astype(float)
    l = l[l.confidence >= min_conf]
    X = l.pivot_table(index="comment_id", columns="variable", values="confidence", aggfunc="max").notna().astype(int)
    dim_of = l.drop_duplicates("variable").set_index("variable").dimension
    vid = l.drop_duplicates("comment_id").set_index("comment_id").video_id
    rows = []
    for preds, target in TASKS:
        pc = [c for c in X.columns if dim_of[c] in preds]
        tc = [c for c in X.columns if dim_of[c] == target]
        # comments with at least one predictor-dimension label and at least one target-dimension label
        any_p = (X[pc].sum(axis=1) > 0) & (X[tc].sum(axis=1) > 0)
        n = int(any_p.sum())
        name = " + ".join(preds) + " -> " + target
        if n < MIN_N:
            rows.append(dict(task=name, n_comments=n, status=f"insufficient data (<{MIN_N})", mean_auc=np.nan))
            continue
        d = X[any_p]
        aucs = []
        for t in tc:
            y = d[t].values
            if y.sum() < MIN_POS or (1 - y).sum() < MIN_POS:
                continue
            p = np.zeros(len(d))
            for tr, te in GroupKFold(5).split(d, y, vid[d.index]):
                if y[tr].min() == y[tr].max():
                    p[te] = y[tr].mean(); continue
                p[te] = LogisticRegression(class_weight="balanced", max_iter=500).fit(d.iloc[tr][pc], y[tr]).predict_proba(d.iloc[te][pc])[:, 1]
            aucs.append(roc_auc_score(y, p))
        rows.append(dict(task=name, n_comments=n, status=f"{len(aucs)} targets modelled", mean_auc=round(float(np.mean(aucs)), 2) if aucs else np.nan))
    res = pd.DataFrame(rows)
    res.to_csv("data/processed/predictive_feasibility.csv", index=False)
    print(res.to_string(index=False))
    # co-occurrence (always reported): how often two variables appear in the same comment
    co = (X.T @ X)
    pairs = [(a, b, int(co.loc[a, b])) for i, a in enumerate(co.index) for b in co.index[i + 1:] if dim_of[a] != dim_of[b] and co.loc[a, b] > 0]
    pd.DataFrame(pairs, columns=["variable_a", "variable_b", "comments_together"]).sort_values("comments_together", ascending=False) \
        .to_csv("data/processed/iio_cooccurrence.csv", index=False)
    print(f"\n{len(pairs)} cross-dimension variable pairs co-occur; top:")
    print(pd.DataFrame(pairs, columns=["a", "b", "n"]).sort_values("n", ascending=False).head(6).to_string(index=False))


if __name__ == "__main__":
    main(float(sys.argv[1]) if len(sys.argv) > 1 else 0.5)
