from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "output"
OUT_DIR.mkdir(exist_ok=True)

INPUT_JSON = DATA_DIR / "news_python.json"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
USER_AGENT = "NLP-Lab5/1.0 (educational; student@example.com)"
# Типы сущностей spaCy -> канонические
SPACY_LABELS = {
    "PER": "PERSON", "PERSON": "PERSON",
    "ORG": "ORG",
    "LOC": "LOC", "GPE": "GPE",
    "DATE": "DATE",
    "PRODUCT": "PRODUCT",
    "EVENT": "EVENT",
}