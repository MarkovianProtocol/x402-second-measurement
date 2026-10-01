#!/usr/bin/env python3
"""Fleet fingerprint: do settlement submitters share a lifetime transaction count?

Independent operators accumulate transactions at their own pace, so their nonces
should be spread arbitrarily. Wallets provisioned and driven by one system tend to
march in step. This measures the nonces of every submitter we observed and reports
clusters whose lifetime counts sit within 1% of each other — a signal that does not
depend on the co-service graph at all.
"""
import json
import os
import statistics
import time
import urllib.request

RPC = os.environ.get("BASE_RPC", "https://mainnet.base.org")
D = os.environ.get("X402_DIR", os.path.expanduser("~/x402_measure"))


def rpc(m, p, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(
                RPC, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": m,
                                      "params": p}).encode(),
                headers={"Content-Type": "application/json",
                         "User-Agent": "markovian-x402-measure/1.0"})
            r = json.load(urllib.request.urlopen(req, timeout=40))
            if "error" in r:
                raise RuntimeError(str(r["error"])[:60])
            return r["result"]
        except Exception:
            if i + 1 == tries:
                raise
            time.sleep(2 * (2 ** i))


def main():
    d = json.load(open(os.path.join(D, "facilitators.json")))
    rows = d["submitters"]
    nonces, bal = {}, {}
    for r in rows:
        s = r["submitter"]
        try:
            nonces[s] = int(rpc("eth_getTransactionCount", [s, "latest"]), 16)
            bal[s] = int(rpc("eth_getBalance", [s, "latest"]), 16) / 1e18
        except Exception:
            continue
    print(f"measured {len(nonces)} submitters\n")

    groups = []
    for s, n in sorted(nonces.items(), key=lambda kv: kv[1]):
        for g in groups:
            if abs(n - g["mean"]) / max(g["mean"], 1) < 0.01:
                g["m"].append((s, n))
                g["mean"] = statistics.mean([x[1] for x in g["m"]])
                break
        else:
            groups.append({"mean": n, "m": [(s, n)]})

    share = {r["submitter"]: r["share"] for r in rows}
    fleets = sorted([g for g in groups if len(g["m"]) > 1],
                    key=lambda g: -len(g["m"]))
    print("FLEETS (lifetime tx counts within 1% of each other):")
    out = []
    for g in fleets:
        ns = [x[1] for x in g["m"]]
        sh = sum(share.get(s, 0) for s, _ in g["m"])
        spread = 100 * (max(ns) - min(ns)) / max(ns)
        print(f"  {len(g['m']):>3} wallets | counts {min(ns):,}-{max(ns):,} "
              f"(spread {spread:.2f}%) | {sh:.1f}% of sampled settlements")
        out.append({"wallets": len(g["m"]), "min": min(ns), "max": max(ns),
                    "spread_pct": round(spread, 3), "settlement_share": round(sh, 2),
                    "addresses": [s for s, _ in g["m"]]})

    singles = [g for g in groups if len(g["m"]) == 1]
    print(f"\nunclustered submitters: {len(singles)} "
          f"({sum(share.get(g['m'][0][0], 0) for g in singles):.1f}% of settlements)")
    json.dump({"measured": len(nonces), "fleets": out,
               "unclustered": len(singles)},
              open(os.path.join(D, "fleets.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
