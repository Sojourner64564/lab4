#!/usr/bin/env python
"""Пример 2 (слайды 22-24): кластеризация городов по кулинарным векторам."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans, AgglomerativeClustering, SpectralClustering
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import normalize

from config import OUT_DIR

# Города и их кухни. Для демо — «правдоподобные» данные.
# В проде: скрапинг сайтов по запросу «блюда <город>» (см. scrape_city_dishes ниже).
CITIES_DISHES = {
    "Пермь":        {"посикунчики": 0.9, "пельмени": 0.8, "пистики": 0.6, "шаньги": 0.7,
                     "суп": 0.3, "салат": 0.2, "борщ": 0.1, "плов": 0.1},
    "Кунгур":       {"посикунчики": 0.8, "пельмени": 0.7, "пистики": 0.4, "шаньги": 0.6,
                     "суп": 0.2, "салат": 0.2, "борщ": 0.1, "плов": 0.05},
    "Казань":       {"эчпочмак": 0.9, "беляш": 0.7, "чак-чак": 0.9, "плов": 0.6,
                     "лагман": 0.3, "суп": 0.3, "салат": 0.1, "борщ": 0.05},
    "Уфа":          {"эчпочмак": 0.85, "беляш": 0.6, "чак-чак": 0.8, "плов": 0.5,
                     "лагман": 0.3, "суп": 0.3, "салат": 0.1, "борщ": 0.05},
    "Челябинск":    {"эчпочмак": 0.6, "пельмени": 0.6, "чак-чак": 0.4, "плов": 0.4,
                     "суп": 0.4, "салат": 0.3, "борщ": 0.3, "пицца": 0.1},
    "Самара":       {"эчпочмак": 0.4, "пельмени": 0.4, "чак-чак": 0.3, "плов": 0.3,
                     "суп": 0.4, "салат": 0.3, "борщ": 0.3, "пицца": 0.2},
    "Москва":       {"пицца": 0.7, "суши": 0.7, "борщ": 0.4, "салат": 0.4, "суп": 0.5,
                     "плов": 0.3, "пельмени": 0.2, "эчпочмак": 0.1},
    "СПб":          {"пицца": 0.7, "суши": 0.6, "борщ": 0.4, "салат": 0.4, "суп": 0.5,
                     "плов": 0.3, "пельмени": 0.2, "эчпочмак": 0.1},
    "Петрозаводск": {"калитки": 0.9, "рыбник": 0.7, "уха": 0.8, "шаньги": 0.5,
                     "суп": 0.3, "салат": 0.2, "борщ": 0.1, "плов": 0.05},
    "Хабаровск":    {"уха": 0.6, "суши": 0.5, "пицца": 0.4, "суп": 0.4, "салат": 0.3,
                     "борщ": 0.2, "плов": 0.2, "пельмени": 0.2},
}


def build_matrix():
    cities = list(CITIES_DISHES)
    dishes = sorted({d for v in CITIES_DISHES.values() for d in v})
    X = np.array([[CITIES_DISHES[c].get(d, 0.0) for d in dishes] for c in cities])
    return cities, dishes, normalize(X)


def cluster_all(X, k):
    return {
        "kmeans": KMeans(n_clusters=k, random_state=42, n_init=10).fit_predict(X),
        "hier":   AgglomerativeClustering(n_clusters=k, linkage="ward").fit_predict(X),
        "spectral": SpectralClustering(n_clusters=k, affinity="cosine",
                                       random_state=42, n_init=10).fit_predict(X),
    }


def elbow_silhouette(X, k_range=range(2, 11)):
    inertia, sil = [], []
    for k in k_range:
        km = KMeans(n_clusters=k, random_state=42, n_init=10).fit(X)
        inertia.append(km.inertia_)
        sil.append(silhouette_score(X, km.labels_) if k > 1 else 0.0)
    return list(k_range), inertia, sil


def plot_all(cities, dishes, X, labels, k, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)

    # elbow + silhouette
    ks, inertia, sil = elbow_silhouette(X)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    axes[0].plot(ks, inertia, marker="o"); axes[0].set_title("Метод локтя (inertia)")
    axes[0].set_xlabel("k"); axes[0].set_ylabel("inertia"); axes[0].grid(alpha=0.3)
    axes[0].axvline(k, color="#e6194B", linestyle="--")
    axes[1].plot(ks, sil, marker="o", color="#2ca02c")
    axes[1].set_title("Silhouette score"); axes[1].set_xlabel("k")
    axes[1].set_ylabel("silhouette"); axes[1].grid(alpha=0.3)
    axes[1].axvline(k, color="#e6194B", linestyle="--")
    fig.tight_layout(); fig.savefig(out_dir / "elbow_silhouette.png", dpi=120); plt.close(fig)

    # PCA-визуализация k-means
    from sklearn.decomposition import PCA
    Z = PCA(n_components=2, random_state=42).fit_transform(X)
    fig, ax = plt.subplots(figsize=(10, 6))
    palette = plt.get_cmap("tab10")
    for cl in sorted(set(labels["kmeans"])):
        mask = labels["kmeans"] == cl
        ax.scatter(Z[mask, 0], Z[mask, 1], s=120,
                   color=palette(cl), label=f"кластер {cl}", alpha=0.85)
        for i, c in enumerate(cities):
            if mask[i]:
                ax.annotate(c, (Z[i, 0], Z[i, 1]), fontsize=9,
                            xytext=(5, 5), textcoords="offset points")
    ax.set_title(f"k-means по кулинарным векторам городов: {k} кластера")
    ax.legend(); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(out_dir / "clusters_pca.png", dpi=120); plt.close(fig)


def main(k=3):
    cities, dishes, X = build_matrix()
    print(f"[demo] {len(cities)} городов × {len(dishes)} блюд")
    labels = cluster_all(X, k)

    df = pd.DataFrame({"city": cities, **labels})
    print(df.to_string(index=False))

    # проверка содержательной валидации
    grouped = df.groupby("kmeans")["city"].apply(list).to_dict()
    print("\nКластеры (k-means):")
    for cl, cs in grouped.items():
        print(f"  {cl}: {', '.join(cs)}")

    out = OUT_DIR / "clustering"
    out.mkdir(exist_ok=True)
    df.to_csv(out / "clusters.csv", index=False, encoding="utf-8")
    with open(out / "clusters.json", "w", encoding="utf-8") as f:
        json.dump({str(cl): cs for cl, cs in grouped.items()}, f, ensure_ascii=False, indent=2)
    plot_all(cities, dishes, X, labels, k, out)
    print(f"[save] {out} — clusters.csv, clusters.json, elbow_silhouette.png, clusters_pca.png")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=3)
    main(ap.parse_args().k)


# --- Скрапинг-вариант (опционально) ---
# def scrape_city_dishes(city: str) -> dict:
#     """Возвращает {dish: freq} по запросу 'блюда <city>'."""
#     import requests
#     from bs4 import BeautifulSoup
#     url = f"https://www.google.com/search?q=блюда+{city}"
#     # ... парсинг сниппетов и подсчёт упоминаний блюд ...