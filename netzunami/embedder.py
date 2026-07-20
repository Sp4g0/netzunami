from sentence_transformers import SentenceTransformer
import numpy as np


_MODEL: SentenceTransformer | None = None


def get_model(model_name: str = "all-MiniLM-L6-v2") -> SentenceTransformer:
    global _MODEL
    if _MODEL is None:
        _MODEL = SentenceTransformer(model_name)
    return _MODEL


def embed(texts: list[str], model_name: str = "all-MiniLM-L6-v2") -> np.ndarray:
    model = get_model(model_name)
    return model.encode(texts, show_progress_bar=False, normalize_embeddings=True)


def embed_single(text: str, model_name: str = "all-MiniLM-L6-v2") -> np.ndarray:
    return embed([text], model_name)[0]
