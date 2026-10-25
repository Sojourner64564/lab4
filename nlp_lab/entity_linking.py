import time
from functools import lru_cache

import requests

from config import USER_AGENT, WIKIDATA_API, OUT_DIR

_HEADERS = {"User-Agent": USER_AGENT, "Accept": "application/json"}


@lru_cache(maxsize=256)
def search_entity(name: str, lang: str = "ru") -> dict | None:
    params = {
        "action": "wbsearchentities",
        "search": name,
        "language": lang,
        "uselang": lang,
        "format": "json",
        "limit": 3,
    }
    for attempt in range(4):
        try:
            r = requests.get(WIKIDATA_API, params=params, headers=_HEADERS, timeout=15)
            if r.status_code == 429:
                wait = 2 ** attempt
                print(f"[EL] 429 для '{name}', ждём {wait}s")
                time.sleep(wait)
                continue
            r.raise_for_status()
            hits = r.json().get("search", [])
            if not hits:
                return None
            h = hits[0]
            return {"qid": h["id"], "label": h.get("label"), "description": h.get("description")}
        except requests.RequestException as e:
            print(f"[EL] {name}: {e}")
            time.sleep(2)
    return None


def link_entities(ner_df):
    import pandas as pd
    rows = []
    for _, r in ner_df[ner_df["label"].isin(["ORG", "PERSON", "GPE", "LOC", "PRODUCT"])].iterrows():
        hit = search_entity(r["text"])
        rows.append({
            "text": r["text"], "label": r["label"],
            "qid": hit["qid"] if hit else None,
            "canonical": hit["label"] if hit else None,
            "description": hit["description"] if hit else None,
        })
        time.sleep(1.0)  # вежливость: 1 запрос/сек
    res = pd.DataFrame(rows).drop_duplicates(subset=["text", "label"])
    print("=== Entity Linking ===")
    print(res.to_string(index=False))
    res.to_csv(OUT_DIR / "entity_linking.csv", index=False)
    return res