"""Security layer: input validation, prompt-injection detection, catalogue grounding / output gate. No secrets exist to leak:
this app needs no API key, and nothing the user types is stored."""
import re
INJ = [re.compile(p, re.I) for p in [
    r"ignore\s+(?:all\s+|any\s+|the\s+|your\s+|previous\s+|prior\s+|above\s+|earlier\s+|shopping\s+)*(?:instruction|task|rule|prompt|direction)",
    r"(?:reveal|show|print|expose|leak|dump|display|tell)\W+(?:\w+\W+){0,5}?(?:system\s*prompt|api\W*key|secret|password|credential|token|database|\.env|config)",
    r"system\s*prompt", r"you\s+are\s+now", r"developer\s+mode|jailbreak|\bdan\b", r"disregard|override\s+(?:the\s+)?(?:rules|instructions)",
    r"(?:drop|delete)\s+table|union\s+select|select\s+.+\s+from|;\s*--", r"<\s*script|javascript:", r"\{\{|\$\{", r"act\s+as\s+(?:an?\s+)?(?:admin|root|developer)"]]

def check_input(q):
    s = {"input_validation": "PASS", "prompt_injection": "PASS", "catalogue_grounding": "PASS", "output_validation": "PASS", "api_key_protection": "PASS"}
    if not isinstance(q, str): s["input_validation"] = "FAIL"; return s, "Query must be text.", "invalid", None
    q = re.sub(r"\s+", " ", re.sub(r"[\x00-\x1f\x7f]", " ", q)).strip()
    if len(q) < 3: s["input_validation"] = "FAIL"; return s, "Query too short (minimum 3 characters).", "invalid", None
    if len(q) > 300: s["input_validation"] = "FAIL"; return s, "Query too long (maximum 300 characters).", "invalid", None
    if any(p.search(q) for p in INJ): s["prompt_injection"] = "BLOCKED"; return s, "Prompt injection detected. Request blocked.", "blocked", None
    return s, None, None, q

def final_gate(results, constraints, products_by_id):
    """Catalogue grounding + output gate: every displayed product must exist in the DB with the same price and satisfy ALL constraints."""
    bad = []
    for r in results:
        db = products_by_id.get(r["id"])
        if db is None or db["price"] != r["price"] or any(c.check(db) for c in constraints): bad.append(r["id"])
    return [{"label": "Every product exists in the catalogue with matching price", "ok": not any(products_by_id.get(r["id"]) is None or products_by_id[r["id"]]["price"] != r["price"] for r in results)},
            {"label": "Every product re-checked against all hard constraints", "ok": not bad}], bad
