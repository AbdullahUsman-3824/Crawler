"""Sentiment (VADER) and dictionary-based emotion flags for screened English comments.

Usage: python -m src.sentiment_emotion data/processed/relevance_screened.csv
Output: data/processed/sentiment_emotion.csv  (needs: pip install vaderSentiment)
Emotion flags are a simple lexicon approximation, not a trained emotion model.
"""
import re
import sys

import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

EMOTIONS = {
    "fear": r"scar\w*|afraid|fear\w*|terrif\w*|panic\w*|worr\w*|anxi\w*|creepy|dangerous|threat\w*|paranoi\w*|nightmare",
    "anger": r"angry|anger|furious|rage|hate|disgust\w*|despicable|evil|scum|monsters?|animals?|criminals?|bastards?|idiots?|stupid|outrag\w*",
    "sadness": r"sad|heartbreak\w*|heartbroken|devastat\w*|cry\w*|tears|depress\w*|sorry|pity|tragic|grief|lost everything|hopeless",
    "shame": r"asham\w*|embarrass\w*|guilt\w*|stupid of me|fool(ed)?|gullible|naive",
    "trust_gratitude": r"thank\w*|grateful|appreciat\w*|helpful|useful|informative|trust\w*|safe|protect\w*",
    "surprise": r"wow|omg|shock\w*|unbelievable|can'?t believe|crazy|insane|wtf|whoa",
    "urgency_loss": r"urgent\w*|immediately|right now|lost|stolen|drained|emptied|gone|wiped",
}
EM_RE = {k: re.compile(r"\b(" + v + r")\b", re.I) for k, v in EMOTIONS.items()}


def main(path):
    s = pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    s = s[s.final_label.isin(["relevant", "partially_relevant"])].copy()
    an = SentimentIntensityAnalyzer()
    s["compound"] = s.comment_text.map(lambda t: an.polarity_scores(t)["compound"])
    s["sentiment"] = pd.cut(s.compound, [-1.01, -0.05, 0.05, 1.01], labels=["negative", "neutral", "positive"]).astype(str)
    for k, rx in EM_RE.items():
        s["emo_" + k] = s.comment_text.map(lambda t: int(bool(rx.search(t))))
    cols = ["comment_id", "video_id", "final_label", "compound", "sentiment"] + ["emo_" + k for k in EMOTIONS]
    s[cols].to_csv("data/processed/sentiment_emotion.csv", index=False, encoding="utf-8-sig")
    print(s.sentiment.value_counts(normalize=True).round(3).to_string())
    print(s.groupby("final_label")[["compound"] + ["emo_" + k for k in EMOTIONS]].mean().round(3).T.to_string())


if __name__ == "__main__":
    main(sys.argv[1])
