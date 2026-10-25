"""Rule-based RE: (Subject, relation, Object) между сущностями в предложении."""
import re
import pandas as pd

from config import OUT_DIR
from eda import load_corpus

# Паттерны: глагол/предлог между двумя сущностями
# _REL_PATTERNS = [
#     (r"основал\w*", "founded"),
#     (r"создал\w*", "created"),
#     (r"разработал\w*", "developed"),
#     (r"работает в", "works_for"),
#     (r"находится в", "is_located_in"),
#     (r"написал\w*", "authored"),
#     (r"выпустил\w*", "released"),
#     (r"купил\w*", "acquired"),
# ]
_REL_PATTERNS = [
    (r"основал\w*", "founded"),
    (r"создал\w*", "created"),
    (r"разработал\w*", "developed"),
    (r"работает (на|в)", "works_for"),
    (r"находится в", "is_located_in"),
    (r"написал\w*", "authored"),
    (r"выпустил\w*", "released"),
    (r"купил\w*", "acquired"),
    (r"написан\w* (на|в)", "written_in"),
    (r"использует\w*", "uses"),
    (r"входит в", "part_of"),
    (r"позволяет", "allows"),
    (r"преврат\w* в", "transforms_to"),
    (r"связан\w* с", "related_to"),
]

def extract_relations(text: str, entities: list[dict]) -> list[dict]:
    """Ищем пары сущностей внутри одного предложения + паттерн между ними."""
    sents = re.split(r"(?<=[.!?])\s+", text or "")
    out = []
    for sent in sents:
        sent_ents = [e for e in entities if sent.find(e["text"]) >= 0]
        for i, e1 in enumerate(sent_ents):
            for e2 in sent_ents[i + 1:]:
                between = sent[e1["end"]:e2["start"]] if e1["end"] < e2["start"] else ""
                for pattern, rel in _REL_PATTERNS:
                    if re.search(pattern, between, re.IGNORECASE):
                        out.append({"subject": e1["text"], "s_type": e1["label"],
                                    "relation": rel,
                                    "object": e2["text"], "o_type": e2["label"],
                                    "sentence": sent.strip()[:200]})
    return out


def run(df: pd.DataFrame, ner_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in df.iterrows():
        ents = ner_df[ner_df["url"] == r["url"]].to_dict("records")
        for rel in extract_relations(r["full_text"], ents):
            rel["doc_title"] = r["title"][:70]
            rel["url"] = r["url"]
            rows.append(rel)
    res = pd.DataFrame(rows)
    print("=== Relation Extraction ===")
    if res.empty:
        print("Отношений не найдено (нужен более крупный корпус).")
    else:
        print(res[["subject", "relation", "object"]].to_string(index=False))
    res.to_csv(OUT_DIR / "relations.csv", index=False)
    return res


if __name__ == "__main__":
    from ner_extract import run_spacy
    df = load_corpus()
    ner_df = run_spacy(df)
    run(df, ner_df)