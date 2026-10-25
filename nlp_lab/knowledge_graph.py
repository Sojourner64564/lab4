"""Строим граф: узлы = сущности (Q-коды), рёбра = отношения."""
import json
from pathlib import Path

import networkx as nx

from config import OUT_DIR


def build_graph(link_df, rel_df) -> nx.DiGraph:
    G = nx.DiGraph()
    canon = {(r["text"], r["label"]): r for _, r in link_df.iterrows()}
    for (text, label), r in canon.items():
        node_id = r["qid"] if isinstance(r["qid"], str) and r["qid"] else f"{label}:{text}"
        G.add_node(node_id, label=r["canonical"] if isinstance(r["canonical"], str) else text,
                   type=label, qid=r["qid"] if isinstance(r["qid"], str) else None,
                   description=r["description"] if isinstance(r["description"], str) else None)

    for _, r in rel_df.iterrows():
        s = canon.get((r["subject"], r["s_type"]))
        o = canon.get((r["object"], r["o_type"]))
        if s is None or o is None:      # ← фикс
            continue
        s_id = s["qid"] if isinstance(s["qid"], str) and s["qid"] else f"{r['s_type']}:{r['subject']}"
        o_id = o["qid"] if isinstance(o["qid"], str) and o["qid"] else f"{r['o_type']}:{r['object']}"
        if s_id == o_id:                # не добавляем петли
            continue
        G.add_edge(s_id, o_id, relation=r["relation"])
    return G


def export_json(G: nx.DiGraph, path: Path) -> None:
    data = {
        "nodes": [
            {"id": n, **{k: v for k, v in d.items() if v is not None}}
            for n, d in G.nodes(data=True)
        ],
        "edges": [
            {"source": u, "target": v, "relation": d.get("relation")}
            for u, v, d in G.edges(data=True)
        ],
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def export_pyvis(G: nx.DiGraph, path: Path) -> None:
    """Интерактивный HTML-граф (для отчёта/stakeholders)."""
    try:
        from pyvis.network import Network
        net = Network(height="700px", width="100%", directed=True, bgcolor="#fff",
                      font_color="#222")
        colors = {"PERSON": "#e6194B", "ORG": "#3cb44b", "GPE": "#4363d8",
                  "LOC": "#911eb4", "PRODUCT": "#f58231"}
        for n, d in G.nodes(data=True):
            net.add_node(n, label=d.get("label", n), title=d.get("description", ""),
                         color=colors.get(d.get("type"), "#999999"))
        for u, v, d in G.edges(data=True):
            net.add_edge(u, v, label=d.get("relation", ""))
        net.write_html(str(path), notebook=False)
    except Exception as e:
        print(f"[KG] pyvis недоступен: {e}")


def demo() -> None:
    """Демо из лекции (стр. 19)."""
    G = nx.DiGraph()
    G.add_edge("Q937", "Q3008", relation="born_in")
    G.add_edge("Q937", "1879", relation="born_in_year")
    G.add_edge("Q3008", "Q183", relation="located_in")
    G.add_edge("Q937", "Q21643", relation="worked_at")
    export_json(G, OUT_DIR / "kg_demo.json")
    export_pyvis(G, OUT_DIR / "kg_demo.html")
    print("Демо-граф: Einstein -> Ulm -> Germany, Princeton, 1879")


if __name__ == "__main__":
    import pandas as pd
    link_f = OUT_DIR / "entity_linking.csv"
    rel_f = OUT_DIR / "relations.csv"
    if link_f.exists() and rel_f.exists():
        G = build_graph(pd.read_csv(link_f), pd.read_csv(rel_f))
        export_json(G, OUT_DIR / "knowledge_graph.json")
        export_pyvis(G, OUT_DIR / "knowledge_graph.html")
        print(f"Граф: {G.number_of_nodes()} узлов, {G.number_of_edges()} рёбер")
    else:
        print("Сначала запустите ner_extract.py и relation_extract.py")
    demo()