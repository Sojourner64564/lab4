"""NER: spaCy (ru_core_news_sm) + fallback на transformers."""
import json
import pandas as pd

from config import OUT_DIR, SPACY_LABELS
from eda import load_corpus


def spacy_entities(text: str, nlp) -> list[dict]:
    doc = nlp(text or "")
    return [
        {"text": e.text, "label": SPACY_LABELS.get(e.label_, e.label_), "start": e.start_char, "end": e.end_char}
        for e in doc.ents
    ]


def run_spacy(df: pd.DataFrame) -> pd.DataFrame:
    try:
        import spacy
        nlp = spacy.load("ru_core_news_sm")
    except Exception as e:
        print(f"[NER] spaCy недоступен: {e}")
        return pd.DataFrame()

    rows = []
    for _, r in df.iterrows():
        for ent in spacy_entities(r["full_text"], nlp):
            rows.append({"doc_title": r["title"][:70], "url": r["url"], **ent})
    res = pd.DataFrame(rows)

    print("=== NER (spaCy) ===")
    print(res["label"].value_counts().to_string())
    print("\nТоп-ORG:")
    print(res[res["label"] == "ORG"]["text"].value_counts().head(10).to_string())
    print("\nТоп-PERSON:")
    print(res[res["label"] == "PERSON"]["text"].value_counts().head(10).to_string())

    _BLACKLIST = {"Сделал", "Кедр", "Привет", "Хранение", "Хаброжители",
                  "Typing", "Pyhton", "TypeVar", "local‑doc"}
    res = res[~res["text"].isin(_BLACKLIST)]

    res.to_csv(OUT_DIR / "ner_entities.csv", index=False)

    # Пример из лекции
    demo = "Виктор Петрович основал компанию Яндекс в Москве в 1997 году."
    print("\nДемо:", demo)
    for e in spacy_entities(demo, nlp):
        print(f"  {e['text']:>20} -> {e['label']}")
    return res


def run_transformers(df: pd.DataFrame, model_name="DeepPavlov/rubert-base-cased"):
    """Fallback: NER через HF pipeline. Внимание: требует весов NER-head."""
    try:
        from transformers import pipeline
        nlp = pipeline("ner", model=model_name, tokenizer=model_name,
                       aggregation_strategy="simple")
        demo = "Виктор Петрович основал Яндекс в Москве в 1997 году."
        print("\n=== NER (transformers) ===")
        for e in nlp(demo):
            print(f"  {e['word']:>20} -> {e['entity_group']}")
    except Exception as e:
        print(f"[NER] HF недоступен: {e}")


if __name__ == "__main__":
    df = load_corpus()
    run_spacy(df)
    # run_transformers(df)  # раскомментируйте, если есть ruBERT NER-head