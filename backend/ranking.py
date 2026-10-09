"""Stage 7 - AI ranking of the products that survived the hard constraints. Every number comes from product data."""
import math, re

WEIGHTS = {"semantic": 40, "use_case": 20, "attributes": 15, "price_fit": 15, "rating": 10}
LABELS = {"semantic": "Semantic relevance", "use_case": "Use-case match", "attributes": "Attribute match",
          "price_fit": "Price fit", "rating": "Rating & popularity"}
# use case -> (catalogue types that serve it, title keywords that also hint at it)
USE_EVIDENCE = {
    "daily wear": ({"casual", "sneakers", "walking"}, r"casual|walking|comfort|daily"),
    "college": ({"casual", "sneakers", "walking"}, r"casual|sneaker|walking|comfort"),
    "office": ({"formal"}, r"formal|loafer|derby|oxford|brogue|leather"),
    "gym": ({"training", "running"}, r"gym|training|sports|running"),
    "jogging": ({"running"}, r"running|jogging|marathon|sports"),
    "walking": ({"walking"}, r"walking|comfort"),
    "party": ({"heels"}, r"party|embellished|glitter|sequin|stiletto|block|wedge"),
    "travel": ({"walking", "boots", "sneakers"}, r"trek|trail|hiking|walking|boot"),
    "rainy season": ({"sandals"}, r"waterproof|rain|rubber|eva|flip|slider|crocs|clog"),
    "beach/home": ({"sandals"}, r"flip|slider|slipper|beach|pool|clog")}
PREF_EVIDENCE = {"comfortable": r"comfort|cushion|foam|soft|memory", "lightweight": r"light|mesh|knit|breath",
                 "waterproof": r"waterproof|rain|rubber|eva|pvc", "leather": r"leather", "slip-on": r"slip.?on",
                 "lace-up": r"lace", "non-slip": r"non.?slip|grip|anti.?skid"}

def rank(valid, sims, I, index_of):
    """valid: products passing all constraints; sims: cosine per catalogue index; returns ranked list with score breakdown."""
    mx = max([sims[index_of[p["id"]]] for p in valid], default=0) or 1
    out = []
    for p in valid:
        comp = {}
        cos = sims[index_of[p["id"]]]
        comp["semantic"] = (cos / mx, f"cosine {cos:.2f} (best candidate = 100%)")
        if I["use_cases"]:
            hit = []
            for u in I["use_cases"]:
                types, rx = USE_EVIDENCE[u]
                hit.append(1.0 if p["product_type"] in types else 0.6 if re.search(rx, p["title"], re.I) else 0.0)
            comp["use_case"] = (sum(hit) / len(hit), "; ".join(f"{u}: {'type fits' if h == 1 else 'title hints' if h else 'no evidence'}" for u, h in zip(I["use_cases"], hit)))
        if I["preferences"]:
            hit = [1.0 if re.search(PREF_EVIDENCE[x], p["title"], re.I) else 0.0 for x in I["preferences"]]
            comp["attributes"] = (sum(hit) / len(hit), "; ".join(f"{x}: {'in title' if h else 'not stated'}" for x, h in zip(I["preferences"], hit)))
        if I["budget_max"]:
            head = max(0.0, 1 - p["price"] / I["budget_max"]); disc = max(0.0, (p["mrp"] - p["price"]) / p["mrp"]) if p["mrp"] else 0.0
            comp["price_fit"] = (0.5 * head + 0.5 * disc, f"{head:.0%} under budget, {disc:.0%} off MRP")
        if p["rating"] > 0:
            comp["rating"] = (0.8 * p["rating"] / 5 + 0.2 * min(1, math.log10(p["rating_count"] + 1) / 3), f"{p['rating']}★ from {p['rating_count']} ratings")
        else:
            comp["rating"] = (0.5, "no ratings yet (neutral 50%)")
        wsum = sum(WEIGHTS[k] for k in comp); pts = {k: v[0] * WEIGHTS[k] for k, v in comp.items()}
        out.append({"id": p["id"], "score": round(100 * sum(pts.values()) / wsum),
                    "breakdown": [{"key": k, "label": LABELS[k], "weight": WEIGHTS[k], "points": round(pts[k], 1),
                                   "raw": round(comp[k][0], 3), "note": comp[k][1]} for k in comp],
                    "na": [LABELS[k] for k in WEIGHTS if k not in comp], "cos": round(cos, 3)})
    pm = {p["id"]: p for p in valid}
    out.sort(key=lambda r: (-r["score"], -pm[r["id"]]["rating"], pm[r["id"]]["price"]))
    return out
