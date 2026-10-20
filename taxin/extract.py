"""What an AI extraction step hands the engine: the true documents plus, for about half the
returns, one realistic extraction or upload error."""
import copy, random
from . import forms

DEV_KINDS = ["digit_swap", "box_shift", "decimal", "wrong_recipient", "duplicate", "corrected_both", "missing", "qualified_gt"]


def swap_digits(r, x):
    s = f"{x:.2f}"
    idx = [i for i in range(len(s) - 1) if s[i].isdigit() and s[i + 1].isdigit() and s[i] != s[i + 1]]
    if not idx:
        return None
    i = r.choice(idx)
    return float(s[:i] + s[i + 1] + s[i] + s[i + 2:])


def plant(r, h, kind):
    docs = h["docs"]
    w2s = [d for d in docs if d["form"] == "W-2"]
    if kind == "digit_swap":
        d = r.choice(w2s)
        box = r.choice(["2", "4", "6"])
        v = swap_digits(r, d["boxes"][box])
        if v is None or abs(v - d["boxes"][box]) < 1.5:
            return None
        d["boxes"][box] = v
        return dict(doc=d["id"], box=box)
    if kind == "box_shift":
        d = r.choice(w2s)
        d["boxes"]["1"] = d["boxes"]["2"]                       # the withholding read into the wages box
        return dict(doc=d["id"], box="1")
    if kind == "decimal":
        d = r.choice(w2s)
        box = r.choice(["4", "6"])
        d["boxes"][box] = round(d["boxes"][box] / r.choice([10, 100]), 2)
        return dict(doc=d["id"], box=box)
    if kind == "wrong_recipient":
        if not h["spouse"]:
            return None
        sp = [d for d in docs if d["tin"] == h["spouse"]["tin"]]
        if not sp:
            return None
        d = r.choice(sp)
        d["tin"] = h["taxpayer"]["tin"]                          # filed under the other spouse
        return dict(doc=d["id"])
    if kind == "duplicate":
        d = copy.deepcopy(r.choice(docs))
        d["id"] = d["id"] + "-dup"
        docs.append(d)
        return dict(doc=d["id"])
    if kind == "corrected_both":
        src = r.choice([d for d in docs if d["form"] != "W-2"] or docs)
        d = copy.deepcopy(src)
        d["id"] = d["id"] + "-c"
        d["corrected"] = True
        key = next(iter(d["boxes"]))
        d["boxes"][key] = round(d["boxes"][key] * r.uniform(0.7, 1.3), 2)
        if d["form"] == "1099-DIV":
            d["boxes"]["1b"] = round(min(d["boxes"]["1b"], d["boxes"]["1a"]), 2)
        docs.append(d)                                          # both kept: would double count
        return dict(doc=src["id"])
    if kind == "missing":
        d = r.choice(docs)
        docs.remove(d)
        return dict(payer=d["payer"], form=d["form"])
    if kind == "qualified_gt":
        divs = [d for d in docs if d["form"] == "1099-DIV"]
        if not divs:
            return None
        d = r.choice(divs)
        d["boxes"]["1b"] = round(d["boxes"]["1a"] * r.uniform(1.05, 1.5), 2)
        return dict(doc=d["id"], box="1b")
    if kind == "ein_swap":                                      # held-out only: a second W-2 from the same employer name
        if len(w2s) < 1:
            return None
        d = copy.deepcopy(r.choice(w2s))
        d["id"] = d["id"] + "-b"
        d["payer_ein"] = forms.ein(r)
        docs.append(d)
        return dict(doc=d["id"])
    raise ValueError(kind)


def make(seed, n, kinds=DEV_KINDS, rate=0.5):
    r = random.Random(seed)
    out = []
    for i in range(n):
        h = forms.household(r, i)
        truth = copy.deepcopy(h)
        kind, where = None, None
        if r.random() < rate:
            for _ in range(5):
                k = r.choice(kinds)
                where = plant(r, h, k)
                if where is not None:
                    kind = k
                    break
        out.append(dict(ret=h, truth=truth, kind=kind, where=where))
    return out
