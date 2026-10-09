"""One-time download of the free MiniLM model so the app can run it offline afterwards."""
from sentence_transformers import SentenceTransformer
SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2"); print("MiniLM ready. Restart the app; /api/health will show it.")
