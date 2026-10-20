"""Deterministic checks on extracted inputs, each citing the document and box.

CLEAN       nothing to look at
REVIEW      a box or document is inconsistent: the preparer checks the source before the engine runs
ASK_CLIENT  something expected is missing (a payer from last year)
"""
from .forms import SS_BASE, SS_RATE, SS_MAX, MED_RATE, ADD_MED, ADD_MED_AT

TOL = 1.00
PRETAX = ("12D", "12E", "12F", "12G", "12S")


def check(ret):
    f = []
    people = {ret["taxpayer"]["tin"]: ret["taxpayer"]["name"]}
    if ret["spouse"]:
        people[ret["spouse"]["tin"]] = ret["spouse"]["name"]
    docs = ret["docs"]

    def flag(level, code, doc, msg):
        f.append(dict(level=level, code=code, doc=doc, msg=msg))

    for d in docs:
        b, i = d["boxes"], d["id"]
        if d["tin"] not in people:
            flag("REVIEW", "UNKNOWN_RECIPIENT", i, f"{d['form']} recipient TIN {d['tin']} is not the taxpayer or spouse")
        elif people[d["tin"]].split()[0] != d["name"].split()[0]:
            flag("REVIEW", "NAME_TIN_MISMATCH", i, f"{d['form']} from {d['payer']} names {d['name']} but carries {people[d['tin']]}'s TIN")
        if d["form"] == "W-2":
            want4 = round(min(b["3"], SS_BASE) * SS_RATE, 2)
            if b["3"] > SS_BASE + TOL:
                flag("REVIEW", "W2_BOX3_OVER_BASE", i, f"box 3 {b['3']:,.2f} exceeds the 2025 wage base {SS_BASE:,.2f}")
            if abs(b["4"] - want4) > TOL:
                flag("REVIEW", "W2_BOX4", i, f"box 4 {b['4']:,.2f} should be 6.2% of box 3 = {want4:,.2f}")
            want6 = round(b["5"] * MED_RATE + ADD_MED * max(0.0, b["5"] - ADD_MED_AT), 2)
            if abs(b["6"] - want6) > TOL:
                flag("REVIEW", "W2_BOX6", i, f"box 6 {b['6']:,.2f} should be 1.45% of box 5 (+0.9% over $200k) = {want6:,.2f}")
            deferred = sum(b.get(k, 0.0) for k in PRETAX)
            if abs((b["5"] - deferred) - b["1"]) > max(TOL, 0.02 * b["5"]):
                flag("REVIEW", "W2_BOX1_VS_5", i, f"box 1 {b['1']:,.2f} vs box 5 {b['5']:,.2f} minus pre-tax deferrals {deferred:,.2f}")
            if b["2"] > b["1"]:
                flag("REVIEW", "W2_BOX2_GT_1", i, f"federal withholding {b['2']:,.2f} exceeds wages {b['1']:,.2f}")
        elif d["form"] == "1099-DIV":
            if b["1b"] > b["1a"] + TOL:
                flag("REVIEW", "DIV_1B_GT_1A", i, f"qualified dividends {b['1b']:,.2f} exceed ordinary {b['1a']:,.2f}")
            if b.get("2b", 0) > b.get("2a", 0) + TOL:
                flag("REVIEW", "DIV_2B_GT_2A", i, "unrecaptured 1250 gain exceeds total capital gain distributions")
        elif d["form"] == "1098":
            rate = b["1"] / b["2"] if b["2"] else 1
            if not 0.005 <= rate <= 0.12:
                flag("REVIEW", "1098_RATE", i, f"interest {b['1']:,.2f} on principal {b['2']:,.2f} implies {100 * rate:.1f}%")

    # duplicates and corrected forms
    seen = {}
    for d in docs:
        key = (d["form"], d["payer"], d["tin"])
        seen.setdefault(key, []).append(d)
    for key, ds in seen.items():
        if len(ds) < 2:
            continue
        corr = [d for d in ds if d["corrected"]]
        orig = [d for d in ds if not d["corrected"]]
        if corr and orig:
            for d in orig:
                flag("REVIEW", "SUPERSEDED", d["id"], f"{key[0]} from {key[1]} has a CORRECTED version ({corr[0]['id']}): use only the corrected one")
        elif any(a["boxes"] == b["boxes"] for k, a in enumerate(ds) for b in ds[k + 1:]):
            flag("REVIEW", "DUPLICATE", ds[-1]["id"], f"{key[0]} from {key[1]} uploaded twice with identical amounts")
        else:
            flag("REVIEW", "SAME_PAYER_TWICE", ds[-1]["id"], f"two different {key[0]}s from {key[1]}: confirm both are real (e.g. two EINs)")

    # last year's payers
    have = {(d["payer"], d["form"]) for d in docs}
    for payer, form in ret["last_year_payers"]:
        if (payer, form) not in have:
            flag("ASK_CLIENT", "MISSING_VS_LAST_YEAR", None, f"no {form} from {payer} this year (filed last year)")

    level = "REVIEW" if any(x["level"] == "REVIEW" for x in f) else "ASK_CLIENT" if f else "CLEAN"
    return dict(decision=level, flags=f, derived=derive(ret))


def derive(ret):
    """Excess Social Security withheld: per person, only with 2+ employers, never across spouses."""
    out = {}
    for p in [ret["taxpayer"], ret["spouse"]]:
        if not p:
            continue
        w = [d for d in ret["docs"] if d["form"] == "W-2" and d["tin"] == p["tin"] and not d["id"].endswith("-dup")]
        if len({d["payer"] for d in w}) >= 2:
            excess = round(sum(d["boxes"]["4"] for d in w) - SS_MAX, 2)
            if excess > 0:
                out[p["name"]] = excess
    return out


def schema_only(ret):
    bad = [d for d in ret["docs"] if not d.get("tin") or any((not isinstance(v, (int, float))) or v < 0 for v in d["boxes"].values())]
    return dict(decision="REVIEW" if bad else "CLEAN", flags=[])
