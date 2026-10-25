#!/usr/bin/env python
"""CLI пайплайна ЛР5: EDA -> BoW/TF-IDF -> Sentiment -> NER -> RE -> EL -> KG."""
import argparse
import sys

from eda import load_corpus, report as eda_report
from vectorize import demo as vec_demo
from sentiment import analyze as sent_analyze
from ner_extract import run_spacy as ner_run
from relation_extract import run as rel_run
from entity_linking import link_entities
from knowledge_graph import build_graph, export_json, export_pyvis, demo as kg_demo


def main():
    p = argparse.ArgumentParser(description="NLP Lab5 pipeline")
    p.add_argument("--input", default=None, help="JSON корпуса (по умолчанию data/news_python.json)")
    p.add_argument("--stage", default="all",
                   choices=["all", "eda", "vector", "sentiment", "ner", "re", "el", "kg", "demo"])
    args = p.parse_args()

    if args.input:
        import config
        from pathlib import Path
        config.INPUT_JSON = Path(args.input)

    df = load_corpus()
    print(f"Корпус: {len(df)} документов\n")

    if args.stage in ("all", "eda"):
        eda_report(df); print()
    if args.stage in ("all", "vector"):
        vec_demo(df); print()
    if args.stage in ("all", "sentiment"):
        sent_analyze(df); print()

    ner_df = None
    if args.stage in ("all", "ner", "re", "el", "kg"):
        ner_df = ner_run(df); print()

    rel_df = None
    if args.stage in ("all", "re") and ner_df is not None and not ner_df.empty:
        rel_df = rel_run(df, ner_df); print()

    link_df = None
    if args.stage in ("all", "el") and ner_df is not None and not ner_df.empty:
        link_df = link_entities(ner_df); print()

    if args.stage in ("all", "kg"):
        if link_df is not None and rel_df is not None and not rel_df.empty:
            G = build_graph(link_df, rel_df)
            export_json(G, __import__("config").OUT_DIR / "knowledge_graph.json")
            export_pyvis(G, __import__("config").OUT_DIR / "knowledge_graph.html")
            print(f"Граф: {G.number_of_nodes()} узлов, {G.number_of_edges()} рёбер")
        kg_demo()

    if args.stage == "demo":
        kg_demo()

    print(f"\nРезультаты: output/")


if __name__ == "__main__":
    main()