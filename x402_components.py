#!/usr/bin/env python3
"""Cluster x402 settlement traffic into distinct operations.

A "facilitator" counted naively is just an address that submits settlements. But
if two submitters serve the same payer, they are part of one operation. Building
the bipartite submitter-payer graph and taking connected components collapses a
rotating hot-wallet fleet into the operation behind it.
"""
import collections
import json
import os
import random
import time
import urllib.request

RPC = os.environ.get("BASE_RPC", "https://mainnet.base.org")
D = os.environ.get("X402_DIR", os.path.expanduser("~/x402_measure"))
N_BLOCKS = 400


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
                raise RuntimeError(str(r["error"])[:80])
            return r["result"]
        except Exception:
            if i + 1 == tries:
                raise
            time.sleep(2 * (2 ** i))


def main():
    by_block, tx_payer = {}, {}
    for line in open(os.path.join(D, "authorizations.jsonl")):
        r = json.loads(line)
        by_block.setdefault(r["block"], set()).add(r["tx"])
        tx_payer[r["tx"]] = r["authorizer"]

    random.seed(402)
    sample = sorted(random.sample(sorted(by_block), N_BLOCKS))

    edges = collections.defaultdict(set)
    counts = collections.Counter()
    for i, b in enumerate(sample):
        blk = rpc("eth_getBlockByNumber", [hex(b), True])
        want = by_block[b]
        for t in blk.get("transactions", []):
            if t["hash"] in want:
                s = t["from"].lower()
                edges[s].add(tx_payer[t["hash"]])
                counts[s] += 1
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(sample)}", flush=True)

    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for s, ps in edges.items():
        for p in ps:
            union("S:" + s, "P:" + p)

    comp = collections.defaultdict(lambda: {"subs": set(), "payers": set(), "n": 0})
    for s, ps in edges.items():
        c = find("S:" + s)
        comp[c]["subs"].add(s)
        comp[c]["n"] += counts[s]
        comp[c]["payers"] |= ps

    total = sum(counts.values())
    ordered = sorted(comp.values(), key=lambda c: -c["n"])
    out = {"sampled_blocks": len(sample), "settlements": total,
           "distinct_submitters": len(edges),
           "distinct_payers": len({p for ps in edges.values() for p in ps}),
           "components": len(comp),
           "top_components": [
               {"submitters": len(c["subs"]), "payers": len(c["payers"]),
                "settlements": c["n"], "share": round(100 * c["n"] / total, 2)}
               for c in ordered[:10]]}
    json.dump(out, open(os.path.join(D, "components.json"), "w"), indent=1)

    print(f"\nsample: {total:,} settlements in {len(sample)} blocks")
    print(f"submitters: {len(edges)}  payers: {out['distinct_payers']}")
    print(f"CONNECTED COMPONENTS (distinct operations): {out['components']}")
    for c in out["top_components"][:6]:
        print(f"   {c['submitters']:>3} submitters, {c['payers']:>4} payers, "
              f"{c['settlements']:>5} settlements ({c['share']}%)")


if __name__ == "__main__":
    main()
