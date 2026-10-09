"""Semantic similarity layer. Uses a local MiniLM sentence-transformer if it is installed AND already downloaded;
otherwise falls back to TF-IDF + cosine written from scratch (no download, no network, always works)."""
import math, os, re
from collections import Counter, defaultdict
from domain import stem, tokens, TYPE_LABEL

STOP = set("i need a an the for my me to of and or with under below within show find want some in on at that this please looking buy get can you it be from by up than".split())
TYPE_SYN = {"running": "running jogging", "walking": "walking", "training": "training gym workout", "casual": "casual everyday",
            "sneakers": "sneakers casual", "formal": "formal office", "sandals": "sandals sliders flip flops",
            "heels": "heels party", "boots": "boots", "sports-other": "sports"}

def doc_text(p):
    return " ".join([p["title"], TYPE_LABEL[p["product_type"]], TYPE_SYN[p["product_type"]], p["brand"] or "", p["colour"] or "", p["gender"] or ""])

def _terms(text):
    w = [stem(t) for t in tokens(text) if t not in STOP and len(t) > 1]
    return w + [a + "_" + b for a, b in zip(w, w[1:])]          # unigrams + bigrams

class TfidfEngine:
    name = "TF-IDF + cosine (offline, from scratch)"
    def __init__(self, products):
        docs = [Counter(_terms(doc_text(p))) for p in products]; n = len(docs)
        df = Counter(t for d in docs for t in d)
        self.idf = {t: math.log((n + 1) / (c + 1)) + 1 for t, c in df.items()}; self.n = n
        self.post = defaultdict(list)                            # inverted index: term -> [(doc, weight)]
        for i, d in enumerate(docs):
            v = {t: (1 + math.log(c)) * self.idf[t] for t, c in d.items()}; norm = math.sqrt(sum(x * x for x in v.values())) or 1
            for t, x in v.items(): self.post[t].append((i, x / norm))
    def scores(self, text):
        q = {t: (1 + math.log(c)) * self.idf[t] for t, c in Counter(_terms(text)).items() if t in self.idf}
        qn = math.sqrt(sum(x * x for x in q.values())) or 1; out = [0.0] * self.n
        for t, x in q.items():
            for i, w in self.post[t]: out[i] += (x / qn) * w
        return out

class MiniLMEngine:
    name = "MiniLM sentence-transformer (local)"
    def __init__(self, products):
        from sentence_transformers import SentenceTransformer           # raises if not installed
        self.model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", local_files_only=True)  # raises if not downloaded
        import numpy as np
        cache = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "emb_minilm.npy")
        if os.path.exists(cache) and np.load(cache).shape[0] == len(products): self.emb = np.load(cache)
        else:
            self.emb = self.model.encode([doc_text(p) for p in products], batch_size=64, normalize_embeddings=True); np.save(cache, self.emb)
    def scores(self, text):
        return [float(x) for x in self.emb @ self.model.encode([text], normalize_embeddings=True)[0]]

def make_engine(products):
    if os.getenv("SEMANTIC", "auto") != "tfidf":
        try: return MiniLMEngine(products)
        except Exception: pass
    return TfidfEngine(products)
