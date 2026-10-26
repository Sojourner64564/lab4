#!/usr/bin/env python
"""Тематическое моделирование веб-данных: LDA, NMF, coherence, сравнение.

Примеры:
    python topic_modeling.py --dataset news --method lda --topics auto --output news_topics
    python topic_modeling.py --dataset products --method nmf --topics 15 --output product_categories
    python topic_modeling.py --dataset mixed --method both --topics 10 --compare
"""
import argparse
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from nltk.corpus import stopwords
from sklearn.decomposition import NMF, LatentDirichletAllocation
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer

from config import OUT_DIR, DATA_DIR
from topic_viz import plot_top_words, plot_coherence, plot_doc_topic, plot_wordclouds

try:
    import pymorphy3
    _morph = pymorphy3.MorphAnalyzer()
except Exception:
    _morph = None

try:
    from gensim import corpora, models
    from gensim.models.coherencemodel import CoherenceModel
    _GENSIM = True
except Exception:
    _GENSIM = False

_WORD = re.compile(r"[A-Za-zА-Яа-яЁё]{3,}")
_STOP = set(stopwords.words("russian")) | {
    "это", "который", "также", "уже", "ещё", "весь", "свой",
    "который", "которая", "которые", "которых", "можно", "нужно",
}


def lemmatize(text: str) -> str:
    words = _WORD.findall((text or "").lower())
    out = []
    for w in words:
        if w in _STOP:
            continue
        lemma = _morph.parse(w)[0].normal_form if _morph else w
        if lemma in _STOP or len(lemma) < 3:
            continue
        out.append(lemma)
    return " ".join(out)


def load_dataset(name: str) -> pd.DataFrame:
    """news / products / mixed -> DataFrame с колонкой 'text'."""
    files = {
        "news": [DATA_DIR / "news_big.json", DATA_DIR / "news_python.json"],
        "products": [DATA_DIR / "products_big.json"],
    }
    if name == "mixed":
        paths = files["news"] + files["products"]
    else:
        paths = files[name]

    rows = []
    for p in paths:
        if not p.exists():
            print(f"[dataset] пропуск {p} — файла нет")
            continue
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        for d in data:
            text = " ".join(str(d.get(k) or "") for k in ("title", "summary"))
            if not text.strip():
                continue
            rows.append({"source": d.get("source") or d.get("store"),
                         "title": d.get("title"), "text": text.strip()})
    df = pd.DataFrame(rows)
    print(f"[dataset] {name}: {len(df)} документов")
    return df


def prepare_texts(df: pd.DataFrame) -> list[str]:
    return [lemmatize(t) for t in df["text"]]


def fit_lda_gensim(texts, k, passes=10):
    tokenized = [t.split() for t in texts if t]
    dictionary = corpora.Dictionary(tokenized)
    dictionary.filter_extremes(no_below=2, no_above=0.8)
    corpus = [dictionary.doc2bow(t) for t in tokenized]
    model = models.LdaModel(corpus=corpus, id2word=dictionary,
                            num_topics=k, passes=passes, random_state=42)
    topics = [[w for w, _ in model.show_topic(i, topn=10)] for i in range(k)]
    return model, dictionary, corpus, topics


def fit_nmf_sklearn(texts, k):
    vec = TfidfVectorizer(ngram_range=(1, 1), max_features=2000, min_df=2, max_df=0.8)
    X = vec.fit_transform(texts)
    model = NMF(n_components=k, random_state=42, init="nndsvd", max_iter=300)
    model.fit(X)
    feature_names = vec.get_feature_names_out()
    topics = [[feature_names[i] for i in topic.argsort()[::-1][:10]]
              for topic in model.components_]
    return model, feature_names, X, topics


def fit_lda_sklearn(texts, k):
    """LDA через sklearn — для plot_top_words и doc-topic matrix."""
    vec = CountVectorizer(ngram_range=(1, 1), max_features=2000, min_df=2, max_df=0.8)
    X = vec.fit_transform(texts)
    model = LatentDirichletAllocation(n_components=k, random_state=42,
                                      learning_method="batch", max_iter=20)
    model.fit(X)
    feature_names = vec.get_feature_names_out()
    topics = [[feature_names[i] for i in topic.argsort()[::-1][:10]]
              for topic in model.components_]
    return model, feature_names, X, topics


def compute_coherence(texts, topics):
    if not _GENSIM:
        return 0.0
    tokenized = [t.split() for t in texts if t]
    dictionary = corpora.Dictionary(tokenized)
    cm = CoherenceModel(topics=topics, texts=tokenized,
                        dictionary=dictionary, coherence="c_v")
    return float(cm.get_coherence())


def pick_best_k(texts, method, k_range=range(3, 21)):
    scores = {}
    for k in k_range:
        try:
            if method == "lda":
                _, _, _, topics = fit_lda_sklearn(texts, k)
            else:
                _, _, _, topics = fit_nmf_sklearn(texts, k)
            scores[k] = compute_coherence(texts, topics)
            print(f"  K={k:>2}: coherence={scores[k]:.4f}")
        except Exception as e:
            print(f"  K={k}: ошибка {e}")
            scores[k] = 0.0
    best_k = max(scores, key=scores.get)
    return best_k, scores


