import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE = True
except ImportError:
    HAS_SENTENCE = False

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


_MODEL = None
_TFIDF = None


def get_model(model_name: str = "all-MiniLM-L6-v2"):
    global _MODEL
    if _MODEL is None and HAS_SENTENCE:
        _MODEL = SentenceTransformer(model_name)
    return _MODEL


def embed(texts: list[str], model_name: str = "all-MiniLM-L6-v2"):
    import numpy as np

    if HAS_SENTENCE:
        model = get_model(model_name)
        return model.encode(texts, show_progress_bar=False, normalize_embeddings=True)

    global _TFIDF
    if _TFIDF is None:
        _TFIDF = TfidfVectorizer(max_features=5000, stop_words="english")
        _TFIDF.fit(texts)
    vectors = _TFIDF.transform(texts).toarray().astype(np.float32)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return vectors / norms


def embed_single(text: str, model_name: str = "all-MiniLM-L6-v2"):
    return embed([text], model_name)[0]
