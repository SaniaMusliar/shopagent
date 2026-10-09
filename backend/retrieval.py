"""Stages 4-6 - Hard constraints, catalogue retrieval and hard filtering (with a full rejection log)."""
import re
from domain import TYPE_LABEL
from itertools import zip_longest

class Constraint:
    """One non-negotiable requirement. check(p) returns None if satisfied, else the human-readable reason."""
    def __init__(self, kind, label, fn, implicit=False, value=None):
        self.kind, self.label, self.fn, self.implicit, self.value = kind, label, fn, implicit, value
    def check(self, p): return self.fn(p)
    def info(self): return {"kind": self.kind, "label": self.label, "implicit": self.implicit, "value": self.value}

def build_constraints(I):
    C = []; inr = lambda n: f"₹{n:,}"
    if I["types"]:
        ts = set(I["types"]); lab = " / ".join(TYPE_LABEL[t] for t in sorted(ts))
        C.append(Constraint("type", f"Product type: {lab}", lambda p, ts=ts, lab=lab: None if p["product_type"] in ts else
                 f"Product type is {TYPE_LABEL[p['product_type']]}, not {lab}", value=sorted(ts)))
    for s in I["styles"]:
        from domain import STYLE_RE
        rx = re.compile(STYLE_RE[s], re.I)
        C.append(Constraint("style", f"Style: {s}", lambda p, rx=rx, s=s: None if rx.search(p["title"]) else f"Not a {s} style", value=s))
    if I["gender"]:
        g = I["gender"]; ok = {"women": {"women", "unisex"}, "men": {"men", "unisex"}, "kids": {"kids"}, "unisex": {"unisex"}}[g]
        C.append(Constraint("gender", f"Gender: {g}" + (" (unisex fits too)" if g in ("women", "men") else ""),
                 lambda p, ok=ok, g=g: None if p["gender"] in ok else ("Gender not stated, cannot verify " + g if not p["gender"] else f"Made for {p['gender']}, not {g}"), value=g))
    else:
        C.append(Constraint("audience", "Adult catalogue (kids' footwear excluded unless requested)",
                 lambda p: "Kids' footwear, not requested" if p["gender"] == "kids" else None, implicit=True))
    if I["colours"]:
        cs = set(I["colours"]); lab = "/".join(sorted(cs))
        C.append(Constraint("colour", f"Colour: {lab}", lambda p, cs=cs, lab=lab: None if p["colour"] in cs else
                 (f"Colour not stated, cannot verify {lab}" if not p["colour"] else f"Colour is {p['colour']}, not {lab}"), value=sorted(cs)))
    if I["brands"]:
        bs = {b.lower() for b in I["brands"]}; lab = " / ".join(I["brands"])
        C.append(Constraint("brand", f"Brand: {lab}", lambda p, bs=bs, lab=lab: None if (p["brand"] or "").lower() in bs else f"Brand is {p['brand']}, not {lab}", value=I["brands"]))
    mx, mn = I["budget_max"], I["budget_min"]
    if mx is not None or mn is not None:
        lab = "Budget: " + (f"{inr(mn)} to {inr(mx)}" if mx and mn else f"up to {inr(mx)}" if mx else f"from {inr(mn)}")
        def budget(p):
            if mx is not None and p["price"] > mx: return f"Price {inr(p['price'])} exceeds budget {inr(mx)}"
            if mn is not None and p["price"] < mn: return f"Price {inr(p['price'])} is below minimum {inr(mn)}"
        C.append(Constraint("budget", lab, budget, value={"max": mx, "min": mn}))
    C.append(Constraint("availability", "Availability: listed in catalogue snapshot", lambda p: None if p["availability"] else "Not available", implicit=True))
    return C

def retrieve(products, C):
    """Retrieval = every catalogue record of the requested type/style (whole catalogue if no type was asked)."""
    pool = products
    for c in C:
        if c.kind in ("type", "style"): pool = [p for p in pool if c.check(p) is None]
    return pool

def hard_filter(pool, C):
    """Apply remaining constraints one by one; returns valid products and the funnel (count before -> after each)."""
    funnel = []; cur = pool
    for c in C:
        if c.kind in ("type", "style"): continue
        nxt = [p for p in cur if c.check(p) is None]; funnel.append({"label": c.label, "kind": c.kind, "before": len(cur), "after": len(nxt)}); cur = nxt
    return cur, funnel

def rejection_log(products, C, sims, limit=12):
    """Why were products rejected? Picks the most query-similar rejected products, one constraint kind at a time (round robin)."""
    fails = {}; counts = {}
    for i, p in enumerate(products):
        f = [(c.kind, r) for c in C if (r := c.check(p))]
        if f:
            fails[i] = f
            for k in {k for k, _ in f}: counts[k] = counts.get(k, 0) + 1
    by_kind = {}
    for i, f in fails.items():
        by_kind.setdefault(f[0][0], []).append(i)                    # grouped by FIRST failed constraint
    for k in by_kind: by_kind[k].sort(key=lambda i: (len(fails[i]), -sims[i]))
    picked = []
    for row in zip_longest(*[by_kind[k] for k in sorted(by_kind, key=lambda k: -counts[k])]):
        picked += [i for i in row if i is not None]
    out = [{"id": products[i]["id"], "title": products[i]["title"], "brand": products[i]["brand"], "price": products[i]["price"],
            "type": products[i]["product_type"], "colour": products[i]["colour"], "image_url": products[i]["image_url"],
            "reasons": [r for _, r in fails[i]]} for i in picked[:limit]]
    return out, counts

def leave_one_out_hints(products, C):
    """For a NO MATCH result: text-only facts about what dropping one requirement would change (never a product card)."""
    hints = []
    for c in C:
        if c.implicit or c.kind in ("type", "style"): continue
        rest = [x for x in C if x is not c]; ok = [p for p in products if all(x.check(p) is None for x in rest)]
        if not ok: continue
        if c.kind == "budget": hints.append(f"Without the budget limit {len(ok)} matching products exist, the cheapest costs ₹{min(p['price'] for p in ok):,}.")
        elif c.kind == "colour": hints.append(f"Without the colour requirement {len(ok)} products match; colours available: {', '.join(sorted({p['colour'] or 'unknown' for p in ok}))}.")
        elif c.kind == "gender": hints.append(f"Without the gender requirement {len(ok)} products match.")
        elif c.kind == "brand": hints.append(f"Without the brand requirement {len(ok)} products match.")
    return hints