def topic_terms_json(topics, model=None, feature_names=None):
    """Возвращает {topic_id: [(word, weight), ...]}."""
    result = {}
    if model is not None and feature_names is not None:
        for t_idx, comp in enumerate(model.components_):
            top = comp.argsort()[::-1][:10]
            result[t_idx] = [(str(feature_names[i]), float(comp[i])) for i in top]
    else:
        for t_idx, words in enumerate(topics):
            result[t_idx] = [(w, 1.0 / (i + 1)) for i, w in enumerate(words)]
    return result


def doc_topic_matrix(model, X):
    return model.transform(X)


def save_outputs(out_prefix, df, model, feature_names, X, topics, k, method,
                 coherence_scores, doc_topic, best_k=None):
    out_dir = OUT_DIR / out_prefix
    out_dir.mkdir(parents=True, exist_ok=True)

    plot_top_words(model, feature_names, 10,
                   f"{method.upper()}, K={k}", out_dir / "top_words.png")

    if coherence_scores:
        ks = sorted(coherence_scores)
        scores = [coherence_scores[c] for c in ks]
        plot_coherence(ks, scores, best_k or k,
                       f"{method.upper()}: выбор K по coherence",
                       out_dir / "coherence.png")

    if doc_topic is not None:
        dt_df = pd.DataFrame(doc_topic, columns=[f"T{i + 1}" for i in range(doc_topic.shape[1])])
        dt_df.insert(0, "title", df["title"].values[: len(dt_df)])
        dt_df.to_csv(out_dir / "doc_topic.csv", index=False, encoding="utf-8")
        plot_doc_topic(doc_topic, df["title"].astype(str).tolist(),
                       out_dir / "doc_topic.png")

    terms = topic_terms_json(topics, model, feature_names)
    with open(out_dir / "topic_words.json", "w", encoding="utf-8") as f:
        json.dump({str(k_): v for k_, v in terms.items()}, f, ensure_ascii=False, indent=2)

    plot_wordclouds(terms, out_dir / "wordclouds")
    print(f"[save] {out_dir} — top_words.png, coherence.png, doc_topic.csv, topic_words.json, wordclouds/")


def run_method(method, texts, df, k, auto):
    if auto:
        print(f"[{method.upper()}] подбор K по coherence, диапазон 3..20")
        best_k, scores = pick_best_k(texts, method)
        k = best_k
        print(f"[{method.upper()}] оптимум K={k}, coherence={scores[k]:.4f}")
    else:
        scores = {}

    print(f"[{method.upper()}] обучение, K={k}")
    if method == "lda":
        model, feature_names, X, topics = fit_lda_sklearn(texts, k)
    else:
        model, feature_names, X, topics = fit_nmf_sklearn(texts, k)

    if not scores:
        scores = {k: compute_coherence(texts, topics)}

    doc_topic = doc_topic_matrix(model, X)
    return model, feature_names, X, topics, k, scores, doc_topic


def compare_models(texts, df, k):
    results = {}
    for method in ("lda", "nmf"):
        m, fn, X, topics, kk, scores, dt = run_method(method, texts, df, k, auto=False)
        results[method] = {"coherence": scores[kk], "topics": topics, "k": kk}
        save_outputs(f"comparison_{method}", df, m, fn, X, topics, kk, method,
                     scores, dt)
    print("\n=== Сравнение LDA vs NMF ===")
    for m, r in results.items():
        print(f"{m.upper():>4}: K={r['k']}, coherence={r['coherence']:.4f}")
    (OUT_DIR / "comparison").mkdir(parents=True, exist_ok=True)   # ← добавить
    with open(OUT_DIR / "comparison" / "comparison.json", "w", encoding="utf-8") as f:
        json.dump({m: {"k": r["k"], "coherence": r["coherence"]} for m, r in results.items()},
                  f, ensure_ascii=False, indent=2)
    return results


def main():
    p = argparse.ArgumentParser(description="Topic modeling (LDA / NMF / both)")
    p.add_argument("--dataset", required=True, choices=["news", "products", "mixed"])
    p.add_argument("--method", default="lda", choices=["lda", "nmf", "both"])
    p.add_argument("--topics", default="auto", help="число K или 'auto'")
    p.add_argument("--compare", action="store_true", help="сравнить LDA и NMF")
    p.add_argument("--output", required=True, help="префикс каталога в output/")
    args = p.parse_args()

    df = load_dataset(args.dataset)
    if len(df) < 50:
        print(f"[warn] {len(df)} документов — слишком мало для стабильных топиков. "
              "Перезапустите ЛР4 с --limit 300.")
    texts = prepare_texts(df)
    texts = [t for t in texts if t.strip()]
    print(f"[prep] после лемматизации: {len(texts)} текстов")

    if args.compare or args.method == "both":
        k = int(args.topics) if args.topics.isdigit() else 10
        compare_models(texts, df, k)
        return

    auto = args.topics == "auto"
    k = int(args.topics) if not auto else 10
    model, feature_names, X, topics, k, scores, doc_topic = run_method(
        args.method, texts, df, k, auto)
    save_outputs(args.output, df, model, feature_names, X, topics, k,
                 args.method, scores, doc_topic,
                 best_k=k if auto else None)


if __name__ == "__main__":
    main()