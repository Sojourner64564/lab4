"""Визуализации для тематического моделирования (слайды 12, 16, 19-21)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def plot_top_words(model, feature_names, n_top_words, title, out_path):
    """Слайд 20: сетка 2x5 bar-chart'ов топ-слов по топикам."""
    n_topics = model.components_.shape[0]
    n_cols = 5
    n_rows = (n_topics + n_cols - 1) // n_cols
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(30, 6 * n_rows), sharex=False)
    axes = axes.flatten()
    for topic_idx, topic in enumerate(model.components_):
        top_idx = topic.argsort()[:-n_top_words - 1:-1]
        top_words = [feature_names[i] for i in top_idx]
        weights = topic[top_idx]
        ax = axes[topic_idx]
        ax.barh(top_words, weights, height=0.7, color="#0b3d91")
        ax.set_title(f"Topic {topic_idx + 1}", fontdict={"fontsize": 18})
        ax.invert_yaxis()
        ax.tick_params(axis="y", labelsize=10)
    for ax in axes[n_topics:]:
        ax.axis("off")
    plt.subplots_adjust(top=0.93, bottom=0.05, wspace=0.6, hspace=0.3)
    plt.suptitle(title, fontsize=22)
    fig.savefig(out_path, dpi=110, bbox_inches="tight")
    plt.close(fig)


def plot_coherence(k_values, scores, best_k, title, out_path):
    """Слайд 16: K vs coherence, вертикальная линия на оптимуме."""
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(k_values, scores, marker="o", color="#1f77b4", linewidth=2)
    ax.axvline(best_k, color="#e6194B", linestyle="--", label=f"оптимум K={best_k}")
    ax.set_xlabel("число топиков K")
    ax.set_ylabel("coherence score (c_v)")
    ax.set_title(title)
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def plot_doc_topic(doc_topic, titles, out_path, max_docs=15):
    """Слайд 12: stacked bar — доля каждой темы в документе."""
    n_topics = doc_topic.shape[1]
    idx = np.arange(min(len(doc_topic), max_docs))
    fig, ax = plt.subplots(figsize=(14, 6))
    bottom = np.zeros(len(idx))
    cmap = plt.get_cmap("tab20")
    for t in range(n_topics):
        vals = doc_topic[idx, t]
        ax.bar(idx, vals, bottom=bottom, label=f"T{t + 1}", color=cmap(t % 20))
        bottom += vals
    ax.set_xticks(idx)
    labels = [t[:30] for t in titles[: len(idx)]]
    ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=8)
    ax.set_ylabel("доля топика в документе")
    ax.set_title("Матрица «документ — топик»")
    ax.legend(ncol=min(n_topics, 10), fontsize=8, loc="upper right")
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def plot_wordclouds(topic_terms, out_dir):
    """Опционально (слайд 17): облако слов на каждый топик."""
    from wordcloud import WordCloud
    from pathlib import Path
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for t_idx, terms in topic_terms.items():
        freq = dict(terms)
        wc = WordCloud(width=800, height=400, background_color="white",
                       colormap="viridis").generate_from_frequencies(freq)
        path = out_dir / f"topic_{t_idx + 1}.png"
        wc.to_file(str(path))