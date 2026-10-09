"""Orchestrates the 8 stages and records a TRACE of real inputs/outputs; the AI Processing page replays this trace."""
import time
from database import load_products
from domain import check_domain, TYPE_LABEL
from intent import build_vocab, extract_intent, semantic_text, token_view
from retrieval import build_constraints, retrieve, hard_filter, rejection_log, leave_one_out_hints
from ranking import rank, WEIGHTS, LABELS
from explain import explain, why_list, validate_text
from security import check_input, final_gate
from semantic import make_engine

class Engine:
    def __init__(self):
        self.products = load_products(); self.by_id = {p["id"]: p for p in self.products}
        self.index = {p["id"]: i for i, p in enumerate(self.products)}
        self.vocab = build_vocab(self.products); self.sem = make_engine(self.products)
_E = None
def engine():
    global _E
    if _E is None: _E = Engine()
    return _E

def public(p):
    return {k: p[k] for k in ("id", "title", "brand", "product_type", "gender", "colour", "price", "mrp", "rating", "rating_count", "image_url", "product_url")} | {"source": "Myntra"}

def run(raw_query):
    E = engine(); T = {}; trace = []; t0 = time.perf_counter()
    def stage(sid, title, summary, data, since):
        ms = round((time.perf_counter() - since) * 1000, 1); T[sid] = ms
        trace.append({"id": sid, "title": title, "summary": summary, "data": data, "ms": ms})
    base = {"catalogue": {"size": len(E.products), "source": "Myntra India (CC0)", "snapshot": "May 2023", "engine": E.sem.name}}

    # 1 - user query + security
    t = time.perf_counter(); sec, msg, kind, q = check_input(raw_query)
    if msg:
        stage("query", "User Query", msg, {"security": sec}, t)
        return {**base, "status": "blocked" if kind == "blocked" else "invalid", "message": msg, "security": sec, "trace": trace, "timings": T}
    stage("query", "User Query", f"{len(q)} characters received, cleaned and scanned: input validation PASS, injection scan PASS", {"query": q, "chars": len(q), "security": sec}, t)

    # 2 - domain check
    t = time.perf_counter(); dom = check_domain(q)
    stage("domain", "Domain Check", dom["reason"], dom, t)
    if not dom["in_domain"]:
        return {**base, "status": "outside", "query": q, "message": "OUTSIDE CURRENT CATALOGUE", "domain": dom, "security": sec, "trace": trace, "timings": T,
                "detail": "This AI Shopping Agent currently specializes in footwear. No footwear products were recommended for this request."}

    # 3 - intent extraction
    t = time.perf_counter(); I = extract_intent(q, E.vocab)
    slots = [("Product type", " / ".join(TYPE_LABEL[x] for x in I["types"]) if I["types"] else None), ("Colour", ", ".join(I["colours"]) or None),
             ("Gender", I["gender"]), ("Brand", ", ".join(I["brands"]) or None),
             ("Budget", (f"₹{I['budget_min']:,} to ₹{I['budget_max']:,}" if I["budget_min"] and I["budget_max"] else f"up to ₹{I['budget_max']:,}" if I["budget_max"] else f"from ₹{I['budget_min']:,}" if I["budget_min"] else None)),
             ("Use case", ", ".join(I["use_cases"]) or None), ("Preference", ", ".join(I["preferences"]) or None)]
    slots = [{"k": k, "v": v} for k, v in slots if v]
    tv = token_view(q, I)
    stage("intent", "Intent Extraction", f"{len(slots)} requirement(s) understood from the sentence", {"intent": I, "slots": slots, "notes": I["unsupported"], "tokens": tv}, t)

    # 4 - constraint extraction
    t = time.perf_counter(); C = build_constraints(I)
    stage("constraints", "Constraint Extraction", f"{len(C)} hard constraints will be enforced (never relaxed)", {"constraints": [c.info() for c in C]}, t)

    # 5 - catalogue retrieval
    t = time.perf_counter(); pool = retrieve(E.products, C)
    stage("retrieval", "Catalogue Retrieval", f"{len(pool)} of {len(E.products)} catalogue products retrieved" + (" for the requested type" if I["types"] else " (no type requested)"),
          {"catalogue": len(E.products), "retrieved": len(pool)}, t)

    # 6 - hard filtering (+ rejection log)
    t = time.perf_counter(); valid, funnel = hard_filter(pool, C)
    sims = E.sem.scores(semantic_text(q, I))
    rej, rcounts = rejection_log(E.products, C, sims)
    pid, vid = {x["id"] for x in pool}, {x["id"] for x in valid}; step = max(1, len(E.products) // 180)   # evenly spaced sample of the real catalogue for the animation
    grid = [{"id": x["id"], "t": x["title"][:48], "s": "valid" if x["id"] in vid else "rejected" if x["id"] in pid else "other"} for x in E.products[::step][:180]]
    stage("filtering", "Hard Constraint Filter", f"{len(pool)} → {len(valid)} valid products", {"funnel": funnel, "valid": len(valid), "rejections": rej, "reject_counts": rcounts, "grid": grid, "pool": len(pool)}, t)

    out = {**base, "query": q, "security": sec, "domain": dom, "intent": I, "slots": slots, "constraints": [c.info() for c in C], "funnel": funnel,
           "valid_count": len(valid), "rejections": rej, "reject_counts": rcounts, "weights": WEIGHTS, "labels": LABELS}
    if not valid:
        hints = leave_one_out_hints(E.products, C)
        trace.append({"id": "ranking", "title": "AI Ranking", "summary": "Skipped: no valid product to rank", "data": {}, "ms": 0})
        trace.append({"id": "explanation", "title": "Explanation", "summary": "NO EXACT MATCH FOUND: constraints were not relaxed", "data": {"hints": hints}, "ms": 0})
        T["total"] = round((time.perf_counter() - t0) * 1000, 1)
        return {**out, "status": "no_match", "message": "NO EXACT MATCH FOUND", "detail": "No product in the catalogue satisfies every requirement. Nothing was substituted.",
                "hints": hints, "results": [], "trace": trace, "timings": T}

    # 7 - ranking
    t = time.perf_counter(); rk = rank(valid, sims, I, E.index)
    stage("ranking", "AI Ranking", f"{len(valid)} valid products scored; best match {rk[0]['score']}%",
          {"weights": WEIGHTS, "top": [{"id": r["id"], "title": E.by_id[r["id"]]["title"], "score": r["score"], "breakdown": r["breakdown"]} for r in rk[:8]], "engine": E.sem.name}, t)
    results = [{**public(E.by_id[r["id"]]), "score": r["score"], "breakdown": r["breakdown"], "na": r["na"], "cos": r["cos"],
                "why": why_list(E.by_id[r["id"]], I, r)} for r in rk[:24]]

    # 8 - explanation + output validation
    t = time.perf_counter(); best = E.by_id[rk[0]["id"]]; text = explain(best, I, rk[0])
    v = validate_text(text, best, I, [r["title"] for r in results[1:6]]); gate, bad = final_gate(results, C, E.by_id)
    if bad: results = [r for r in results if r["id"] not in bad]; sec["output_validation"] = "FLAG"
    if not v["ok"]: text = f"{best['title']} is the best match for your constraints."; sec["output_validation"] = "FLAG"
    stage("explanation", "Explanation", "Explanation written from catalogue facts and checked against the database", {"text": text, "checks": v["checks"] + gate, "top3": [r["id"] for r in results[:3]], "facts": {"Product": best["title"], "Brand": best["brand"], "Type": TYPE_LABEL[best["product_type"]], "Colour": best["colour"] or "n/a", "Price": f"₹{best['price']:,}", "MRP": f"₹{best['mrp']:,}", "Rating": f"{best['rating']}★ ({best['rating_count']})" if best["rating"] else "unrated"}}, t)
    T["total"] = round((time.perf_counter() - t0) * 1000, 1)
    return {**out, "status": "ok", "message": f"{len(valid)} valid products found", "results": results, "top": [r["id"] for r in results[:3]],
            "explanation": {"text": text, "source": "grounded template (no LLM)", "checks": v["checks"] + gate}, "trace": trace, "timings": T}
