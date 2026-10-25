# Лабораторная 5: EDA, NLP и извлечение знаний

Подпапка `nlp_lab/` — анализ корпуса `news_python.json` (собран в ЛР4 пауком `NewsSpider`).

## Установка

```bash
cd nlp_lab
python -m venv venv            # если venv ещё нет (создаётся в корне lab4)
# Windows: ..\venv\Scripts\Activate.ps1
# Linux/macOS: source ../venv/bin/activate

pip install -r requirements.txt
python -m spacy download ru_core_news_sm
python -c "import nltk; nltk.download('vader_lexicon'); nltk.download('stopwords')"