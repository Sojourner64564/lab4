"""Sentiment: VADER + transformers (fallback)."""
import json
import pandas as pd

from config import OUT_DIR
from eda import load_corpus

try:
    from nltk.sentiment import SentimentIntensityAnalyzer
    _sia = SentimentIntensityAnalyzer()
except Exception:
    _sia = None

_LABEL = {True: "positive", False: "negative"}


def vader_scores(text: str) -> dict:
    if _sia is None:
        return {"neg": 0.0, "neu": 1.0, "pos": 0.0, "compound": 0.0}
    return _sia.polarity_scores(text or "")


def classify(compound: float) -> str:
    if compound >= 0.05:
        return "positive"
    if compound <= -0.05:
        return "negative"
    return "neutral"


def analyze(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in df.iterrows():
        s = vader_scores(r["full_text"])
        rows.append({
            "title": r["title"][:70],
            "compound": round(s["compound"], 3),
            "pos": round(s["pos"], 3),
            "neg": round(s["neg"], 3),
            "label": classify(s["compound"]),
        })
    res = pd.DataFrame(rows)
    print("=== Sentiment (VADER) ===")
    print(res["label"].value_counts().to_string())
    print("\nПримеры:")
    for _, r in res.sort_values("compound").head(3).iterrows():
        print(f"  [neg] {r['title']}  compound={r['compound']}")
    for _, r in res.sort_values("compound", ascending=False).head(3).iterrows():
        print(f"  [pos] {r['title']}  compound={r['compound']}")
    res.to_csv(OUT_DIR / "sentiment.csv", index=False)
    return res


def analyze_transformers(df: pd.DataFrame, model_name="cointegrated/rubert-tiny2-cedr-emotion-detection"):
    """Опционально: русский ruBERT для эмоций/тональности."""
    try:
        from transformers import pipeline
        clf = pipeline("text-classification", model=model_name, top_k=1)
        texts = df["full_text"].str.slice(0, 400).tolist()
        return pd.DataFrame({
            "title": df["title"],
            "label": [r["label"] for r in clf(texts)],
            "score": [round(r["score"], 3) for r in clf(texts)],
        })
    except Exception as e:
        print(f"[sentiment] трансформеры недоступны: {e}")
        return None


if __name__ == "__main__":
    analyze(load_corpus())