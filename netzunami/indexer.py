import os
import re
import json
import numpy as np
from pathlib import Path
from .embedder import embed


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> list[str]:
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        chunk = " ".join(words[start : start + chunk_size])
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


def extract_text_from_pdf(pdf_path: str) -> str:
    import fitz

    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text() + "\n"
    doc.close()
    return text


def extract_text_from_txt(txt_path: str) -> str:
    with open(txt_path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def index_manuals(
    manuals_dir: str,
    output_dir: str,
    model_name: str = "all-MiniLM-L6-v2",
    chunk_size: int = 512,
    chunk_overlap: int = 64,
    rebuild: bool = False,
) -> tuple[any, list[dict]]:
    import faiss
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    index_path = out / "faiss.index"
    meta_path = out / "metadata.json"

    if index_path.exists() and meta_path.exists() and not rebuild:
        index = faiss.read_index(str(index_path))
        with open(meta_path) as f:
            metadata = json.load(f)
        print(f"  Loaded existing index ({index.ntotal} vectors)")
        return index, metadata

    texts = []
    metadata = []

    for fname in sorted(os.listdir(manuals_dir)):
        fpath = os.path.join(manuals_dir, fname)
        if fname.endswith(".pdf"):
            print(f"  Extracting PDF: {fname}")
            raw = extract_text_from_pdf(fpath)
        elif fname.endswith(".txt"):
            raw = extract_text_from_txt(fpath)
        else:
            continue

        chunks = chunk_text(raw, chunk_size, chunk_overlap)
        for i, chunk in enumerate(chunks):
            texts.append(chunk)
            metadata.append({
                "source": fname,
                "chunk": i,
                "text": chunk[:200] + "..." if len(chunk) > 200 else chunk,
            })

    if not texts:
        print("  No documents found to index")
        dim = 384
        index = faiss.IndexFlatIP(dim)
        return index, metadata

    print(f"  Generating embeddings for {len(texts)} chunks...")
    vectors = embed(texts, model_name)
    dim = vectors.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(vectors.astype(np.float32))

    faiss.write_index(index, str(index_path))
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"  Indexed {index.ntotal} vectors into {index_path}")
    return index, metadata


def search(
    index: any,
    metadata: list[dict],
    query: str,
    model_name: str = "all-MiniLM-L6-v2",
    top_k: int = 5,
) -> list[tuple[dict, float]]:
    qvec = embed([query], model_name).astype(np.float32)
    scores, indices = index.search(qvec, top_k)
    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx >= 0 and idx < len(metadata):
            results.append((metadata[idx], float(score)))
    return results
