"""Stage 8 - Explanation. Text is built ONLY from catalogue fields + the user's constraints (no LLM, nothing invented),
then validated against the database record before display."""
import re
from domain import TYPE_LABEL

def why_list(p, I, rk):
    w = [f"Type: {TYPE_LABEL[p['product_type']]}" + (" (requested)" if I["types"] else "")]
    if I["colours"]: w.append(f"Colour: {p['colour']} (requested {'/'.join(I['colours'])})")
    if I["gender"]: w.append(f"Made for: {p['gender']} (requested {I['gender']})")
    if I["brands"]: w.append(f"Brand: {p['brand']} (requested)")
    if I["budget_max"]: w.append(f"Price ₹{p['price']:,} is within the ₹{I['budget_max']:,} budget")
    for b in rk["breakdown"]:
        if b["key"] in ("use_case", "attributes") and b["raw"] > 0: w.append(f"{b['label']}: {b['note']}")
    w.append(f"{p['rating']}★ from {p['rating_count']} ratings" if p["rating"] else "No customer ratings yet")
    return w

def explain(p, I, rk):
    bits = [f"{TYPE_LABEL[p['product_type']].lower()}"]
    if I["colours"]: bits.append(f"in {p['colour']}")
    if I["gender"]: bits.append(f"for {I['gender']}")
    s = f"{p['title']} ({p['brand']}) is the best match: it is {' '.join(bits)}"
    s += f" and costs ₹{p['price']:,}" + (f", within your ₹{I['budget_max']:,} budget" if I["budget_max"] else "")
    disc = round(100 * (p["mrp"] - p["price"]) / p["mrp"]) if p["mrp"] > p["price"] else 0
    if disc: s += f" ({disc}% below its ₹{p['mrp']:,} MRP)"
    s += "."
    uc = [b for b in rk["breakdown"] if b["key"] == "use_case" and b["raw"] > 0]
    if uc: s += f" Use-case evidence: {uc[0]['note']}."
    s += f" Rated {p['rating']}★ by {p['rating_count']} customers." if p["rating"] else " It has no customer ratings yet."
    return s + f" Overall match score: {rk['score']}%."

def validate_text(text, p, I, others):
    """Output validation: every figure in the text must equal a database value; no other product may be mentioned."""
    amounts = {int(x.replace(",", "")) for x in re.findall(r"₹([\d,]+)", text)}
    allowed = {p["price"], p["mrp"], I["budget_max"], I["budget_min"]} - {None}
    rates = set(re.findall(r"(\d\.\d)★", text))
    checks = [("Product exists in the database", True),
              ("Every ₹ amount matches the database record or the user's budget", amounts <= allowed),
              ("Rating matches the database record", rates <= ({str(p['rating'])} if p["rating"] else set())),
              ("No other product or link mentioned", not any(t in text for t in others) and "http" not in text)]
    return {"checks": [{"label": l, "ok": bool(o)} for l, o in checks], "ok": all(o for _, o in checks)}
