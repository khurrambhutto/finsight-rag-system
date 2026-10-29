"""Index current extracted passages and search a single report."""
import hashlib
import json
import os
import re
import threading
import uuid
from functools import lru_cache

from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer
from app.retrieval.context import select_passages

MODEL_NAME = os.getenv('FINSIGHT_EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
COLLECTION = 'finsight_' + hashlib.sha256(MODEL_NAME.encode()).hexdigest()[:16]
LOCK = threading.Lock()


@lru_cache(maxsize=1)
def embedder():
    return SentenceTransformer(MODEL_NAME, device='cpu')


@lru_cache(maxsize=1)
def client():
    return QdrantClient(url=os.getenv('QDRANT_URL', 'http://127.0.0.1:6333'), timeout=30)


def segments(chunk):
    """Keep table headers with row groups; limit text fed to the encoder."""
    text = chunk['text']
    if chunk['content_type'] == 'table':
        lines = text.splitlines()
        if len(lines) > 2:
            header = '\n'.join(lines[:2])
            rows = lines[2:]
            if rows and re.search(r'\b(?:19|20)\d{2}\b', rows[0]) and re.search(r'year|ended|months', rows[0], re.I):
                header += '\n' + rows.pop(0)
            return [header + '\n' + row for row in rows if row.strip()] or [text]
    words = text.split()
    return [' '.join(words[i:i + 160]) for i in range(0, len(words), 160)] or [text]


def embedding_text(text):
    lines = [line for line in text.splitlines() if not re.fullmatch(r'[\s|:=-]+', line)]
    return ' '.join(' '.join(line.replace('|', ' ').split()) for line in lines)


def search(document, chunks, question, limit=8):
    if not chunks:
        return []
    signature = hashlib.sha256(('table-rows-v3' + json.dumps(chunks, sort_keys=True, ensure_ascii=False)).encode()).hexdigest()
    with LOCK:
        model = embedder()
        store = client()
        if not store.collection_exists(COLLECTION):
            store.create_collection(COLLECTION, vectors_config=models.VectorParams(size=model.get_sentence_embedding_dimension(), distance=models.Distance.COSINE))
        condition = models.Filter(must=[models.FieldCondition(key='document_id', match=models.MatchValue(value=document['id']))])
        existing, _ = store.scroll(COLLECTION, scroll_filter=condition, limit=1, with_payload=True, with_vectors=False)
        entries = [(chunk, segment) for chunk in chunks if chunk['content_type'] != 'heading' for segment in segments(chunk)]
        count = store.count(COLLECTION, count_filter=condition, exact=True).count
        if not existing or existing[0].payload.get('signature') != signature or count != len(entries):
            store.delete(COLLECTION, points_selector=models.FilterSelector(filter=condition), wait=True)
            for start in range(0, len(entries), 32):
                batch = entries[start:start + 32]
                inputs = [f"{document['company']} {document['year']} {chunk['section'] or ''}\n{embedding_text(text)}" for chunk, text in batch]
                vectors = model.encode(inputs, normalize_embeddings=True, batch_size=32).tolist()
                points = [models.PointStruct(id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{chunk['id']}:{start + offset}")), vector=vector,
                    payload={'document_id': document['id'], 'chunk_id': chunk['id'], 'page': chunk['page'], 'section': chunk['section'], 'content_type': chunk['content_type'], 'text': text, 'signature': signature})
                    for offset, ((chunk, text), vector) in enumerate(zip(batch, vectors))]
                store.upsert(COLLECTION, points=points, wait=True)
        query = model.encode(question, normalize_embeddings=True).tolist()
        hits = store.query_points(COLLECTION, query=query, query_filter=condition, limit=80, with_payload=True).points
        return select_passages(document, chunks, hits, question, limit)
