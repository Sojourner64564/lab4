"""Векторизация: BoW, TF-IDF, n-граммы, top-термины по документам."""
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer

from config import OUT_DIR
from eda import load_corpus


def bow_top(texts, ngram=(1, 1), top_k=15):
    vec = CountVectorizer(ngram_range=ngram, max_df=0.8, min_df=1)
    X = vec.fit_transform(texts)
    sum_words = X.sum(axis=0).A1
    vocab = vec.get_feature_names_out()
    return sorted(zip(vocab, sum_words), key=lambda t: -t[1])[:top_k]


def tfidf_per_doc(texts, titles, ngram=(1, 1), top_k=5):
    vec = TfidfVectorizer(ngram_range=ngram, max_df=0.8, min_df=1, sublinear_tf=True)
    X = vec.fit_transform(texts)
    vocab = vec.get_feature_names_out()
    rows = []
    for i, title in enumerate(titles):
        row = X[i].toarray().ravel()
        idx = row.argsort()[::-1][:top_k]
        rows.append({
            "title": title[:60],
            "top_terms": ", ".join(f"{vocab[j]} ({row[j]:.2f})" for j in idx if row[j] > 0),
        })
    return pd.DataFrame(rows)


def demo(df: pd.DataFrame) -> pd.DataFrame:
    texts = df["full_text"].tolist()
    print("=== BoW: топ-слова ===")
    for w, c in bow_top(texts):
        print(f"  {w:>20}: {c}")
    print("\n=== TF-IDF: топ-биграммы корпуса ===")
    for w, s in bow_top(texts, ngram=(2, 2))[:10]:
        print(f"  {w:>25}: {s:.2f}")
    res = tfidf_per_doc(texts, df["title"].tolist())
    print("\n=== TF-IDF: топ-термы документа ===")
    for _, r in res.head(5).iterrows():
        print(f"  {r['title']}\n    -> {r['top_terms']}")
    res.to_csv(OUT_DIR / "tfidf_per_doc.csv", index=False)
    return res


if __name__ == "__main__":
    demo(load_corpus())