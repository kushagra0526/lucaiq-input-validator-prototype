"""Planted extraction errors vs validation.  python evaluate.py [dev|heldout] [out.json]"""
import json, sys
from collections import Counter
from taxin import extract, validate

METHODS = {"schema": validate.schema_only, "rules": validate.check}


def run(which):
    if which == "heldout":
        h = json.load(open("heldout/config.json"))
        items = extract.make(h["seed"], h["n"], h["kinds"], h["rate"])
    else:
        items = extract.make(1, 1500)
    res = {m: Counter() for m in METHODS}
    per = {m: Counter() for m in METHODS}
    kinds = Counter(it["kind"] or "clean" for it in items)
    credit_ok = credit_n = 0
    for it in items:
        for m, fn in METHODS.items():
            d = fn(it["ret"])["decision"]
            if it["kind"]:
                res[m]["missed"] += d == "CLEAN"
                per[m][it["kind"]] += d != "CLEAN"
            else:
                res[m]["clean_flagged"] += d != "CLEAN"
        if not it["kind"]:
            truth = validate.derive(it["truth"])
            got = validate.check(it["ret"])["derived"]
            credit_n += bool(truth)
            credit_ok += bool(truth) and truth == got
    return dict(set=which, returns=len(items), with_error=sum(v for k, v in kinds.items() if k != "clean"), clean=kinds["clean"],
                kinds=dict(kinds), results={m: dict(v) for m, v in res.items()}, caught={m: dict(v) for m, v in per.items()},
                excess_ss=dict(returns=credit_n, computed_right=credit_ok))


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "dev"
    r = run(which)
    print(f"{which}: {r['returns']} returns, {r['with_error']} with one planted extraction/upload error")
    for m, x in r["results"].items():
        print(f"  {m:7s} errors passed as CLEAN {x.get('missed', 0):4d}/{r['with_error']}   clean returns flagged {x.get('clean_flagged', 0):4d}/{r['clean']}")
    print("  caught per error kind (schema / rules):")
    for k, n in sorted(r["kinds"].items()):
        if k != "clean":
            print(f"    {k:16s} {n:4d}   {r['caught']['schema'].get(k, 0):4d}  {r['caught']['rules'].get(k, 0):4d}")
    print(f"  excess Social Security credit computed right on {r['excess_ss']['computed_right']}/{r['excess_ss']['returns']} clean returns that have one")
    if len(sys.argv) > 2:
        json.dump(r, open(sys.argv[2], "w"), indent=1)
