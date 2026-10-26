## Практика 5: тематическое моделирование и кластерный анализ

### Установка
    pip install gensim pyLDAvis

### Запуск
    # 1) расширить корпус (в корне lab4)
    python run_spider.py --spider news --keywords "python,данные,ML" --days 60 --limit 300 --output nlp_lab\data\news_big.json
    python run_spider.py --spider ecommerce --category "ноутбуки" --limit 300 --output nlp_lab\data\products_big.json

    # 2) тематическое моделирование
    cd nlp_lab
    python topic_modeling.py --dataset news --method lda --topics auto --output news_topics
    python topic_modeling.py --dataset products --method nmf --topics 15 --output products_topics
    python topic_modeling.py --dataset mixed --method both --topics 10 --compare

    # 3) кластеризация городов (Пример 2)
    python clustering_demo.py --k 3

### Артефакты
| Файл | Что показывает |
|---|---|
| output/news_topics/top_words.png | топ-10 слов по топикам (plot_top_words) |
| output/news_topics/coherence.png | K vs coherence (c_v), оптимум |
| output/news_topics/doc_topic.csv | матрица «документ — топик» |
| output/news_topics/topic_words.json | ключевые слова с весами |
| output/news_topics/wordclouds/ | облака слов по топикам |
| output/comparison/ | LDA vs NMF (coherence, K) |
| output/clustering/elbow_silhouette.png | метод локтя + silhouette |
| output/clustering/clusters_pca.png | 2D PCA городов по кластерам |

### Ограничения
- LDA обучается на CountVectorizer, NMF — на TF-IDF (важно, слайд 19).
- На корпусе <200 документов топики «слипаются» — нужно ≥200 (лучше 500+).
- `--topics auto` перебирает K=3..20 — на больших корпусах медленно (~5-10 мин).