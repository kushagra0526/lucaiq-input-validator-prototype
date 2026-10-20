import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

r = json.load(open("out/heldout_first_run.json"))
K = [k for k in sorted(r["kinds"]) if k != "clean"]
x = np.arange(len(K))
fig, ax = plt.subplots(figsize=(12, 4.2))
ax.bar(x - 0.2, [100 * r["caught"]["schema"].get(k, 0) / r["kinds"][k] for k in K], 0.4, color="#aaa", label="schema-only validation")
ax.bar(x + 0.2, [100 * r["caught"]["rules"].get(k, 0) / r["kinds"][k] for k in K], 0.4, color="#2a7", label="input validator (this)")
ax.set_xticks(x); ax.set_xticklabels([k.replace("_", " ") for k in K], fontsize=8); ax.set_ylabel("% of returns stopped before the engine")
ax.legend()
ax.set_title(f"Held-out, first run: {r['returns']} synthetic returns; {r['results']['rules']['missed']}/{r['with_error']} errors passed, "
             f"{r['results']['rules'].get('clean_flagged', 0)}/{r['clean']} clean returns flagged ('ein swap' never planted in dev)")
fig.tight_layout(); fig.savefig("docs/result.png", dpi=110)
