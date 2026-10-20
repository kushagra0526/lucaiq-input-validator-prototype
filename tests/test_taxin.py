import os, sys, unittest, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from taxin import forms, validate


def ret(docs, spouse=True):
    tp = dict(name="Priya Shah", tin="000-11-1111")
    sp = dict(name="Arjun Shah", tin="000-22-2222") if spouse else None
    for k, d in enumerate(docs):
        d.setdefault("id", f"D{k}")
    return dict(taxpayer=tp, spouse=sp, docs=docs, last_year_payers=sorted({(d["payer"], d["form"]) for d in docs}))


class T(unittest.TestCase):
    def test_constants(self):
        self.assertEqual(forms.SS_MAX, 10918.20)

    def test_w2_consistent_is_clean(self):
        r = random.Random(1)
        d = forms.w2(r, dict(name="Priya Shah", tin="000-11-1111"), "Northwind Labs", 250_000)
        self.assertEqual(validate.check(ret([d]))["decision"], "CLEAN")

    def test_decimal_in_box4(self):
        r = random.Random(2)
        d = forms.w2(r, dict(name="Priya Shah", tin="000-11-1111"), "Northwind Labs", 180_000)
        d["boxes"]["4"] = round(d["boxes"]["4"] / 10, 2)
        out = validate.check(ret([d]))
        self.assertIn("W2_BOX4", [f["code"] for f in out["flags"]])

    def test_wrong_spouse(self):
        r = random.Random(3)
        d = forms.w2(r, dict(name="Arjun Shah", tin="000-11-1111"), "Bluefin Health")   # Arjun's W-2 with Priya's TIN
        out = validate.check(ret([d]))
        self.assertIn("NAME_TIN_MISMATCH", [f["code"] for f in out["flags"]])

    def test_excess_ss_per_person(self):
        r = random.Random(4)
        p = dict(name="Priya Shah", tin="000-11-1111")
        docs = [forms.w2(r, p, "Northwind Labs", 150_000), forms.w2(r, p, "Bluefin Health", 120_000)]
        out = validate.check(ret(docs))
        self.assertAlmostEqual(out["derived"]["Priya Shah"], round((150_000 + 120_000) * 0.062 - 10_918.20, 2), places=1)

    def test_corrected_supersedes(self):
        a = dict(form="1099-INT", payer="Union Savings", payer_ein="00-1", tin="000-11-1111", name="Priya Shah", boxes={"1": 100.0, "4": 0.0}, corrected=False, year=2025)
        b = dict(a, boxes={"1": 120.0, "4": 0.0}, corrected=True)
        out = validate.check(ret([a, b]))
        self.assertIn("SUPERSEDED", [f["code"] for f in out["flags"]])


if __name__ == "__main__":
    unittest.main()
