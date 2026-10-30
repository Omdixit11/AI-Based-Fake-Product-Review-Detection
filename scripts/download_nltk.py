"""Download the NLTK data this project needs. Run once: python scripts/download_nltk.py"""
import nltk

for pkg in ["stopwords", "wordnet", "omw-1.4", "vader_lexicon", "punkt", "punkt_tab"]:
    nltk.download(pkg, quiet=True)
    print("ok:", pkg)
