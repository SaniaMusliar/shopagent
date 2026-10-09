"""Stage 2 - Domain check: is this a footwear request? Controlled footwear taxonomy lives here."""
import re

def stem(w): return w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w
def tokens(t): return re.findall(r"[a-z0-9]+", t.lower())

# Catalogue product types (set by data/prep3.py):
TYPES = ["running", "walking", "training", "casual", "sneakers", "formal", "sandals", "heels", "boots", "sports-other"]
TYPE_LABEL = {"running": "Running shoes", "walking": "Walking shoes", "training": "Training/gym shoes",
              "casual": "Casual shoes", "sneakers": "Sneakers", "formal": "Formal shoes", "sandals": "Sandals",
              "heels": "Heels", "boots": "Boots", "sports-other": "Sports shoes (general)"}

# word (stemmed) -> catalogue types it may refer to. Disjoint sets are unioned, overlapping sets are intersected.
TYPE_WORDS = {
    "running": {"running"}, "jogging": {"running"}, "runner": {"running"},
    "walking": {"walking"}, "training": {"training"}, "gym": {"training"}, "workout": {"training"},
    "sport": {"running", "walking", "training", "sports-other"},
    "casual": {"casual", "sneakers"}, "sneaker": {"sneakers"}, "formal": {"formal"},
    "sandal": {"sandals"}, "slipper": {"sandals"}, "slider": {"sandals"}, "flop": {"sandals"}, "chappal": {"sandals"},
    "heel": {"heels"}, "stiletto": {"heels"}, "wedge": {"heels"}, "boot": {"boots"},
    "loafer": {"casual", "formal"}, "oxford": {"formal"}, "derby": {"formal"}, "brogue": {"formal"},
}
# finer styles that are not a catalogue type: enforced as a title keyword
STYLE_RE = {"loafer": "loafer", "wedge": "wedge", "stiletto": "stiletto", "oxford": "oxford", "derby": "derby",
            "brogue": "brogue", "slider": "slider", "slipper": "slipper", "flop": "flip.?flop"}

FOOTWEAR_NOUNS = {"shoe", "footwear", "sneaker", "sandal", "slipper", "slider", "flop", "chappal", "heel", "stiletto",
                  "wedge", "boot", "loafer", "oxford", "derby", "brogue"}
SOFT_SIGNALS = {"running", "jogging", "walking"}   # count as footwear only when no other product is named
OTHER_PRODUCTS = {"laptop", "phone", "mobile", "smartphone", "tv", "television", "shirt", "tshirt", "jean", "trouser",
                  "pant", "dress", "kurta", "saree", "watch", "bag", "backpack", "wallet", "belt", "sunglass",
                  "headphone", "earbud", "speaker", "camera", "tablet", "charger", "book", "furniture", "sofa",
                  "chair", "fridge", "refrigerator", "ac", "car", "bike", "short", "jacket", "hoodie", "sock", "cap",
                  "hat", "perfume", "makeup", "lipstick", "grocery", "rice", "mouse", "keyboard", "monitor",
                  "console", "toy", "tshirts", "jewellery", "ring", "necklace"}

def check_domain(query):
    toks = [stem(t) for t in tokens(query)]
    nouns = [t for t in toks if t in FOOTWEAR_NOUNS]
    soft = [t for t in toks if t in SOFT_SIGNALS]
    other = [t for t in toks if t in OTHER_PRODUCTS]
    ok = bool(nouns) or (bool(soft) and not other)
    if ok: reason = "Footwear terms found: " + ", ".join(dict.fromkeys(nouns + soft))
    elif other: reason = "Request is about a non-footwear product: " + ", ".join(dict.fromkeys(other))
    else: reason = "No footwear term found in the request"
    return {"in_domain": ok, "signals": list(dict.fromkeys(nouns + soft)), "other_products": list(dict.fromkeys(other)), "reason": reason}
