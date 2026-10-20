"""A married couple's extracted 2025 documents with three upload/extraction slips."""
import copy, random, sys
from taxin import forms, validate

sys.stdout.reconfigure(encoding="utf-8")
r = random.Random(7)
priya, arjun = dict(name="Priya Shah", tin="000-41-5521"), dict(name="Arjun Shah", tin="000-63-0198")
docs = [forms.w2(r, priya, "Northwind Labs", 168_000.00), forms.w2(r, priya, "Bluefin Health", 142_500.00),
        forms.w2(r, arjun, "Granite Logistics", 96_400.00),
        dict(form="1099-DIV", payer="Meridian Brokerage", payer_ein="00-5512093", tin=arjun["tin"], name=arjun["name"],
             boxes={"1a": 3_412.18, "1b": 2_901.77, "2a": 640.00, "2b": 0.0, "4": 0.0, "7": 41.20}, corrected=False, year=2025)]
for k, d in enumerate(docs):
    d["id"] = f"D{k + 1}"
ret = dict(taxpayer=priya, spouse=arjun, docs=docs, last_year_payers=sorted({(d["payer"], d["form"]) for d in docs} | {("Union Savings", "1099-INT")}))
true_credit = validate.derive(copy.deepcopy(ret))
# the slips: Priya's Bluefin W-2 lands under Arjun's SSN, box 4 on her Northwind W-2 loses a digit, the 1099-DIV is uploaded twice
docs[1]["tin"] = arjun["tin"]
docs[0]["boxes"]["4"] = round(docs[0]["boxes"]["4"] / 10, 2)
dup = copy.deepcopy(docs[3]); dup["id"] = "D5"; docs.append(dup)
print("Extracted documents (Priya and Arjun Shah, MFJ, synthetic):")
for d in docs:
    who = "Priya" if d["tin"] == priya["tin"] else "Arjun"
    main = {k: d["boxes"][k] for k in list(d["boxes"])[:4]}
    print(f"  {d['id']} {d['form']:9s} {d['payer']:18s} filed under {who:5s} {main}")
print(f"\nschema-only check: {validate.schema_only(ret)['decision']}")
out = validate.check(ret)
print(f"input validator:   {out['decision']}")
for f in out["flags"]:
    print(f"   {f['level']:10s} {f['code']:22s} {f['doc'] or '':4s} {f['msg']}")
print(f"\nexcess Social Security credit on these inputs: {out['derived'] or 'none'}"
      f"\n   from the true documents it would be: {true_credit}  (it only exists once Priya's two W-2s are both hers)")
