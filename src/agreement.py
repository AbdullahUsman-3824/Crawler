"""Inter-rater agreement for the relevance pilot.

Usage (from project root):
  python -m src.agreement annotations/relevance_pilot_v1.csv annotations/annotator_B_done.csv
"""
import sys
import pandas as pd

LABELS = ["relevance_label", "context_type"]


def kappa(a, b):
    n = len(a)
    cats = sorted(set(a) | set(b))
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.tolist().count(c) / n) * (b.tolist().count(c) / n) for c in cats)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0, po


def main(path_a, path_b):
    a = pd.read_csv(path_a, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    b = pd.read_csv(path_b, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    b = b[["comment_id", "relevance_label", "context_type", "reason"]]
    m = b.merge(a, on="comment_id", suffixes=("_B", "_A"))
    print(f"Comments compared: {len(m)}")
    for col in LABELS:
        k, po = kappa(m[col + "_A"], m[col + "_B"])
        print(f"{col}: agreement {po:.1%}, Cohen's kappa {k:.2f}")
    # relevant+partial vs irrelevant/uncertain
    bin_ = lambda s: s.isin(["relevant", "partially_relevant"]).map({True: "keep", False: "drop"})
    k, po = kappa(bin_(m.relevance_label_A), bin_(m.relevance_label_B))
    print(f"keep(relevant+partial) vs drop: agreement {po:.1%}, kappa {k:.2f}")
    print("\nConfusion (rows = A, cols = B):")
    print(pd.crosstab(m.relevance_label_A, m.relevance_label_B))
    diff = m[(m.relevance_label_A != m.relevance_label_B) | (m.context_type_A != m.context_type_B)]
    out = diff[["comment_id", "comment_text", "relevance_label_A", "relevance_label_B",
                "context_type_A", "context_type_B", "reason_A", "reason_B"]]
    out.to_csv("annotations/disagreements.csv", index=False, encoding="utf-8-sig")
    n_rel = (m.relevance_label_A != m.relevance_label_B).sum()
    n_ctx = (m.context_type_A != m.context_type_B).sum()
    print(f"\nrelevance disagreements: {n_rel} | context_type disagreements: {n_ctx}")
    print(f"{len(diff)} rows saved to annotations/disagreements.csv")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
