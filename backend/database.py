"""SQLite catalogue. Built once from data/footwear_clean.csv (Myntra, CC0, May-2023 snapshot)."""
import csv, json, os, re, sqlite3
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(ROOT, "data", "footwear_clean.csv")
DB_PATH = os.path.join(ROOT, "data", "footwear.db")
SCHEMA = """CREATE TABLE products(
 id INTEGER PRIMARY KEY, source TEXT, source_id TEXT, title TEXT, brand TEXT, category TEXT,
 product_type TEXT, gender TEXT, colour TEXT, price INTEGER, mrp INTEGER, currency TEXT,
 image_url TEXT, description TEXT, rating REAL, rating_count INTEGER, availability INTEGER,
 product_url TEXT, raw_data TEXT)"""

def classify(cat, title, old):
    """Re-derive the product type from URL category + title WORDS (whole words only, so brand 'Bootco' is not a boot,
    and 'block heel boots' is a boot, not a heel). Mirrors prep3.py with these fixes."""
    t = title.lower(); w = lambda rx: re.search(rx, t)
    if w(r"\bboots?\b") or cat == "boots": return "boots"
    if cat == "heels" or w(r"\b(heels?|pumps?|stilettos?|wedges?)\b"): return "heels"
    if cat in ("sandals", "sports-sandals", "flip-flops"): return "sandals"
    if cat == "formal-shoes": return "formal"
    if cat == "sports-shoes":
        if w(r"\b(running|jogging)\b"): return "running"
        if w(r"\bwalking\b"): return "walking"
        if w(r"\b(training|gym)\b"): return "training"
        return "sports-other"
    if cat in ("casual-shoes", "sneakers", "loafers"): return "sneakers" if (cat == "sneakers" or w(r"\bsneakers?\b")) else "casual"
    return old

def build(csv_path=CSV_PATH, db_path=DB_PATH):
    if os.path.exists(db_path): os.remove(db_path)
    con = sqlite3.connect(db_path); con.execute(SCHEMA); n = 0
    with open(csv_path, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            # availability: the dataset has no stock field; every row is a live listing in the snapshot -> 1
            con.execute("INSERT INTO products VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                int(r["pid"]), "myntra", r["pid"], r["title"], r["brand"], r["cat"], classify(r["cat"], r["title"], r["type"]),
                r["gender"] or None, r["colour"] or None, int(float(r["price"])), int(float(r["mrp"] or 0)), "INR",
                r["image_url"], None, float(r["rating"] or 0), int(float(r["rating_count"] or 0)), 1,
                r["product_url"], json.dumps(r, ensure_ascii=False)))
            n += 1
    con.commit(); con.close(); return n

_CACHE = {}
def load_products(db_path=DB_PATH):
    if db_path not in _CACHE:
        if not os.path.exists(db_path): build(db_path=db_path)
        con = sqlite3.connect(db_path); con.row_factory = sqlite3.Row
        _CACHE[db_path] = [dict(r) for r in con.execute("SELECT * FROM products ORDER BY id")]
        con.close()
    return _CACHE[db_path]

def get_product(pid, db_path=DB_PATH):
    for p in load_products(db_path):
        if p["id"] == pid: return p

if __name__ == "__main__":
    print("products loaded:", build())
