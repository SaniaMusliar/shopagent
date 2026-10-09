"""Stage 3 - Intent extraction: free text -> structured requirements (slots). Rules + lexicons, no LLM."""
import re
from domain import stem, tokens, TYPE_WORDS, STYLE_RE

WOMEN = {"women", "woman", "womens", "ladies", "lady", "female", "sister", "mom", "mother", "wife", "girlfriend"}
MEN = {"men", "man", "mens", "male", "brother", "dad", "father", "husband", "boyfriend", "gents"}
KIDS = {"kid", "kids", "boys", "girls", "child", "children", "son", "daughter", "toddler", "infant"}
UNISEX = {"unisex"}

USE_CASES = {  # use case -> trigger regex
    "daily wear": r"\bdaily\b|\beveryday\b|\bday[- ]to[- ]day\b", "college": r"\bcollege\b|\bcampus\b|\buniversity\b",
    "office": r"\boffice\b|\bwork\b|\bcorporate\b|\binterview\b|\bmeeting", "gym": r"\bgym\b|\bworkout\b|\bcrossfit\b",
    "jogging": r"\bjog|\bmarathon\b|\brunning\b", "walking": r"\bwalk", "party": r"\bparty\b|\bwedding\b|\bfestive\b|\bfunction\b|\bdiwali\b",
    "travel": r"\btravel|\btrek|\bhiking\b|\btrail\b", "rainy season": r"\bmonsoon\b|\brain", "beach/home": r"\bbeach\b|\bpool\b|\bhome\b|\bindoor\b"}
PREFERENCES = {  # soft preference -> trigger regex
    "comfortable": r"comfort|comfy|cushion|soft", "lightweight": r"lightweight|light weight|light\b",
    "waterproof": r"waterproof|water[- ]resistant", "leather": r"\bleather\b", "slip-on": r"slip[- ]?on",
    "lace-up": r"lace[- ]?up|laces", "non-slip": r"non[- ]?slip|grip|anti[- ]?skid"}

def _amount(m): return int(float(m.group(1)) * (1000 if m.group(2) else 1))

def parse_budget(q):
    t = q.lower().replace(",", ""); cur = r"\s*(?:₹|rs\.?|inr)?\s*"; num = r"(\d+(?:\.\d+)?)\s*(k)?\b"
    mx = re.search(r"(?:under|below|within|upto|up to|less than|max(?:imum)?|budget(?: of)?|not more than|no more than|cheaper than)" + cur + num, t)
    mn = re.search(r"(?:above|over|more than|at least|minimum|min|starting from)" + cur + num, t)
    if not mx: mx = re.search(r"(?:₹|rs\.?|inr)\s*" + num, t) or re.search(num + r"\s*(?:rs|rupees|inr)\b", t)
    return (_amount(mx) if mx else None), (_amount(mn) if mn else None)

def build_vocab(products):
    brands = {}
    for p in products:
        b = (p["brand"] or "").strip()
        if len(b) >= 3 and b.lower() not in WOMEN | MEN | KIDS: brands[b.lower()] = b
    return {"brands": brands, "colours": sorted({p["colour"] for p in products if p["colour"]})}

def extract_intent(query, vocab):
    q = query.lower(); toks = tokens(q); stems = [stem(t) for t in toks]
    # product type (hard): union of disjoint words, intersection of overlapping ones ("casual sneakers" -> sneakers)
    type_words = [s for s in stems if s in TYPE_WORDS]; types = None
    for s in dict.fromkeys(type_words):
        cur = TYPE_WORDS[s]
        types = set(cur) if types is None else ((types & cur) or (types | cur))
    styles = [s for s in dict.fromkeys(type_words) if s in STYLE_RE]
    colours = [("grey" if t == "gray" else t) for t in toks if (t == "gray" or t in vocab["colours"])]
    g = ("women" if set(toks) & WOMEN else None, "men" if set(toks) & MEN else None,
         "kids" if set(toks) & KIDS else None, "unisex" if set(toks) & UNISEX else None)
    g = [x for x in g if x]; gender = g[0] if len(g) == 1 else None
    bmax, bmin = parse_budget(q)
    brands = [orig for low, orig in vocab["brands"].items() if re.search(r"(?<![a-z0-9])" + re.escape(low) + r"(?![a-z0-9])", q)]
    unsupported = []
    if re.search(r"\bsize\s*(?:uk|us|eu)?\s*\d|\b(?:uk|us|eu)\s*\d{1,2}\b", q):
        unsupported.append("Shoe size was ignored: the catalogue has no size data")
    return {"types": sorted(types) if types else None, "type_words": list(dict.fromkeys(type_words)), "styles": styles,
            "colours": list(dict.fromkeys(colours)), "gender": gender, "budget_max": bmax, "budget_min": bmin,
            "brands": brands, "use_cases": [k for k, r in USE_CASES.items() if re.search(r, q)],
            "preferences": [k for k, r in PREFERENCES.items() if re.search(r, q)], "unsupported": unsupported}

def semantic_text(query, intent):
    """Query text for the semantic layer: budget phrases removed, canonical type words added (jogging -> running)."""
    t = re.sub(r"(?:under|below|within|upto|up to|less than|max\w*|budget(?: of)?|above|over|at least)?\s*(?:₹|rs\.?|inr)?\s*\d[\d,.]*\s*k?\b", " ", query.lower())
    return (t + " " + " ".join(intent["types"] or [])).strip()

TOK_STOP = set("i need a an the for my me to of and or with under below within show find want some in on at that this please looking buy get can you it be from by up than is are who likes like".split())
def token_view(query, I):
    """Per-token record for the simulator: raw word, stem, stop-word flag and which requirement slot it filled."""
    ctypes = set(I["type_words"]); colours = set(I["colours"]) | ({"gray"} if "grey" in I["colours"] else set())
    brands = {w for b in I["brands"] for w in tokens(b.lower())}; out = []
    for t in tokens(query):
        s = stem(t); slot = None
        if s in ctypes or t in ctypes: slot = "Product type"
        elif t in colours: slot = "Colour"
        elif I["gender"] and t in (WOMEN | MEN | KIDS | UNISEX): slot = "Gender"
        elif t in brands: slot = "Brand"
        elif re.fullmatch(r"\d+k?", t) or t in ("rs", "inr", "rupees") or (I["budget_max"] or I["budget_min"]) and t in ("under", "below", "within", "upto", "above", "over", "budget"): slot = "Budget"
        else:
            for k, rx in {**USE_CASES, **PREFERENCES}.items():
                if re.search(rx, t): slot = "Use case" if k in USE_CASES else "Preference"; break
        out.append({"raw": t, "stem": s, "stop": t in TOK_STOP and slot is None, "slot": slot})
    return out
