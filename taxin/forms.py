"""Synthetic households and their true 2025 tax documents. All names and identifiers are fake
(SSNs in the never-issued 000 area, EINs with the never-assigned 00 prefix)."""
import random

SS_BASE, SS_RATE, MED_RATE, ADD_MED, ADD_MED_AT = 176_100.00, 0.062, 0.0145, 0.009, 200_000.00
SS_MAX = round(SS_BASE * SS_RATE, 2)          # 10,918.20
FIRST = "Priya Arjun Maya Daniel Grace Omar Lena Victor Hana Samuel Ines Tomas".split()
LAST = "Shah Morales Okafor Lindqvist Novak Haddad Brennan Castillo".split()
EMPLOYERS = "Northwind Labs,Bluefin Health,Granite Logistics,Cedar Analytics,Harbor Retail,Summit Foods,Atlas Robotics,Pinecrest Bank".split(",")
BANKS = "First Prairie Bank,Lakeshore Credit Union,Meridian Brokerage,Westgate Securities,Union Savings".split(",")


def tin(r):
    return f"000-{r.randint(10, 99)}-{r.randint(1000, 9999)}"


def ein(r):
    return f"00-{r.randint(1000000, 9999999)}"


def w2(r, person, employer, wages=None):
    box5 = round(wages if wages is not None else r.uniform(30_000, 260_000), 2)
    d = round(r.choice([0, 0, r.uniform(2_000, 23_500)]), 2)
    box1 = round(box5 - d, 2)
    box3 = min(box5, SS_BASE)
    b = {"1": box1, "2": round(box1 * r.uniform(0.08, 0.24), 2), "3": round(box3, 2), "4": round(box3 * SS_RATE, 2),
         "5": box5, "6": round(box5 * MED_RATE + ADD_MED * max(0.0, box5 - ADD_MED_AT), 2), "16": box1}
    if d:
        b["12D"] = d
    return dict(form="W-2", payer=employer, payer_ein=ein(r), tin=person["tin"], name=person["name"], boxes=b, corrected=False, year=2025)


def household(r, i):
    tp = dict(name=f"{r.choice(FIRST)} {r.choice(LAST)}", tin=tin(r))
    sp = dict(name=f"{r.choice(FIRST)} {tp['name'].split()[1]}", tin=tin(r)) if r.random() < 0.6 else None
    docs = []
    for p in [tp] + ([sp] if sp else []):
        n = r.choices([1, 2, 3], [65, 28, 7])[0]
        emps = r.sample(EMPLOYERS, n)
        big = r.random() < 0.35 and n > 1                         # two well-paid jobs: excess SS withheld
        for e in emps:
            docs.append(w2(r, p, e, r.uniform(120_000, 190_000) if big else None))
    for bank in r.sample(BANKS, r.randint(1, 3)):
        owner = r.choice([tp] + ([sp] if sp else []))
        if r.random() < 0.6:
            docs.append(dict(form="1099-INT", payer=bank, payer_ein=ein(r), tin=owner["tin"], name=owner["name"],
                             boxes={"1": round(r.uniform(15, 6_000), 2), "4": 0.0}, corrected=False, year=2025))
        else:
            a = round(r.uniform(100, 20_000), 2)
            g = round(r.uniform(0, 5_000), 2)
            docs.append(dict(form="1099-DIV", payer=bank, payer_ein=ein(r), tin=owner["tin"], name=owner["name"],
                             boxes={"1a": a, "1b": round(a * r.uniform(0.3, 0.95), 2), "2a": g, "2b": 0.0, "4": 0.0,
                                    "7": round(a * r.uniform(0, 0.03), 2)}, corrected=False, year=2025))
    if r.random() < 0.5:
        principal = round(r.uniform(150_000, 800_000), 2)
        docs.append(dict(form="1098", payer="Keystone Mortgage", payer_ein=ein(r), tin=tp["tin"], name=tp["name"],
                         boxes={"1": round(principal * r.uniform(0.03, 0.07) * r.uniform(0.9, 1.0), 2), "2": principal},
                         corrected=False, year=2025))
    for k, d in enumerate(docs):
        d["id"] = f"R{i}-D{k + 1}"
    last_year = sorted({(d["payer"], d["form"]) for d in docs})
    return dict(id=f"R{i}", taxpayer=tp, spouse=sp, docs=docs, last_year_payers=last_year)
