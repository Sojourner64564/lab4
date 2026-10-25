"""EDA текстового корпуса: количественные метрики, wordcloud, n-граммы."""
import json
import re
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from nltk.corpus import stopwords
from wordcloud import WordCloud

from config import INPUT_JSON, OUT_DIR

_STOPWORDS = set(stopwords.words("russian")) | {"это", "который", "также", "уже", "ещё", "весь", "свой"}
_WORD = re.compile(r"[A-Za-zА-Яа-яЁё]+")


def load_corpus(path=INPUT_JSON) -> pd.DataFrame:
    with open(path, encoding="utf-8") as f:
        rows = json.load(f)
    df = pd.DataFrame(rows)
    df["full_text"] = (df["title"].fillna("") + " " + df["summary"].fillna("")).str.strip()
    return df


def tokenize(text: str) -> list[str]:
    return [w.lower() for w in _WORD.findall(text or "") if w.lower() not in _STOPWORDS and len(w) > 2]


def quantitative_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Длина, слово-счёт, средняя длина слова, доля уникальных."""
    df = df.copy()
    df["n_chars"] = df["full_text"].str.len()
    tokens = df["full_text"].map(tokenize)
    df["n_words"] = tokens.map(len)
    df["avg_word_len"] = tokens.map(lambda t: round(sum(len(w) for w in t) / len(t), 2) if t else 0.0)
    df["uniq_ratio"] = tokens.map(lambda t: round(len(set(t)) / len(t), 3) if t else 0.0)
    cols = ["title", "n_chars", "n_words", "avg_word_len", "uniq_ratio"]
    return df[cols]


def plot_distributions(df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    sns.histplot(df["n_words"], bins=15, ax=axes[0]).set(title="Слов в документе")
    sns.histplot(df["avg_word_len"], bins=15, ax=axes[1]).set(title="Средняя длина слова")
    sns.boxplot(y=df["uniq_ratio"], ax=axes[2]).set(title="Лексическое разнообразие")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "eda_distributions.png", dpi=120)
    plt.close(fig)


def make_wordcloud(df: pd.DataFrame, name="wordcloud.png") -> None:
    text = " ".join(" ".join(tokenize(t)) for t in df["full_text"])
    wc = WordCloud(width=1200, height=600, background_color="white",
                   colormap="viridis", max_words=200).generate(text)
    plt.figure(figsize=(12, 6))
    plt.imshow(wc, interpolation="bilinear")
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(OUT_DIR / name, dpi=120)
    plt.close()


def top_ngrams(df: pd.DataFrame, n=2, top_k=20) -> list[tuple[str, int]]:
    counter = Counter()
    for text in df["full_text"]:
        toks = tokenize(text)
        counter.update(" ".join(toks[i:i + n]) for i in range(len(toks) - n + 1))
    return counter.most_common(top_k)


def report(df: pd.DataFrame) -> dict:
    met = quantitative_metrics(df)
    report = {
        "documents": len(df),
        "mean_words": round(met["n_words"].mean(), 2),
        "median_words": round(met["n_words"].median(), 2),
        "min_words": int(met["n_words"].min()),
        "max_words": int(met["n_words"].max()),
        "mean_uniq_ratio": round(met["uniq_ratio"].mean(), 3),
    }
    print("=== EDA ===")
    for k, v in report.items():
        print(f"{k:>18}: {v}")
    print("\nТоп-биграммы:", top_ngrams(df, 2, 10))
    print("Топ-триграммы:", top_ngrams(df, 3, 10))
    plot_distributions(met)
    make_wordcloud(df)
    met.sort_values("n_words", ascending=False).to_csv(OUT_DIR / "eda_metrics.csv", index=False)
    return report


if __name__ == "__main__":
    report(load_corpus())